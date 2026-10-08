// a2u-bridge: headless driver for a portable OpenUtau install.
// Must run with the OpenUtau install dir as AppContext.BaseDirectory
// (i.e. the deployed a2u-bridge.exe lives next to OpenUtau.exe) so that
// PathManager resolves Singers/Cache/prefs.json from the real install.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using OpenUtau.Core;
using Serilog;
using OpenUtau.Core.Format;
using OpenUtau.Core.Ustx;

namespace Agent2Utau.Bridge {

    // Single-threaded scheduler + message pump emulating the Avalonia UI
    // thread. Work posted to mainScheduler / PostOnUIThread lands here and
    // is executed on the bridge main thread while it pumps.
    sealed class UiScheduler : TaskScheduler {
        public readonly BlockingCollection<Action> Queue = new BlockingCollection<Action>();
        private readonly Thread mainThread;

        public UiScheduler(Thread mainThread) { this.mainThread = mainThread; }

        protected override void QueueTask(Task task) {
            Queue.Add(() => TryExecuteTask(task));
        }
        protected override bool TryExecuteTaskInline(Task task, bool taskWasPreviouslyQueued) {
            if (Thread.CurrentThread != mainThread) return false;
            return TryExecuteTask(task);
        }
        protected override IEnumerable<Task> GetScheduledTasks() => Enumerable.Empty<Task>();
        public override int MaximumConcurrencyLevel => 1;

        public void Post(Action a) => Queue.Add(a);

        // Run queued actions until `done` or timeout. Returns true if done.
        public bool PumpUntil(Func<bool> done, TimeSpan timeout) {
            var deadline = DateTime.UtcNow + timeout;
            while (!done()) {
                var remain = deadline - DateTime.UtcNow;
                if (remain <= TimeSpan.Zero) return false;
                if (Queue.TryTake(out var a, TimeSpan.FromMilliseconds(Math.Min(200, remain.TotalMilliseconds)))) {
                    try { a(); } catch (Exception e) { Sink.RecordError("pump", e); }
                }
            }
            // drain
            while (Queue.TryTake(out var a, TimeSpan.Zero)) {
                try { a(); } catch (Exception e) { Sink.RecordError("pump", e); }
            }
            return true;
        }
    }

    // Captures notifications flowing through DocManager for JSON reporting.
    sealed class Sink : ICmdSubscriber {
        public readonly List<string> Errors = new List<string>();
        public readonly List<string> Progress = new List<string>();
        public readonly List<string> Warnings = new List<string>();
        private static Sink inst;
        public static Sink Inst => inst ??= new Sink();

        public static void RecordError(string where, Exception e) {
            Inst.Errors.Add($"{where}: {e.GetType().Name}: {e.Message}");
        }

        public void OnNext(UCommand cmd, bool isUndo) {
            switch (cmd) {
                case ErrorMessageNotification err:
                    var msg = err.e != null ? $"{err.message} {err.e.Message}".Trim() : err.message;
                    Errors.Add(string.IsNullOrEmpty(msg) ? err.e?.GetType().Name ?? "error" : msg);
                    break;
                case ProgressBarNotification p:
                    if (!string.IsNullOrEmpty(p.Info)) Progress.Add(p.Info);
                    break;
            }
        }
    }

    static class Program {
        static UiScheduler ui;

        [STAThread]
        static int Main(string[] args) {
            Console.OutputEncoding = System.Text.Encoding.UTF8;
            // Hard watchdog: never hang forever.
            var watchdog = new Timer(_ => {
                Console.Error.WriteLine("watchdog: forced exit");
                WriteJson(new Dictionary<string, object> {
                    ["ok"] = false, ["errors"] = Sink.Inst.Errors.Concat(new[]{"watchdog timeout"}).ToArray(),
                    ["warnings"] = Sink.Inst.Warnings });
                Environment.Exit(3);
            }, null, TimeSpan.FromMinutes(15), Timeout.InfiniteTimeSpan);
            var result = new Dictionary<string, object>();
            try {
                if (args.Length < 1) {
                    return Fail("usage: a2u-bridge <doctor|inspect|export-pitch|export-phonemes|export-variance|roundtrip|render> [options]", 2);
                }
                var cmd = args[0];
                var opt = ParseOpts(args.Skip(1).ToArray());
                Boot();
                switch (cmd) {
                    case "doctor": result = Doctor(); break;
                    case "inspect": result = Inspect(Req(opt, "project")); break;
                    case "export-pitch": result = ExportPitch(Req(opt, "project"), Req(opt, "out")); break;
                    case "export-phonemes": result = ExportPhonemes(Req(opt, "project"), Req(opt, "out")); break;
                    case "export-variance": result = ExportVariance(Req(opt, "project"), Req(opt, "out")); break;
                    case "export-render-probe":
                        result = RenderProbe.Export(LoadProject(Req(opt, "project")), Req(opt, "out"), Req(opt, "indices"));
                        break;
                    case "roundtrip": result = Roundtrip(Req(opt, "project"), Req(opt, "out")); break;
                    case "render": result = Render(opt); break;
                    default: return Fail($"unknown command {cmd}", 2);
                }
                result["errors"] = Sink.Inst.Errors;
                result["warnings"] = Sink.Inst.Warnings;
                result["ok"] = Sink.Inst.Errors.Count == 0 && (result.TryGetValue("ok", out var ok) ? (bool)ok : true);
                WriteJson(result);
                return (bool)result["ok"] ? 0 : 1;
            } catch (Exception e) {
                Sink.Inst.Errors.Add($"fatal: {e.GetType().Name}: {e.Message}");
                result["ok"] = false;
                result["errors"] = Sink.Inst.Errors;
                WriteJson(result);
                return 1;
            }
        }

        static void Boot() {
            System.Text.Encoding.RegisterProvider(System.Text.CodePagesEncodingProvider.Instance);
            Log.Logger = new LoggerConfiguration()
                .MinimumLevel.Information()
                .WriteTo.File(PathManager.Inst.LogFilePath,
                    rollingInterval: RollingInterval.Day,
                    encoding: System.Text.Encoding.UTF8,
                    shared: true)
                .CreateLogger();
            Log.Information("a2u-bridge boot");
            ui = new UiScheduler(Thread.CurrentThread);
            DocManager.Inst.PostOnUIThread = a => ui.Post(a);
            DocManager.Inst.AddSubscriber(Sink.Inst);
            DocManager.Inst.Initialize(Thread.CurrentThread, ui);
            SingerManager.Inst.SearchAllSingers();
        }

        static UProject LoadProject(string path) {
            Console.Error.WriteLine($"stage: read {path}");
            var project = Formats.ReadProject(new[] { path });
            if (project == null) throw new Exception($"Cannot read {path}");
            Console.Error.WriteLine("stage: load notification");
            DocManager.Inst.ExecuteCmd(new LoadProjectNotification(project));
            Console.Error.WriteLine("stage: validate");
            DocManager.Inst.ExecuteCmd(new ValidateProjectNotification());
            Console.Error.WriteLine("stage: wait phonemes");
            WaitPhonemes(project, TimeSpan.FromSeconds(120));
            Console.Error.WriteLine("stage: phonemes done");
            return project;
        }

        // Wait until every voice part has phonemes applied and a non-stale
        // phrase build (phrase gate observed via renderPhrases fill).
        static void WaitPhonemes(UProject project, TimeSpan timeout) {
            var runner = typeof(DocManager).GetProperty("PhonemizerRunner",
                BindingFlags.NonPublic | BindingFlags.Instance)?.GetValue(DocManager.Inst);
            var parts = project.parts.OfType<UVoicePart>().ToArray();
            var ok = ui.PumpUntil(() => {
                return parts.All(p => p.PhonemesUpToDate && p.renderPhrases.Count > 0)
                    || parts.Length == 0;
            }, timeout);
            Console.Error.WriteLine($"wait phonemes: ok={ok} upToDate={parts.Count(p=>p.PhonemesUpToDate)}/{parts.Length} phrases={parts.Sum(p=>p.renderPhrases.Count)}");
            if (parts.Length > 0 && parts.Any(p => !p.PhonemesUpToDate)) {
                Sink.Inst.Warnings.Add("phonemes not fully up to date after wait");
            }
        }

        static Dictionary<string, object> Doctor() {
            var singers = SingerManager.Inst.Singers;
            var paths = PathManager.Inst.SingersPaths;
            var perPath = paths.Select(p => {
                int n = -1; string err = null;
                try {
                    n = new OpenUtau.Classic.VoicebankLoader(p).SearchAll().Count();
                } catch (Exception e) { err = e.Message; }
                return new { path = p, exists = Directory.Exists(p), voicebanks = n, error = err };
            }).ToArray();
            return new Dictionary<string, object> {
                ["data_path"] = PathManager.Inst.DataPath,
                ["cache_path"] = PathManager.Inst.CachePath,
                ["singers_path"] = PathManager.Inst.SingersPath,
                ["singers_paths"] = perPath,
                ["load_deep"] = OpenUtau.Core.Util.Preferences.Default.LoadDeepFolderSinger,
                ["singers_found"] = singers.Keys.OrderBy(k => k).ToArray(),
                ["phonemizer_factories"] = OpenUtau.Api.PhonemizerFactory.GetAll()
                    .Select(f => f.type.FullName).OrderBy(n => n).ToArray(),
            };
        }

        static Dictionary<string, object> ExportPitch(string path, string output) {
            var project = LoadProject(path);
            var parts = project.parts.OfType<UVoicePart>().ToArray();
            if (parts.Length == 0 || parts.Any(p => !p.PhonemesUpToDate ||
                    p.renderPhrases.Count == 0 || p.notes.Any(n => n.Error) ||
                    p.phonemes.Any(ph => ph.Error))) {
                throw new InvalidOperationException("Cannot export pitch from empty, stale or invalid parts.");
            }
            // RenderPhrase builds its arrays at five-tick intervals, starting
            // at position-leading. Export the actual runtime arrays, not a
            // Python approximation of note bends or vibrato.
            var phrases = parts.SelectMany(p => p.renderPhrases.Select(ph => new {
                part_position = p.position,
                track_no = p.trackNo,
                ph.position,
                ph.leading,
                pitch_start_tick = ph.position - ph.leading,
                pitch_interval_ticks = 5,
                times_ms = Enumerable.Range(0, ph.pitches.Length)
                    .Select(i => project.timeAxis.TickPosToMsPos(ph.position - ph.leading + i * 5)).ToArray(),
                before_pitd_cents = ph.pitchesBeforeDeviation,
                final_cents = ph.pitches,
            })).ToArray();
            foreach (var phrase in phrases) {
                if (phrase.before_pitd_cents.Length != phrase.final_cents.Length ||
                    phrase.final_cents.Length == 0 ||
                    phrase.final_cents.Any(x => !float.IsFinite(x)) ||
                    phrase.before_pitd_cents.Any(x => !float.IsFinite(x))) {
                    throw new InvalidOperationException("Invalid runtime pitch arrays.");
                }
            }
            var payload = new {
                schema_version = 1,
                project = Path.GetFullPath(path),
                units = "absolute MIDI times 100 cents; absolute project milliseconds",
                stage = "RenderPhrase before renderer frame resampling; not measured audio F0",
                phrases,
            };
            var dest = Path.GetFullPath(output);
            Directory.CreateDirectory(Path.GetDirectoryName(dest));
            File.WriteAllText(dest, JsonSerializer.Serialize(payload));
            return new Dictionary<string, object> {
                ["output"] = dest, ["phrase_count"] = phrases.Length,
                ["frame_count"] = phrases.Sum(p => p.final_cents.Length),
            };
        }

        static Dictionary<string, object> ExportPhonemes(string path, string output) {
            var project = LoadProject(path);
            var parts = project.parts.OfType<UVoicePart>().ToArray();
            if (parts.Length == 0 || parts.Any(p => !p.PhonemesUpToDate ||
                    p.renderPhrases.Count == 0 || p.notes.Any(n => n.Error) ||
                    p.phonemes.Any(ph => ph.Error))) {
                throw new InvalidOperationException("Cannot export phonemes from invalid parts.");
            }
            var payloadParts = new List<object>();
            foreach (var part in parts) {
                var notes = part.notes.ToArray();
                int NoteIndex(UNote n) => n == null ? -1 : Array.IndexOf(notes, n);
                var phrases = new List<object>();
                foreach (var phrase in part.renderPhrases) {
                    // Bind identities by source position/symbol, not RenderPhone's
                    // noteIndex: that field is not assigned in some fork builds.
                    var phones = phrase.phones.Select((phone, i) => {
                        if (!double.IsFinite(phone.positionMs) || !double.IsFinite(phone.endMs)
                                || phone.durationMs <= 0) {
                            throw new InvalidOperationException("Invalid runtime phone span.");
                        }
                        var owners = part.phonemes.Where(u =>
                            Math.Abs(u.PositionMs - phone.positionMs) < 1e-6 &&
                            (u.phonemeMapped ?? u.phoneme) == phone.phoneme).ToArray();
                        return new {
                            phone_index = i, phone.phoneme, start_ms = phone.positionMs,
                            end_ms = phone.endMs, phone.tone,
                            owner_note_indices = owners.Select(u => NoteIndex(u.Parent)).ToArray(),
                            owner_primary_indices = owners.Select(u => NoteIndex(u.Parent.Extends ?? u.Parent)).ToArray(),
                            ownership_status = owners.Length == 1 ? "matched" : "ambiguous_or_absent",
                        };
                    }).ToArray();
                    phrases.Add(new {
                        phrase.position, phrase.end, phones,
                        pitch_start_tick = phrase.position - phrase.leading,
                        pitch_interval_ticks = 5,
                        pitch_times_ms = Enumerable.Range(0, phrase.pitches.Length)
                            .Select(i => project.timeAxis.TickPosToMsPos(phrase.position - phrase.leading + i * 5)).ToArray(),
                        final_cents = phrase.pitches,
                    });
                }
                payloadParts.Add(new {
                    part_position = part.position, track_no = part.trackNo,
                    notes = notes.Select((n, i) => new {
                        note_index = i, n.lyric, n.tone,
                        start_ms = project.timeAxis.TickPosToMsPos(part.position + n.position),
                        end_ms = project.timeAxis.TickPosToMsPos(part.position + n.End),
                        primary_index = NoteIndex(n.Extends ?? n),
                    }).ToArray(), phrases,
                });
            }
            var dest = Path.GetFullPath(output);
            Directory.CreateDirectory(Path.GetDirectoryName(dest));
            File.WriteAllText(dest, JsonSerializer.Serialize(new {
                schema_version = 1, project = Path.GetFullPath(path),
                units = "absolute project milliseconds; pitch absolute MIDI times 100 cents",
                stage = "validated phonemizer/RenderPhrase intended phone clock; not measured acoustic alignment",
                historical_acoustic_reproduction = false, parts = payloadParts,
            }));
            return new Dictionary<string, object> {
                ["output"] = dest, ["part_count"] = parts.Length,
                ["phone_count"] = parts.Sum(p => p.renderPhrases.Sum(ph => ph.phones.Length)),
            };
        }

        static Dictionary<string, object> ExportVariance(string path, string output) {
            var project = LoadProject(path);
            var parts = project.parts.OfType<UVoicePart>().ToArray();
            if (parts.Length == 0 || parts.Any(p => !p.PhonemesUpToDate ||
                    p.renderPhrases.Count == 0 || p.notes.Any(n => n.Error) ||
                    p.phonemes.Any(ph => ph.Error))) {
                throw new InvalidOperationException("Cannot export variance from invalid parts.");
            }
            var phrases = new List<object>();
            foreach (var part in parts) foreach (var ph in part.renderPhrases) {
                // The fork exposes methods on an internal singer type. Keep the
                // reflection adapter isolated and fail explicitly on API changes.
                var singer = ph.singer;
                var method = singer.GetType().GetMethod("getVariancePredictor");
                var predictor = method?.Invoke(singer, null)
                    ?? throw new InvalidOperationException("Variance predictor unavailable.");
                lock (singer.GetType().GetProperty("SessionLock")?.GetValue(singer)
                    ?? throw new InvalidOperationException("Singer session lock unavailable.")) {
                    var r = predictor.GetType().GetMethod("Process", new[] { ph.GetType() })?.Invoke(predictor, new object[] { ph })
                        ?? throw new InvalidOperationException("Variance Process API unavailable.");
                    object Field(string name) => r.GetType().GetField(name)?.GetValue(r)
                        ?? throw new InvalidOperationException("Variance field unavailable: " + name);
                    int totalFrames = (int)Field("totalFrames"), headFrames = (int)Field("headFrames");
                    double frameMs = Convert.ToDouble(Field("frameMs"));
                    var breathiness = (float[])Field("breathiness");
                    var voicing = (float[])Field("voicing");
                    var tension = (float[])Field("tension");
                    var channels = new[] { breathiness, voicing, tension };
                    if (channels.Any(c => c.Length != totalFrames || c.Any(x => !float.IsFinite(x))))
                        throw new InvalidOperationException("Invalid variance arrays.");
                    phrases.Add(new {
                        part_position = part.position, track_no = part.trackNo, ph.position,
                        times_ms = Enumerable.Range(0, totalFrames)
                            .Select(i => ph.positionMs + (i-headFrames)*frameMs).ToArray(),
                        breathiness, voicing, tension,
                    });
                }
            }
            var dest = Path.GetFullPath(output);
            Directory.CreateDirectory(Path.GetDirectoryName(dest));
            File.WriteAllText(dest, JsonSerializer.Serialize(new {
                schema_version = 1, project = Path.GetFullPath(path),
                stage = "raw variance predictor before user expression deltas; not measured audio", phrases,
            }));
            return new Dictionary<string, object> { ["output"] = dest, ["phrase_count"] = phrases.Count };
        }

        static Dictionary<string, object> Inspect(string path) {
            var project = LoadProject(path);
            return new Dictionary<string, object> {
                ["name"] = project.name,
                ["file_path"] = project.FilePath,
                ["ustx_version"] = project.ustxVersion.ToString(),
                ["resolution"] = project.resolution,
                ["bpm"] = project.bpm,
                ["tempos"] = project.tempos.Select(t => new { t.position, t.bpm }).ToArray(),
                ["tracks"] = project.tracks.Select(t => new {
                    t.TrackNo, t.TrackName, singer = t.Singer?.Id,
                    singerFound = t.Singer?.Found, singerLoaded = t.Singer?.Loaded,
                    singerType = t.Singer?.SingerType.ToString(),
                    phonemizer = t.Phonemizer?.GetType().FullName,
                    renderer = t.RendererSettings?.renderer,
                    voiceColors = t.VoiceColorNames,
                }).ToArray(),
                ["voice_parts"] = project.parts.OfType<UVoicePart>().Select(p => new {
                    p.name, p.trackNo, p.position, p.Duration,
                    positionMs = project.timeAxis.TickPosToMsPos(p.position),
                    notes = p.notes.Count, renderPhrases = p.renderPhrases.Count,
                    invalidNotes = p.notes.Where(n => n.Error).Select(n => new {
                        n.lyric, n.position, n.duration, n.OverlapError,
                    }).ToArray(),
                    invalidPhonemes = p.phonemes.Where(ph => ph.Error).Select(ph => new {
                        ph.phoneme, ph.position, error = ph.ErrorException?.Message,
                    }).ToArray(),
                    phonemesUpToDate = p.PhonemesUpToDate,
                    phrases = p.renderPhrases.Select(ph => new {
                        ph.position, ph.end, ph.positionMs,
                        leadingMs = ph.leadingMs,
                    }).ToArray(),
                }).ToArray(),
                ["wave_parts"] = project.parts.OfType<UWavePart>().Select(p => new {
                    p.name, p.trackNo, p.position, p.relativePath,
                    loaded = p.Samples != null,
                }).ToArray(),
            };
        }

        static Dictionary<string, object> Roundtrip(string path, string outPath) {
            var project = LoadProject(path);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outPath)));
            Ustx.Save(outPath, project);
            // reload and re-validate
            var project2 = Formats.ReadProject(new[] { outPath });
            if (project2 == null) throw new Exception($"Cannot re-read {outPath}");
            DocManager.Inst.ExecuteCmd(new LoadProjectNotification(project2));
            DocManager.Inst.ExecuteCmd(new ValidateProjectNotification());
            WaitPhonemes(project2, TimeSpan.FromSeconds(120));
            var p1 = project.parts.OfType<UVoicePart>().ToArray();
            var p2 = project2.parts.OfType<UVoicePart>().ToArray();
            return new Dictionary<string, object> {
                ["saved"] = outPath,
                ["notes_before"] = p1.Sum(p => p.notes.Count),
                ["notes_after"] = p2.Sum(p => p.notes.Count),
                ["phrases_after"] = p2.Sum(p => p.renderPhrases.Count),
                ["lyrics_match"] = string.Join("|", p2.SelectMany(p => p.notes.Select(n => n.lyric)))
                    == string.Join("|", p1.SelectMany(p => p.notes.Select(n => n.lyric))),
            };
        }

        static Dictionary<string, object> Render(Dictionary<string, string> opt) {
            var project = LoadProject(Req(opt, "project"));
            // A WAV can be produced even when OpenUtau has silently excluded
            // invalid notes. Fail before export instead of calling that success.
            foreach (var part in project.parts.OfType<UVoicePart>()) {
                foreach (var note in part.notes.Where(n => n.Error)) {
                    Sink.Inst.Errors.Add($"invalid note: {part.name}/{note.lyric} at {note.position}, overlap={note.OverlapError}");
                }
                foreach (var ph in part.phonemes.Where(ph => ph.Error)) {
                    Sink.Inst.Errors.Add($"invalid phoneme: {part.name}/{ph.phoneme} at {ph.position}: {ph.ErrorException?.Message}");
                }
            }
            if (Sink.Inst.Errors.Count > 0) {
                return new Dictionary<string, object> { ["ok"] = false };
            }
            var outPath = Req(opt, "out");
            var timeoutMin = opt.TryGetValue("timeout", out var t) ? int.Parse(t) : 20;
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outPath)));
            var dir = Path.GetDirectoryName(Path.GetFullPath(outPath));
            var stem = Path.GetFileNameWithoutExtension(outPath);
            var before = Directory.Exists(dir)
                ? Directory.GetFiles(dir, "*.wav").ToDictionary(f => f, f => File.GetLastWriteTimeUtc(f))
                : new Dictionary<string, DateTime>();

            Task task;
            if (opt.ContainsKey("mixdown")) {
                task = PlaybackManager.Inst.RenderMixdown(project, outPath);
            } else {
                task = PlaybackManager.Inst.RenderToFiles(project, outPath);
            }
            ui.PumpUntil(() => task.IsCompleted, TimeSpan.FromMinutes(timeoutMin));
            if (!task.IsCompleted) throw new TimeoutException("render did not finish");
            if (task.IsFaulted) throw task.Exception?.Flatten() ?? new Exception("render failed");

            var produced = Directory.GetFiles(dir, "*.wav")
                .Where(f => !before.TryGetValue(f, out var wt) || File.GetLastWriteTimeUtc(f) > wt)
                .Select(f => new { path = f, bytes = new FileInfo(f).Length })
                .ToArray();
            return new Dictionary<string, object> {
                ["files"] = produced,
                ["ok"] = produced.Length > 0 && Sink.Inst.Errors.Count == 0,
            };
        }

        // ---- helpers ----
        static Dictionary<string, string> ParseOpts(string[] args) {
            var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < args.Length; i++) {
                if (args[i].StartsWith("--")) {
                    var key = args[i].Substring(2);
                    if (i + 1 < args.Length && !args[i + 1].StartsWith("--")) d[key] = args[++i];
                    else d[key] = "true";
                }
            }
            return d;
        }
        static string Req(Dictionary<string, string> o, string k) {
            if (!o.TryGetValue(k, out var v) || string.IsNullOrEmpty(v))
                throw new ArgumentException($"missing --{k}");
            return v;
        }
        static int Fail(string msg, int code) {
            WriteJson(new Dictionary<string, object> { ["ok"] = false, ["errors"] = new[] { msg } });
            return code;
        }
        static void WriteJson(object o) {
            Console.WriteLine(JsonSerializer.Serialize(o, new JsonSerializerOptions { WriteIndented = false }));
        }
    }
}

// Diagnostic input export only. Never edits music, singer, preferences or deletes caches.
// Native cache-key matches guard the mirrored renderer feed construction.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using OpenUtau.Core;
using OpenUtau.Core.DiffSinger;
using OpenUtau.Core.Render;
using OpenUtau.Core.Ustx;
using OpenUtau.Core.Util;

namespace Agent2Utau.Bridge {
    static class RenderProbe {
        static object Field(object o, string name) => o.GetType().GetField(name,
            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?.GetValue(o)
            ?? throw new InvalidOperationException("Probe field unavailable: " + name);
        static object Call(object o, string name, params object[] args) => o.GetType().GetMethod(name)?.Invoke(o, args)
            ?? throw new InvalidOperationException("Probe method unavailable: " + name);
        static NamedOnnxValue Float(string name, float[] x, params int[] dims) =>
            NamedOnnxValue.CreateFromTensor(name, new DenseTensor<float>(x, dims));
        static NamedOnnxValue Long(string name, long[] x, params int[] dims) =>
            NamedOnnxValue.CreateFromTensor(name, new DenseTensor<long>(x, dims));
        static object Data(NamedOnnxValue v) {
            var t = (TensorBase)v.Value;
            if (t.GetTypeInfo().ElementType == TensorElementType.Float) {
                var x = v.AsTensor<float>();
                return new { name = v.Name, dtype = "float32", shape = x.Dimensions.ToArray(), values = x.ToArray() };
            }
            if (t.GetTypeInfo().ElementType == TensorElementType.Int64) {
                var x = v.AsTensor<long>();
                return new { name = v.Name, dtype = "int64", shape = x.Dimensions.ToArray(), values = x.ToArray() };
            }
            if (t.GetTypeInfo().ElementType == TensorElementType.Bool) {
                var x = v.AsTensor<bool>();
                return new { name = v.Name, dtype = "bool", shape = x.Dimensions.ToArray(), values = x.ToArray() };
            }
            throw new InvalidOperationException("Probe unsupported tensor type");
        }

        public static Dictionary<string, object> Export(UProject project, string output, string indices) {
            var requested = indices.Split(',').Select(int.Parse).ToHashSet();
            var parts = project.parts.OfType<UVoicePart>().Where(p => p.trackNo == 0).ToArray();
            if (parts.Length == 0 || parts.Any(p => !p.PhonemesUpToDate || p.notes.Any(n => n.Error) || p.phonemes.Any(ph => ph.Error)))
                throw new InvalidOperationException("Invalid probe project");
            var root = Path.GetFullPath(output);
            Directory.CreateDirectory(root);
            var rows = new List<object>();
            int index = -1;
            foreach (var part in parts) foreach (var ph in part.renderPhrases) {
                index++;
                if (!requested.Contains(index)) continue;
                var singer = ph.singer;
                var cfg = (DsConfig)Field(singer, "dsConfig");
                if (!cfg.useContinuousAcceleration || !cfg.useVariableDepth || cfg.useEnergyEmbed)
                    throw new InvalidOperationException("Probe requires supported continuous-depth, non-energy/falsetto model layout");
                var session = (InferenceSession)Call(singer, "getAcousticSession");
                var vocoder = (DsVocoder)Call(singer, "getVocoder");
                var predictor = (DsVariance)Call(singer, "getVariancePredictor");
                VarianceResult raw;
                lock (singer.GetType().GetProperty("SessionLock").GetValue(singer)) raw = predictor.Process(ph);
                float frameMs = vocoder.frameMs();
                int head = DiffSingerUtils.headFrames, tail = DiffSingerUtils.tailFrames;
                var segments = DiffSingerUtils.PaddedSegments(ph, frameMs, head, tail);
                var dur = DiffSingerUtils.PaddedPhoneDurations(ph, frameMs, head, tail);
                int frames = dur.Sum();
                float[] Sample(float[] c, double def, Func<double,double> conv) =>
                    DiffSingerUtils.SampleCurve(ph, c, def, frameMs, frames, head, tail, conv).Select(x => (float)x).ToArray();
                var f0 = Sample(ph.pitches, 0, x => MusicMath.ToneToFreq(x * .01));
                var shifted = f0.Zip(Sample(ph.toneShift, 0, x => x), (x,d) => x*(float)Math.Pow(2,d/1200)).ToArray();
                var feeds = new List<NamedOnnxValue> {
                    Long("tokens", segments.Select(s => Convert.ToInt64(Call(singer,"PhonemeTokenize",s.Phoneme))).ToArray(),1,segments.Count),
                    Long("durations",dur.Select(x => (long)x).ToArray(),1,dur.Length),
                    Float("f0",vocoder.pitch_controllable ? shifted : f0,1,frames),
                    Float("depth",new[]{(float)Math.Min(Preferences.Default.DiffSingerDepth,cfg.maxDepth)},1),
                    Long("steps",new[]{(long)Preferences.Default.DiffSingerSteps},1),
                };
                if(cfg.use_lang_id) {
                    var lang=(Dictionary<string,int>)Field(singer,"languageIds");
                    var ids=DiffSingerUtils.PaddedLanguageIds(ph,frameMs,head,tail,p => lang.GetValueOrDefault(DiffSingerUtils.PhonemeLanguage(p),0));
                    feeds.Add(Long("languages",ids,1,ids.Length));
                }
                var manager=(DiffSingerSpeakerEmbedManager)Call(singer,"getSpeakerEmbedManager");
                feeds.Add(NamedOnnxValue.CreateFromTensor("spk_embed",manager.PhraseSpeakerEmbedByFrame(ph,dur,frameMs,frames,head,tail)));
                if(cfg.useKeyShiftEmbed) {
                    var range=cfg.augmentationArgs.randomPitchShifting.range;
                    double pos=range[1]==0 ? 0 : 12/range[1]/100, neg=range[0]==0 ? 0 : -12/range[0]/100;
                    feeds.Add(Float("gender",Sample(ph.gender,0,x => x<0 ? -x*pos : -x*neg),1,frames));
                }
                if(cfg.useSpeedEmbed) {
                    var vc=ph.curves.FirstOrDefault(c => c.Item1==DiffSingerUtils.VELC);
                    feeds.Add(Float("velocity",vc==null ? Enumerable.Repeat(1f,frames).ToArray() : Sample(vc.Item2,1,x => Math.Pow(2,(x-100)/100)),1,frames));
                }
                void Variance(string name,float[] values,float[] curve,string abbr,float min,float max) {
                    var predicted=DiffSingerUtils.ResamplePaddedCurve(values,frames,raw.headFrames,raw.tailFrames,head,tail,raw.frameMs,frameMs);
                    var input=predicted.Zip(Sample(curve,0,x=>x),DiffSingerUtils.VarianceDeltaFunctions[abbr]).Select(x=>Math.Clamp(x,min,max)).ToArray();
                    feeds.Add(Float(name,input,1,frames));
                }
                if(cfg.useBreathinessEmbed) Variance("breathiness",raw.breathiness,ph.breathiness,"brec",-96,0);
                if(cfg.useVoicingEmbed) Variance("voicing",raw.voicing,ph.voicing,"voic",-96,0);
                if(cfg.useTensionEmbed) Variance("tension",raw.tension,ph.tension,"tenc",-10,10);
                var expected=session.InputMetadata.Keys.OrderBy(x=>x).ToArray();
                if(!expected.SequenceEqual(feeds.Select(v=>v.Name).OrderBy(x=>x)))
                    throw new InvalidOperationException("Probe input names differ from native model");
                var cache=new DiffSingerCache((ulong)Field(singer,"acousticHash"),feeds);
                string cachePath=Path.Combine(PathManager.Inst.CachePath,cache.Filename);
                if(!File.Exists(cachePath)) throw new InvalidOperationException("Probe acoustic feeds do not match an existing native cache: " + cachePath);
                var dest=Path.Combine(root,$"phrase_{index:D3}.json");
                if(File.Exists(dest)) throw new IOException("Preserve prior probe export: " + dest);
                File.WriteAllText(dest,JsonSerializer.Serialize(new {
                    schema_version=1, phrase_index=index, position_ms=ph.positionMs,
                    frame_ms=frameMs,head_frames=head,tail_frames=tail, sample_rate=vocoder.sample_rate,
                    singer_location=singer.Location,acoustic_model=Path.Combine(singer.Location,cfg.acoustic),
                    acoustic_mel_base=cfg.mel_base,vocoder_mel_base=vocoder.mel_base,
                    vocoder_model=Path.Combine(vocoder.Location,vocoder.config.model),
                    native_acoustic_cache=cachePath,native_acoustic_cache_verified=true,
                    tensors=feeds.Select(Data),vocoder_f0=f0,
                    phones=ph.phones.Select(p=>new {p.phoneme,p.suffix,p.positionMs,p.endMs,p.tone}),
                }));
                ExportVarianceInputs(predictor,ph,raw,root,index);
                rows.Add(new { index,output=dest,frames,native_acoustic_cache=cachePath });
            }
            if(rows.Count!=requested.Count) throw new InvalidOperationException("Some requested phrase indices do not exist");
            return new Dictionary<string,object>{{"phrases",rows},{"project_modified",false},{"diagnostic_only",true}};
        }

        static void ExportVarianceInputs(DsVariance predictor,RenderPhrase ph,VarianceResult raw,string root,int index) {
            var cfg=(DsConfig)Field(predictor,"dsConfig");
            if(cfg.predict_dur || cfg.predict_energy || !cfg.predict_breathiness || !cfg.predict_voicing || !cfg.predict_tension || !cfg.useContinuousAcceleration)
                throw new InvalidOperationException("Unsupported variance probe layout");
            float frameMs=predictor.FrameMs;int head=DiffSingerUtils.headFrames,tail=DiffSingerUtils.tailFrames;
            var segments=DiffSingerUtils.PaddedSegments(ph,frameMs,head,tail);
            var dur=DiffSingerUtils.PaddedPhoneDurations(ph,frameMs,head,tail);int frames=dur.Sum();
            var vocabulary=(Dictionary<string,int>)Field(predictor,"phonemeTokens");
            var ling=new List<NamedOnnxValue>{
                Long("tokens",segments.Select(s=>(long)vocabulary[s.Phoneme]).ToArray(),1,segments.Count),
                Long("ph_dur",dur.Select(x=>(long)x).ToArray(),1,dur.Length),
            };
            if(cfg.use_lang_id) {
                var languages=(Dictionary<string,int>)Field(predictor,"languageIds");
                var ids=DiffSingerUtils.PaddedLanguageIds(ph,frameMs,head,tail,p=>languages.GetValueOrDefault(DiffSingerUtils.PhonemeLanguage(p),0));
                ling.Add(Long("languages",ids,1,ids.Length));
            }
            var linguisticCache=new DiffSingerCache((ulong)Field(predictor,"linguisticHash"),ling);
            var encoded=linguisticCache.Load() ?? throw new InvalidOperationException("Native linguistic probe cache not found");
            float[] Sample(float[] c) => DiffSingerUtils.SampleCurve(ph,c,0,frameMs,frames,head,tail,x=>x*.01).Select(x=>(float)x).ToArray();
            var pitch=Sample(ph.pitches).Zip(Sample(ph.toneShift),(x,y)=>x+y).ToArray();
            var variance=new List<NamedOnnxValue>{
                NamedOnnxValue.CreateFromTensor("encoder_out",encoded.First(v=>v.Name=="encoder_out").AsTensor<float>()),
                Long("ph_dur",dur.Select(x=>(long)x).ToArray(),1,dur.Length),
                Float("pitch",pitch,1,frames),
                Float("breathiness",new float[frames],1,frames),
                Float("voicing",new float[frames],1,frames),
                Float("tension",new float[frames],1,frames),
                NamedOnnxValue.CreateFromTensor("retake",new DenseTensor<bool>(Enumerable.Repeat(true,frames*3).ToArray(),new[]{1,frames,3})),
                Long("steps",new[]{(long)Preferences.Default.DiffSingerStepsVariance},1),
                NamedOnnxValue.CreateFromTensor("spk_embed",predictor.getSpeakerEmbedManager().PhraseSpeakerEmbedByFrame(ph,dur,frameMs,frames,head,tail)),
            };
            var cacheKey=new List<NamedOnnxValue>(variance){Long("result_cache_version",new[]{1L},1)};
            var cache=new DiffSingerCache((ulong)Field(predictor,"varianceHash"),cacheKey);
            var cached=cache.Load() ?? throw new InvalidOperationException("Native variance probe cache not found");
            foreach(var pair in new[]{("breathiness_pred",raw.breathiness),("voicing_pred",raw.voicing),("tension_pred",raw.tension)})
                if(!cached.First(v=>v.Name==pair.Item1).AsTensor<float>().ToArray().SequenceEqual(pair.Item2))
                    throw new InvalidOperationException("Native variance probe result mismatch");
            var predictorRoot=(string)Field(predictor,"rootPath");
            var dest=Path.Combine(root,$"variance_{index:D3}.json");
            if(File.Exists(dest)) throw new IOException("Preserve prior variance probe export");
            File.WriteAllText(dest,JsonSerializer.Serialize(new {
                schema_version=1,phrase_index=index,frame_ms=frameMs,head_frames=head,tail_frames=tail,
                variance_model=Path.Combine(predictorRoot,cfg.variance),variance_speaker_root=predictorRoot,
                native_variance_cache=Path.Combine(PathManager.Inst.CachePath,cache.Filename),native_variance_cache_verified=true,
                native_linguistic_cache=Path.Combine(PathManager.Inst.CachePath,linguisticCache.Filename),
                tensors=variance.Select(Data),linguistic_tensors=ling.Select(Data),cached_result=cached.Select(Data),
            }));
        }
    }
}

// Research-only extension of SHA-bound bridge copies. Never deployed to OpenUtau.
using System.Runtime.Loader;
using System.Runtime.InteropServices;
using OpenUtau.Core.DiffSinger;
using OpenUtau.Core.Render;
using OpenUtau.Core.Util;

namespace Agent2Utau.Bridge {
    static partial class Program {
        [DllImport("kernel32", CharSet = CharSet.Unicode, SetLastError = true)]
        static extern bool SetDllDirectory(string lpPathName);
        static string work, install;
        static void ResearchBoot(Dictionary<string,string> opt) {
            work = Path.GetFullPath(Req(opt,"work"));
            install = Path.GetFullPath(Req(opt,"install"));
            var workspace = Path.GetFullPath(Req(opt,"workspace"));
            if (!work.StartsWith(workspace + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new Exception("Private output must be inside workspace");
            AssemblyLoadContext.Default.Resolving += (ctx,name) => {
                var path = Path.Combine(install,name.Name+".dll");
                return File.Exists(path) ? ctx.LoadFromAssemblyPath(path) : null;
            };
            if (!SetDllDirectory(install)) throw new Exception("Native library search isolation failed");
            Directory.CreateDirectory(work);
            var pm = PathManager.Inst;
            foreach (var pair in new[]{("RootPath",install),("DataPath",work),("CachePath",Path.Combine(work,"Cache"))})
                typeof(PathManager).GetField("<"+pair.Item1+">k__BackingField",BindingFlags.Instance|BindingFlags.NonPublic)
                    .SetValue(pm,pair.Item2);
            Directory.CreateDirectory(pm.CachePath);
            string prefs=pm.PrefsFilePath;
            if (!File.Exists(prefs)) File.Copy(Path.Combine(install,"prefs.json"),prefs);
            // Pure locator override in the private preference copy; no sonic setting changes.
            Preferences.Default.AdditionalSingerPath=Path.Combine(install,"Singers");
            Console.Error.WriteLine("isolated data/cache/prefs: "+work);
        }
        static RenderPhrase Selected(UProject p, int index) {
            var all=p.parts.OfType<UVoicePart>().Where(x=>x.trackNo==0).SelectMany(x=>x.renderPhrases).ToArray();
            if (index!=21 && index!=22) throw new Exception("Only frozen phrase indices supported");
            if (index>=all.Length) throw new Exception("Missing phrase");
            return all[index];
        }
        static void Floats(string path,float[] samples) {
            var bytes=new byte[samples.Length*4]; Buffer.BlockCopy(samples,0,bytes,0,bytes.Length);
            using var stream=new FileStream(path,FileMode.CreateNew); stream.Write(bytes);
        }
        static Dictionary<string,object> Acquire(Dictionary<string,string> opt) {
            var project=LoadProject(Req(opt,"project")); int index=int.Parse(Req(opt,"indices"));
            var ph=Selected(project,index); var cts=new CancellationTokenSource();
            var renderer=new DiffSingerRenderer();
            var task=renderer.Render(ph,new OpenUtau.Core.Render.Progress(ph.phones.Length),0,cts,false);
            if (!ui.PumpUntil(()=>task.IsCompleted,TimeSpan.FromMinutes(12))) throw new Exception("Native acquisition timeout");
            var rendered=task.GetAwaiter().GetResult();
            if (rendered.samples==null || rendered.samples.Length==0) throw new Exception("Missing native technical render");
            var output=Path.GetFullPath(Req(opt,"out")); Directory.CreateDirectory(output);
            Floats(Path.Combine(output,"technical-native-DYN.f32"),rendered.samples);
            var info=RenderProbe.Export(project,output,index.ToString());
            info["technical_native_waveform_only"]=true;
            info["private_cache"]=PathManager.Inst.CachePath;
            info["leading_ms"]=rendered.leadingMs; info["position_ms"]=rendered.positionMs;
            return info;
        }
        static Dictionary<string,object> Dynamics(Dictionary<string,string> opt) {
            var project=LoadProject(Req(opt,"project")); int index=int.Parse(Req(opt,"indices"));
            var ph=Selected(project,index); var renderer=new DiffSingerRenderer();
            var output=Path.GetFullPath(Req(opt,"out")); Directory.CreateDirectory(output);
            var input=Path.GetFullPath(Req(opt,"input"));
            if (!input.StartsWith(Path.GetFullPath(Req(opt,"workspace"))+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
                throw new Exception("Only new workspace waves supported");
            var files=Directory.GetFiles(input,"*.f32").OrderBy(x=>x).ToArray();
            if (files.Length!=8) throw new Exception("Exactly eight frozen raw waves per phrase required");
            int? n=null;
            foreach(var file in files) {
                var bytes=File.ReadAllBytes(file);
                if(bytes.Length%4!=0) throw new Exception("Bad float length");
                var samples=new float[bytes.Length/4]; Buffer.BlockCopy(bytes,0,samples,0,bytes.Length);
                if(samples.Any(x=>!float.IsFinite(x))) throw new Exception("Nonfinite raw wave");
                if(n!=null && n.Value!=samples.Length) throw new Exception("Wave clocks differ"); n=samples.Length;
                var result=renderer.Layout(ph); result.samples=samples;
                Renderers.ApplyDynamics(ph,result);
                Floats(Path.Combine(output,Path.GetFileName(file)),result.samples);
            }
            var gains=renderer.Layout(ph); gains.samples=Enumerable.Repeat(1f,n.Value).ToArray();
            Renderers.ApplyDynamics(ph,gains); Floats(Path.Combine(output,"native-DYN-gain.f32"),gains.samples);
            return new Dictionary<string,object>{["position_ms"]=gains.positionMs,["leading_ms"]=gains.leadingMs,
                ["samples"]=n.Value,["files"]=8,["DYN_actual_core"]=true};
        }
    }
}

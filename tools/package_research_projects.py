"""Package exactly the three authorized Baishuo USTX originals, without media."""
from pathlib import Path
import argparse, hashlib, json, shutil, zipfile

PROJECTS={'huahai':'花海+4-有参by白烁.ustx','yuai':'雨爱-有参by白烁.ustx','lastpage':'最后一页-有参by白烁.ustx'}
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def package(source_dir,out):
    source_dir=Path(source_dir);out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'projects').mkdir()
    resources={}
    for key,name in PROJECTS.items():
        source=source_dir/name;destination=out/'projects'/name
        shutil.copyfile(source,destination)
        assert sha(source)==sha(destination)
        resources[key]=dict(file='projects/'+name,sha256=sha(destination),role='author original, research only',historical_audio_included=False)
    manifest=dict(schema=1,author='白烁',resources=resources,audio_included=False,production_profile=False)
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (out/'README.md').write_text('# 白烁工程研究资料\n\n三份USTX为用户授权打包的白烁原件，逐字节保留，哈希见manifest.json。只用于研究处理与反例，不能把作者曲线或参数路线搬入独立生成。\n\n原工程中的声库及音频路径引用保留，但包内没有音频、声库、模型、缓存或历史试听。旧版声库缺失时不能把当前重渲染称为历史作者声音。\n',encoding='utf8')
    archive=out/'baishuo-projects.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for file in [out/'README.md',out/'manifest.json',*(out/'projects'/n for n in PROJECTS.values())]: z.write(file,file.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==5 and all(Path(n).suffix.lower() in {'.ustx','.json','.md'} for n in z.namelist())
        for resource in resources.values(): assert hashlib.sha256(z.read(resource['file'])).hexdigest()==resource['sha256']
    return archive

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dir',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();print(package(a.source_dir,a.out))

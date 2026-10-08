"""Release gate: indexed tree has no audio/model/cache payloads; author pack matches."""
from pathlib import Path
import hashlib, json, re, subprocess, zipfile

ROOT=Path(__file__).resolve().parents[1]
AUDIO={'.wav','.wave','.mp3','.flac','.ogg','.opus','.m4a','.aac','.aif','.aiff','.wma','.mid','.midi','.caf','.ape','.amr','.mka'}
BINARIES={'.onnx','.pt','.pth','.ckpt','.safetensors','.npz','.npy','.dll','.exe'}
def media_magic(data):
    return data.startswith((b'fLaC',b'OggS',b'ID3',b'MThd')) or (data[:4] in [b'RIFF',b'RF64'] and data[8:12]==b'WAVE') or (len(data)>11 and data[4:8]==b'ftyp')
def check():
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf8').split('\0')
    for name in filter(None,paths):
        path=ROOT/name
        if not path.is_file(): raise ValueError(f'Indexed missing file: {name}; stage its deletion')
        if name.split('/')[0] in {'runs','demo','external','.local-archive','.venv'} or path.suffix.lower() in AUDIO|BINARIES:
            raise ValueError(f'Excluded payload indexed: {name}')
        with path.open('rb') as f: head=f.read(32)
        if media_magic(head): raise ValueError(f'Audio content indexed: {name}')
        if path.suffix.lower()=='.zip':
            with zipfile.ZipFile(path) as z:
                for entry in z.infolist():
                    if Path(entry.filename).suffix.lower() not in {'.ustx','.md','.json'} or media_magic(z.read(entry)[:32]):
                        raise ValueError(f'Unexpected ZIP member: {entry.filename}')
    manifest=json.loads((ROOT/'research/baishuo/manifest.json').read_text(encoding='utf8'))
    assert len(manifest['resources'])==3 and not manifest['audio_included']
    with zipfile.ZipFile(ROOT/'research/baishuo/baishuo-projects.zip') as z:
        assert len(z.namelist())==5
        for row in manifest['resources'].values():
            data=(ROOT/'research/baishuo'/row['file']).read_bytes()
            assert hashlib.sha256(data).hexdigest()==row['sha256'] and z.read(row['file'])==data
            indexed=subprocess.check_output(['git','show',':research/baishuo/'+row['file']],cwd=ROOT)
            assert indexed==data,'Author project bytes changed in Git index'
    assert subprocess.check_output(['git','show',':research/baishuo/baishuo-projects.zip'],cwd=ROOT)==(ROOT/'research/baishuo/baishuo-projects.zip').read_bytes()
    skill=ROOT/'skills/singing-expression-editor';links=0
    for path in skill.rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf8')):
            if '://' in link or link.startswith('#'): continue
            assert (path.parent/link.split('#')[0]).exists(),(path,link)
            links+=1
    installed=Path.home()/'.codex/skills/singing-expression-editor'
    if installed.exists():
        for p in skill.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                assert p.read_bytes()==(installed/p.relative_to(skill)).read_bytes(),p
    print(json.dumps(dict(indexed_files=len([p for p in paths if p]),audio_payloads=0,author_projects=3,zip_members=5,skill_links=links,checks='passed')))

if __name__=='__main__': check()

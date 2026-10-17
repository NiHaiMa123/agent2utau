"""Preserve early checker SHA and recheck final code without rewriting seals."""
import copy,json,os,sys
from pathlib import Path
from prepare_feedback_and_skill import ROOT,RUN,KNOW,REPORT,ENTRIES
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref,sha,check
from agent2utau.knowledge import collect_context,validate_context
import check_whole_song as checker

QA=ROOT/'runs/research/lastpage-whole-song-v03-delivery-audit-20261014'
NAME='J-method-whole-song-v03-checker-audit-20261014'
INDEX='table2-whole-song-v03-source-audited-index-20261014'
RESPONSE='RESP:LASTPAGE-J-METHOD-WHOLE-SONG-01'

def main():
    assert not QA.exists();manifest=load(RUN/'completion-manifest.json')
    refs=sum((manifest[k] for k in ['files','documents','entries','implementation','skill','published']),[]);check(refs)
    QA.mkdir(parents=True)
    for name in ENTRIES+['docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json']:
        p=QA/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    code=Path(checker.__file__).read_bytes();delimiter=b'def delivery():\n';assert code.count(delimiter)==1
    early=code.split(delimiter)[0]+b"if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()\n"
    p=QA/'checker-versions/native-fresh-checker.py.txt';p.parent.mkdir();p.write_bytes(early)
    early_hash=sha(p)
    assert all(load(RUN/f'evaluation/{k}-independent-check.json')['checker']['sha256']==early_hash for k in ['native','fresh'])
    final=QA/'checker-versions/final-checker.py.txt';final.write_bytes(code);assert sha(final)==sha(Path(checker.__file__))
    saved=[]
    def archive_output(path,value):
        path=Path(path);allowed=[RUN/f'evaluation/{k}-independent-check.json' for k in ['native','fresh','delivery']]
        assert path in allowed
        old=load(path);new=copy.deepcopy(value);old=copy.deepcopy(old)
        old.pop('checker');new.pop('checker');assert new==old,('Checker behaviour changed',path)
        save(QA/'evaluation'/path.name,value);saved.append(ref(QA/'evaluation'/path.name))
    checker.save=archive_output
    checker.native();checker.fresh();checker.delivery()
    # The original sealed data/check reports are unchanged, including older bindings.
    check(refs)
    output=dict(status='passed',kind='technical_checker_version_archive_and_readonly_recheck',
        original_completion_manifest=ref(RUN/'completion-manifest.json'),
        old_native_fresh_binding=dict(path=str(Path(checker.__file__).relative_to(ROOT)).replace('\\','/'),sha256=early_hash,
            exact_historical_bytes=ref(p),reason='Delivery function later appended to same file; original two checks bound earlier file version'),
        final_checker=ref(Path(checker.__file__)),final_checker_archive=ref(final),
        recheck_outputs=saved,results_except_checker_identity_exact=True,original_sealed_outputs_SHA_exact=True,
        actual_audio_or_model_executions=0,audio_values_changed=False,new_listening_feedback=0,agent_heard=False,
        measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),output)
    (REPORT/(NAME+'.md')).write_text('''# 整曲v03检查器版本追加审计

2026-10-14。最终封存SHA核对通过后发现：原生、fresh两检查记录的checker SHA对应早期检查器，随后同文件追加delivery函数，当前路径SHA已经改变。先前记录和封存manifest原字节保留。

按实际最终源码精确还原追加函数前版本，恢复字节SHA与两份原检查绑定完全相等并另行归档。使用最终检查器重读现有数据，三项独立检查全部通过，去除checker身份字段后与原结果逐字段精确相同。检查器算术、容差、目标、模型输入和音频未变；没有新模型/波形/试听。新归档与复检结果绑定在同名JSON。

知识索引只给整曲生产行追加技术版本审计引用；38行/12研究系列/1整曲记录保持，不新增听觉反馈或通用结论。原整曲报告、原检查记录、receipt与封存manifest不刷新，历史checker引用按本次归档解析，不冒称旧SHA等于当前路径字节。
''',encoding='utf8')
    idx=copy.deepcopy(load(KNOW/'table2-whole-song-v03-index-20261014.json'))
    row=next(r for r in idx['rows'] if r['id']==RESPONSE)
    row.setdefault('feedback_sources',[]).append(ref(REPORT/(NAME+'.json')))
    row['latest_technical_source_audit']=output;row['technical_source_audit_is_listening_feedback']=False
    idx.update(generator=ref(Path(__file__)),prior_index=ref(KNOW/'table2-whole-song-v03-index-20261014.json'))
    save(KNOW/(INDEX+'.json'),idx)
    (KNOW/(INDEX+'.md')).write_text('# 整曲v03当前来源索引\n\n保留38行，追加早期检查器字节归档与最终源码等式复检。没有新试听。完整来源见同名JSON。\n',encoding='utf8')
    reg=load(KNOW/'active-knowledge-sources.json');reg['response_indices']=[(KNOW/(INDEX+'.json')).relative_to(ROOT).as_posix()]
    (KNOW/'active-knowledge-sources.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for name in ENTRIES:
        f=ROOT/name;text=f.read_text(encoding='utf8');lines=text.splitlines(keepends=True);n=0
        relative=Path(os.path.relpath(REPORT/(NAME+'.md'),f.parent)).as_posix()
        for i,line in enumerate(lines):
            if '当前状态whole_song_J_method_v03_rendered_checked_pending_listening：' in line:
                lines[i]=line.rstrip()+f' [检查器版本审计]({relative})。\n';n+=1
        assert n==1;f.write_text(''.join(lines),encoding='utf8')
    packet=collect_context(['PER:S1'],['PARAM:C03.01'],[RESPONSE,'RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01'])
    decisions=[dict(id=r['id'],decision='keep_unknown' if r['id']==RESPONSE else 'use',reason='Production technical record/source versions confirmed; J local accepted.',
        condition_match='Current explicit record and technical supplement.',limitations='No new hearing; full-song quality pending.') for r in packet['records']]
    save(QA/'evaluation/knowledge-roundtrip.json',dict(packet=packet,receipt=validate_context(packet,decisions)))
    frozen=[r for r in refs if r['path'] not in ENTRIES+['docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json']]
    check(frozen)
    save(QA/'completion-manifest.json',dict(status='passed',files=[ref(p) for p in sorted(QA.rglob('*')) if p.is_file()],
        documents=[ref(REPORT/(NAME+s)) for s in ['.md','.json']]+[ref(KNOW/(INDEX+s)) for s in ['.md','.json']]+[ref(KNOW/'active-knowledge-sources.json')],
        entries=[ref(ROOT/n) for n in ENTRIES],implementation=ref(Path(__file__)),previous_data_unchanged=frozen,
        previous_original_completion_manifest=ref(RUN/'completion-manifest.json'),audio_changed=False,new_feedback=0))
    print('Exact early checker archived;final native/fresh/delivery rechecks equal;old seals/data unchanged;active index corrected.',flush=True)

if __name__=='__main__':main()

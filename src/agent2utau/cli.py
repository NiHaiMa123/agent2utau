"""Explicit source/function/native tools. Musical choices belong to the Agent."""
import argparse
from pathlib import Path
from .resources.config import load_config
from .util.jsonio import emit, exception_payload

def build_parser():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('doctor',help='Inspect local OpenUtau and singer resources')
    deploy=commands.add_parser('deploy-bridge');deploy.add_argument('--no-build',action='store_true')
    source=commands.add_parser('observe-source',help='Fresh source observations; no score/expression decisions')
    source.add_argument('source',type=Path);source.add_argument('--out',type=Path,required=True)
    source.add_argument('--steps',default='separate,asr,game,fcpe,rmvpe')
    source.add_argument('--seed',type=int,default=11);source.add_argument('--asr-model',default='large-v3-turbo')
    compile=commands.add_parser('compile-functions',help='[archived line] Compile a complete explicit Agent function plan')
    compile.add_argument('--plan',type=Path,required=True);compile.add_argument('--out',type=Path,required=True)
    compile.add_argument('--review-contract',type=Path,help='Version2: inventory/ledger/reviews/intent_lock/musical_critique; version1 is legacy candidate')
    align=commands.add_parser('align-lyrics',help='Locked lyrics + GAME notes -> normalized notes and deterministic mapping')
    align.add_argument('--lyrics',type=Path,required=True)
    align.add_argument('--game',type=Path,required=True)
    align.add_argument('--out',type=Path,required=True)
    align.add_argument('--hfa',type=Path)
    align.add_argument('--asr',type=Path)
    align.add_argument('--song-id',default='')
    align.add_argument('--baseline',type=Path)
    align.add_argument('--baseline-name')
    freeze=commands.add_parser('freeze-musical-intent',help='[archived line] Freeze source-based musical brief before numeric plan exists')
    for name in ['brief','inventory','plan','out']:freeze.add_argument('--'+name,type=Path,required=True)
    inventory=commands.add_parser('review-inventory',help='[archived line] Enumerate actual native vowels before reading decisions')
    inventory.add_argument('--project',type=Path,required=True);inventory.add_argument('--out',type=Path,required=True)
    for name in ['native-pitch','phonemes','provenance','context','sources']:inventory.add_argument('--'+name,type=Path)
    review=commands.add_parser('review-execution',help='[archived line] Shared independent facts, action mapping and local-review coverage')
    for name in ['project','inventory','out']:review.add_argument('--'+name,type=Path,required=True)
    for name in ['native-pitch','phonemes','provenance','ledger','plan','reviews','intent-lock','musical-critique','atlas']:review.add_argument('--'+name,type=Path)
    delivery=commands.add_parser('review-delivery',help='[archived line] Validate final USTX hash and shared review, including direct scripts')
    for name in ['project','out']:delivery.add_argument('--'+name,type=Path,required=True)
    for name in ['review','audio']:delivery.add_argument('--'+name,type=Path)
    knowledge=commands.add_parser('knowledge-context',help='[archived line] Retrieve explicit table1/table2 IDs; no automatic parameter selection')
    knowledge.add_argument('--entities',nargs='+',required=True);knowledge.add_argument('--parameters',nargs='+',required=True)
    knowledge.add_argument('--responses',nargs='*',default=[]);knowledge.add_argument('--absence-reason',default='')
    knowledge.add_argument('--out',type=Path,required=True)
    for name in ['inspect-project','export-pitch','export-phonemes','export-variance','export-render-probe','render-project','roundtrip']:
        command=commands.add_parser(name);command.add_argument('--project',type=Path,required=True)
        if name!='inspect-project': command.add_argument('--out',type=Path,required=True)
        if name=='export-render-probe': command.add_argument('--indices',required=True)
        if name=='render-project':
            command.add_argument('--timeout-min',type=int,default=20)
            command.add_argument('--mixdown',action='store_true')
            command.add_argument('--execution-review',type=Path,help='Current final project review; absent means unreviewed candidate')
    return parser

def main(argv=None):
    args=build_parser().parse_args(argv);cfg=load_config()
    try:
        if args.command=='freeze-musical-intent':
            from .evaluation.musical_review import freeze_intent
            result=freeze_intent(args.brief,args.inventory,args.plan,args.out)
        elif args.command=='review-inventory':
            from .evaluation.execution_review import build_inventory
            result=build_inventory(args.project,args.out,args.native_pitch,args.phonemes,args.provenance,args.context,args.sources)
        elif args.command=='review-execution':
            from .evaluation.execution_review import review_execution
            result=review_execution(args.project,args.inventory,args.out,args.native_pitch,args.phonemes,args.provenance,args.ledger,args.plan,args.reviews,atlas_path=args.atlas,intent_lock=args.intent_lock,musical_critique=args.musical_critique)
        elif args.command=='review-delivery':
            from .evaluation.execution_review import delivery_review
            result=delivery_review(args.project,args.out,args.review,args.audio)
        elif args.command=='knowledge-context':
            from .knowledge import collect_context
            import json
            packet=collect_context(args.entities,args.parameters,args.responses,args.absence_reason)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:json.dump(packet,f,ensure_ascii=False,indent=2)
            result=dict(status='completed',packet=str(args.out),record_ids=[r['id'] for r in packet['records']],automatic_parameter_selection=False)
        elif args.command=='doctor':
            from .resources.doctor import probe
            result=probe(cfg)
        elif args.command=='deploy-bridge':
            from .openutau.bridge import build_bridge, deploy_bridge
            result=dict(status='completed',bridge=str(deploy_bridge(cfg,None if args.no_build else build_bridge())))
        elif args.command=='observe-source':
            from .workflow import observe_source
            result=observe_source(args.source,args.out,cfg,args.steps.split(','),args.seed,args.asr_model)
        elif args.command=='align-lyrics':
            from .alignment.pipeline import run_alignment
            result=run_alignment(args.lyrics,args.game,args.out,hfa_path=args.hfa,asr_path=args.asr,
                                  song_id=args.song_id,baseline_ustx=args.baseline,baseline_name=args.baseline_name)
        elif args.command=='compile-functions':
            from .workflow import compile_functions
            result=compile_functions(args.plan,args.out,cfg,args.review_contract)
        else:
            from .openutau.bridge import run_bridge
            name={'inspect-project':'inspect','render-project':'render'}.get(args.command,args.command)
            options=[name,'--project',str(args.project.resolve())]
            if hasattr(args,'out'): options+=['--out',str(args.out.resolve())]
            if args.command=='export-render-probe': options+=['--indices',args.indices]
            timeout=600
            if args.command=='render-project':
                from .evaluation.execution_review import validate_review
                if args.execution_review:validate_review(args.project,args.execution_review,cfg)
                options+=['--timeout',str(args.timeout_min)];timeout=args.timeout_min*60+120
                if args.mixdown: options+=['--mixdown']
            result=run_bridge(cfg,options,timeout=timeout)
            if args.command=='render-project' and result.get('ok'):
                from .evaluation.execution_review import delivery_review
                receipts=[]
                for row in result.get('files',[]):
                    audio=Path(row['path']);target=audio.with_suffix('.review.json')
                    receipts.append(delivery_review(args.project,target,args.execution_review,audio))
                result['delivery_reviews']=receipts
                result['status']='rendered_workflow_reviewed' if receipts and all(r['workflow_review_complete'] for r in receipts) else 'rendered_technical_candidate' if receipts and all(r['technical_execution_complete'] for r in receipts) else 'rendered_candidate_review_incomplete'
        emit(result)
        return 1 if result.get('ok') is False or result.get('status')=='failed' else 0
    except Exception as e:
        emit(exception_payload(e));return 1

if __name__=='__main__': raise SystemExit(main())

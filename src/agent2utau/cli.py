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
    compile=commands.add_parser('compile-functions',help='Compile a complete explicit Agent function plan')
    compile.add_argument('--plan',type=Path,required=True);compile.add_argument('--out',type=Path,required=True)
    for name in ['inspect-project','export-pitch','export-phonemes','export-variance','export-render-probe','render-project','roundtrip']:
        command=commands.add_parser(name);command.add_argument('--project',type=Path,required=True)
        if name!='inspect-project': command.add_argument('--out',type=Path,required=True)
        if name=='export-render-probe': command.add_argument('--indices',required=True)
        if name=='render-project':
            command.add_argument('--timeout-min',type=int,default=20)
            command.add_argument('--mixdown',action='store_true')
    return parser

def main(argv=None):
    args=build_parser().parse_args(argv);cfg=load_config()
    try:
        if args.command=='doctor':
            from .resources.doctor import probe
            result=probe(cfg)
        elif args.command=='deploy-bridge':
            from .openutau.bridge import build_bridge, deploy_bridge
            result=dict(status='completed',bridge=str(deploy_bridge(cfg,None if args.no_build else build_bridge())))
        elif args.command=='observe-source':
            from .workflow import observe_source
            result=observe_source(args.source,args.out,cfg,args.steps.split(','),args.seed,args.asr_model)
        elif args.command=='compile-functions':
            from .workflow import compile_functions
            result=compile_functions(args.plan,args.out,cfg)
        else:
            from .openutau.bridge import run_bridge
            name={'inspect-project':'inspect','render-project':'render'}.get(args.command,args.command)
            options=[name,'--project',str(args.project.resolve())]
            if hasattr(args,'out'): options+=['--out',str(args.out.resolve())]
            if args.command=='export-render-probe': options+=['--indices',args.indices]
            timeout=600
            if args.command=='render-project':
                options+=['--timeout',str(args.timeout_min)];timeout=args.timeout_min*60+120
                if args.mixdown: options+=['--mixdown']
            result=run_bridge(cfg,options,timeout=timeout)
        emit(result)
        return 1 if result.get('ok') is False or result.get('status')=='failed' else 0
    except Exception as e:
        emit(exception_payload(e));return 1

if __name__=='__main__': raise SystemExit(main())

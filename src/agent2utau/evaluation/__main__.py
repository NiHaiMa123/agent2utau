"""Explicit independent evaluation command; never searches caches or old songs."""
import argparse, json, sys
from dataclasses import asdict
from pathlib import Path
from .features import Thresholds
from .independent import evaluate


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--role',choices=['current_agent_generated','author_research_only'],default='current_agent_generated')
    for arg in ['native-pitch','phonemes','provenance','feedback','config']:p.add_argument('--'+arg,type=Path)
    args=p.parse_args(argv)
    try:
        cfg=Thresholds(**json.loads(args.config.read_text(encoding='utf8'))) if args.config else Thresholds()
        result=evaluate(args.project,args.out,args.role,args.native_pitch,args.phonemes,args.provenance,args.feedback,cfg,['python','-m','agent2utau.evaluation',*(argv if argv is not None else sys.argv[1:])])
        print(json.dumps(dict(status='completed',stage=result['stage'],findings=result['findings_counts'],vowels=result['vowel_evaluation']),ensure_ascii=False));return 0
    except Exception as e:
        print(json.dumps(dict(status='failed',error=str(e)),ensure_ascii=False));return 1


if __name__=='__main__':raise SystemExit(main())

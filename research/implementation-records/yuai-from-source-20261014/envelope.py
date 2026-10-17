"""Explicit Agent musical level decisions after this run's actual vowel review."""
from source import ROOT,RUN,load,save,sha,ref
from design import cfg,export
import yaml,numpy as np,sys,copy

# UI units: 10 -> 1dB. These are new per-line musical choices following the
# current raw-energy review, not inverse-RMS normalization or historic doses.
# (line, word/phase targets). Consonant connections within a line are carried;
# AP/SP and line-release cores retain default gain.
CHOICES={0:{0:3,2:10,3:12,4:0},1:{5:0,9:5,10:18,12:22,13:16},3:{17:0,18:8,19:12,20:6,21:0},
 6:{31:0,32:22,33:26},8:{40:0,41:4,42:12,43:8,44:10,45:3,46:10},
 11:{58:12,59:18,60:16,61:8,62:7},12:{63:0,65:0,66:18,67:8},
 13:{68:14,70:12,71:18,72:9,74:0,75:9,76:10,77:0,78:0,79:9,80:12},
 14:{81:0,83:0,85:10,86:0,87:0,88:3},15:{89:4,90:10,91:12,92:6,93:6},16:{94:0,95:0,96:16,97:12,98:20},18:{107:0,108:12,109:5},
 20:{115:0,117:9,118:17,119:6},21:{120:6,121:10,122:0,126:0,127:3,128:6,129:10,130:0,131:2,132:0},
 22:{133:6,134:0,137:16,138:0,139:0,140:8},23:{141:0,142:0,143:0,144:4,145:14},24:{146:0,147:0,148:0,149:10,150:14},25:{151:0,152:12,153:0,155:6,156:0,158:14},
 33:{194:0,195:12,196:24},35:{203:0,205:8,206:4,207:5,208:0,209:10},36:{210:0,212:0,214:5,215:12,216:10},
 38:{221:4,222:8,223:4,224:13,225:10},39:{226:8,227:10,228:0,229:18,230:8},
 40:{231:18,232:14,233:8,234:18,235:12,236:13,237:8,238:17,239:14,240:3,241:12,242:18,243:20},
 41:{244:0,245:2,246:0,247:0,248:10,249:0,250:0,251:6},42:{252:12,253:14,254:16,255:4,256:0},43:{257:0,258:0,259:16,260:13,261:19},
 44:{262:0,263:0,264:5,265:8,266:12,267:0,268:0,269:5},45:{270:0,271:10,272:4},46:{273:0,274:10,275:0,276:0,277:10},
 48:{283:0,284:16,285:0,286:0,287:0,288:4,289:0,290:8,291:8,292:20,293:0,294:0,295:0},
 49:{296:0,297:0,298:0,299:0,300:20,301:12,302:6,303:5},50:{304:0,305:5,306:6,307:8,308:16},51:{309:0,310:0,311:10,312:20,313:22},
 52:{314:0,315:0,316:0,317:0,318:8,319:12,320:0,321:7},53:{322:4,323:13,324:7,325:12,326:16},
 54:{327:0,328:10,329:0,330:0,331:0,332:0,333:0,334:6,335:8,336:14,337:0,338:3,339:0},55:{340:12,341:0,342:0,343:0,344:10,345:0,346:0,347:20},
 56:{348:0,349:0,350:2,351:0,352:9},57:{353:0,354:0,355:10,356:13,357:10},58:{358:2,359:5,360:4,361:4,362:10,363:5,364:0,365:0},59:{366:0,367:0,368:7,369:9,370:6}}

def q5(u):return u*u*u*(10+u*(-15+6*u))
def build():
    from agent2utau.knowledge import collect_context,validate_context
    old=load(RUN/'design/knowledge_context.json');entity=['ACO:L1','EVT:L2','PER:S1'];params=['PARAM:C01.01','PARAM:C02.02','PARAM:C03.01','PARAM:C10.01','PARAM:C11.01','PARAM:C12.01','PARAM:C13.01','PARAM:C14.01','PARAM:C19.01','PARAM:C20.01','PARAM:C20.03']
    packet=collect_context(entity,params,[],absence_reason='User excludes author/history; source-only independent current production; general field definitions only.',catalogue_path=ROOT/'docs/reports/yuai/from-source-20261014-knowledge-scope.json')
    decisions=[dict(id=r['id'],decision='use',reason='Use generic current parameter definition/consumer contract; musical values chosen independently.',condition_match='Current source-only Yuai production; speaker CLR plus cl01/cl03 and output DYN explicitly included.',limitations='No historical response/recipe/dose admitted; technical definitions do not establish naturalness.') for r in packet['records']]
    save(RUN/'design/knowledge_context-v2.json',packet);save(RUN/'design/knowledge-decisions-v2.json',decisions);save(RUN/'evaluation/knowledge-receipt-v2.json',validate_context(packet,decisions))
    doc=yaml.safe_load((RUN/'compiled/project.ustx').read_text(encoding='utf8'));words=load(RUN/'design/native-word-decisions.json');ledger={w['word']:w for w in load(RUN/'design/word-ledger.json')};events=[];perword=[]
    for lid,choices in CHOICES.items():
        group=[w for w in words if w['line']==lid];a=group[0]['native_nucleus_s'][0];b=group[-1]['native_nucleus_s'][1];pi=ledger[group[0]['word']]['context'];part=doc['voice_parts'][pi]
        anchors=[[a,0]]
        for w in group:
            if w['word'] in choices:
                va,vb=w['native_nucleus_s'];t=va+min(.065,(vb-va)*.3);value=choices[w['word']]
                anchors.append([t,value])
        # Chosen positive support releases before the nucleus is over;
        # this is not a hard gate or a normalization of the final syllable.
        anchors.append([b-min(.045,(b-a)*.08),0]);anchors.sort();assert all(y[0]>x[0] for x,y in zip(anchors,anchors[1:]))
        xs=list(range(int(np.floor(a*960))-part['position']-5,int(np.ceil(b*960))-part['position']+6,5));ys=[]
        for tick in xs:
            t=(tick+part['position'])/960
            if t<anchors[0][0] or t>anchors[-1][0]:v=0
            else:
                k=max(0,min(len(anchors)-2,np.searchsorted([z[0] for z in anchors],t,side='right')-1));x,y=anchors[k:k+2];u=(t-x[0])/(y[0]-x[0]);v=x[1]+(y[1]-x[1])*q5(u)
            ys.append(round(v))
        part.setdefault('_dyn',{}).update(dict(zip(xs,ys)))
        events.append(dict(line=lid,part=pi,support_s=[a,b],nodes=anchors,chosen_peak_db=max(choices.values())*.1,
            purpose='当前真实元音审阅后，弱承载及推进字有限正向承托，原本强字少加/保持；不追平全部字。词内连接连续，释放和AP/SP保持。',
            source='Agent musical decision from this new waveform',cause_verified=False))
    for part in doc['voice_parts']:
        d=part.pop('_dyn',None)
        if d:xs=sorted(d);part['curves'].append(dict(abbr='dyn',xs=xs,ys=[d[x] for x in xs]))
    for w in words:
        e=next((e for e in events if e['line']==w['line']),None)
        perword.append(dict(word=w['word'],char=w['char'],line=w['line'],decision='有限乐句承托' if e else '保持默认输出包络',
            selected_stored_value=CHOICES.get(w['line'],{}).get(w['word']),scope='Current entire line carries transitions; value is not exact perceived loudness',
            reason=e['purpose'] if e else '当前乐句已有清晰发声层次/自然回收；不因短窗低值自动加量。当前原生预测保持；听觉仍待用户确认。',
            raw_energy=ref(RUN/'evaluation/whole-vowel-energy-raw.json'),ear_truth=False))
    p=RUN/'score/agent-level-base.ustx';p.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    plan=load(RUN/'design/functions.json');plan['project']=str(p);plan['input_hashes'].pop(str(RUN/'score/agent-functions-base.ustx'));plan['input_hashes'][str(p)]=sha(p)
    plan['knowledge_context']=dict(path=str(RUN/'design/knowledge_context-v2.json'),sha256=sha(RUN/'design/knowledge_context-v2.json'),decisions=decisions)
    save(RUN/'design/functions-level.json',plan);save(RUN/'design/envelope-events.json',events);save(RUN/'design/whole-vowel-level-decisions.json',perword)
    from agent2utau.workflow import compile_functions
    r=compile_functions(RUN/'design/functions-level.json',RUN/'compiled-level',cfg());print('Level native compiled',r['native_max_error_c'],len(events),'line envelopes',flush=True)
    assert load(RUN/'compiled-level/pitch.json')['phrases']==load(RUN/'compiled/pitch.json')['phrases']
    assert load(RUN/'compiled-level/phones.json')['parts']==load(RUN/'compiled/phones.json')['parts']
    export('export-dynamics',RUN/'compiled-level/project.ustx',RUN/'evaluation/dynamics-level.json') if False else None

def render(audit_label='level',wordpath=None):
    import subprocess,time
    from agent2utau.openutau.bridge import run_bridge
    before={str(p):sha(p) for p in (RUN/'native-runtime/Cache').iterdir() if p.is_file()};out=RUN/'native-level';out.mkdir();save(out/'before-current-cache.json',before)
    r=run_bridge(cfg(),['render','--project',str(RUN/'compiled-level/project.ustx'),'--out',str(out/'native.wav'),'--timeout','14'],timeout=890);save(out/'receipt.json',r);assert r['ok'],r
    assert all(sha(p)==h for p,h in before.items())
    exe=RUN/'native-runtime/a2u-levelprobe-v15.exe';result=subprocess.run([str(exe),'export-dynamics','--project',str(RUN/'compiled-level/project.ustx'),'--out',str(RUN/'evaluation/dynamics-level.json')],cwd=exe.parent,capture_output=True,encoding='utf8',errors='replace');save(RUN/'logs/dynamics-level-export.json',dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr));assert result.returncode==0
    save(out/'cache-reuse-audit.json',dict(current_run_cache_SHA_preserved=True,old_or_author_cache_read=False,postprocessing_only=True,
        new_cache_files=[str(p) for p in (RUN/'native-runtime/Cache').iterdir() if p.is_file() and str(p) not in before],raw_prediction_reuse='only frozen SHA-bound waveform and prediction generated in this same fresh production',native_Core_ApplyDynamics=True))
    from audit import energy
    energy(audit_label,out/'native_vocal.wav',wordpath);print('Final native envelope rendered; own current raw cache preserved',flush=True)

if __name__=='__main__':{'build':build,'render':render}[sys.argv[1]]()

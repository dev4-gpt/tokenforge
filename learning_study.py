"""Bounded Luminal feedback study and an authentic repair trace.

python learning_study.py --repair-only
python learning_study.py --replicates 2 --rounds 2 --agents 3 --max-minutes 25
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
from tokenforge import agents,harness
from tokenforge.memory import Memory
from tokenforge.reporting import load_bundle,clean_error


def worker(payload):
    if payload['task']=='propose':
        os.environ['MODEL_B']=''
        p=agents.propose(payload['agent'],payload['round'],payload['code'],payload.get('tps',0),payload.get('memories',[]),timeout=20,allow_fallback=False,max_retries=0)
        return asdict(p)
    r=harness.evaluate(payload['code'],[harness.Item(**x) for x in payload['items']],payload.get('runs',3))
    return asdict(r)


def invoke(payload, deadline):
    remaining=deadline-time.monotonic()
    if remaining<=0: return {'status':'timeout','code':'','error':'study deadline reached','tps':[]}
    try:
        p=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker'],input=json.dumps(payload),capture_output=True,text=True,timeout=min(60,remaining))
        if p.returncode: return {'status':'crash','code':'','error':p.stderr[-300:],'tps':[]}
        return json.loads(p.stdout)
    except subprocess.TimeoutExpired:
        return {'status':'timeout','code':'','error':'60-second proposal/evaluation or study deadline reached','tps':[]}


def evaluate(code,items,deadline,runs=3):
    value=invoke({'task':'evaluate','code':code,'items':[asdict(i) for i in items],'runs':runs},deadline)
    return harness.Result(value.get('status','invalid_evaluation'),value.get('tps',[]),clean_error(value.get('error_snippet',value.get('error',''))),value.get('spread',0))


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str)+'\n')


def repair(out):
    deadline=time.monotonic()+180
    bundle=load_bundle('r-20261011-170439')
    source=next(c for c in bundle['candidates'] if c['round']==3 and c['status']=='compile_error')
    mem=Memory(jsonl_path=out/'repair-candidates.jsonl')
    retrieved=mem.retrieve('dispatch_apply_f callback block incompatible function pointer',bundle['run_id'],k_wins=0,k_fails=12)
    context=[r for r in retrieved if str(r['_id'])==source['id']]
    if not context:
        raise RuntimeError('Source failure was not retrieved; refusing to fabricate a trace')
    for row in context:
        row['error_snippet']=clean_error(row.get('error_snippet',''))
    splits=harness.load_splits();items=splits['dev']+splits['validation']
    harness.build_reference(items)
    original=evaluate(source['code'],items,deadline,runs=1)
    proposal=invoke({'task':'propose','agent':0,'round':0,'code':source['code'],'tps':0,'memories':context},deadline)
    result=evaluate(proposal.get('code',''),items,deadline,runs=1) if proposal.get('code') else harness.Result('no_code',error_snippet=proposal.get('error',''))
    lesson={'rule':'dispatch_apply_f needs a C callback void (*)(void*, size_t), not an Objective-C block.','source_failure_id':source['id'],'verified':original.status=='compile_error' and result.status=='ok','scope':[harness.key(i) for i in items]}
    doc={'run_id':'r-repair-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'),'round':1,'agent':0,'model':proposal.get('model',''),'provider':proposal.get('provider','none'),'status':result.status,'code':proposal.get('code',''),'note':proposal.get('note',''),'error_snippet':result.error_snippet,'parent_id':source['id'],'retrieved_ids':[r['_id'] for r in context],'memory_context':context,'prompt':proposal.get('prompt',''),'lesson':lesson,'llm_tokens':proposal.get('tokens',0)}
    repair_id=mem.add(doc)
    trace={'source_run_id':bundle['run_id'],'source_id':source['id'],'repair_id':repair_id,'retrieved_ids':doc['retrieved_ids'],'retrieval_method':context[0]['retrieval_method'],'original_status':original.status,'repair_status':result.status,'checks':{'original':asdict(original),'repair':asdict(result)},'lesson':lesson,'provider':doc['provider'],'model':doc['model'],'llm_tokens':doc['llm_tokens'],'prompt':doc['prompt'],'memory_context':context,'original_code':source['code'],'repaired_code':doc['code'],'interpretation':'Observed feedback-use and repair trace; not a causal memory ablation.'}
    save(out/'repair.json',trace)
    print(json.dumps({k:trace[k] for k in ('source_id','retrieval_method','original_status','repair_status')}),flush=True)


def study(args):
    protocol_path=ROOT/'learning_protocol.json'
    committed=subprocess.check_output(['git','show','HEAD:learning_protocol.json'],cwd=ROOT)
    if committed!=protocol_path.read_bytes(): raise RuntimeError('Protocol must be committed unchanged before optimization')
    protocol=json.loads(committed)
    digest=hashlib.sha256(json.dumps(protocol['fresh'],sort_keys=True).encode()).hexdigest()
    if digest!=protocol['fresh_sha256']: raise RuntimeError('Fresh split hash mismatch')
    if min(args.replicates,args.rounds,args.agents)<=0 or args.max_minutes<=0: raise ValueError('Positive budgets required')
    out=Path(args.output_dir)
    if (out/'summary.json').exists(): raise RuntimeError('Study already recorded; choose a new output directory')
    deadline=time.monotonic()+min(args.max_minutes,25)*60
    splits=harness.load_splits();dev,val=splits['dev'],splits['validation']
    fresh=[harness.Item(**i) for i in protocol['fresh']]
    harness.build_reference(dev+val+fresh)
    baseline=harness.BASELINE_KERNEL
    states=[];proposals=0
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    for rep in range(args.replicates):
        conditions=['champion-only','history'] if rep%2==0 else ['history','champion-only']
        for condition in conditions:
            if time.monotonic()>=deadline or proposals>=24: break
            run_id=f'r-study-{stamp}-{rep+1}-{condition}'
            mem=Memory(jsonl_path=out/f'{run_id}.jsonl')
            champion=baseline;champion_id=None;rounds=[];rows=[]
            for round_idx in range(1,args.rounds+1):
                if time.monotonic()>=deadline or proposals+args.agents>24: break
                b=evaluate(baseline,dev,deadline)
                current=evaluate(champion,dev,deadline)
                if b.status!='ok' or current.status!='ok': break
                contexts=[mem.retrieve(agents.STRATEGIES[(i+round_idx)%len(agents.STRATEGIES)],run_id) if condition=='history' else [] for i in range(args.agents)]
                jobs=[{'task':'propose','agent':i,'round':round_idx,'code':champion,'tps':current.mean_tps,'memories':contexts[i]} for i in range(args.agents)]
                with ThreadPoolExecutor(args.agents) as pool:
                    props=list(pool.map(lambda payload:invoke(payload,deadline),jobs))
                proposals+=len(props)
                scored=[]
                for i,p in enumerate(props):
                    r=evaluate(p['code'],dev,deadline) if p.get('code') else harness.Result('no_code',error_snippet=p.get('error',''))
                    doc={'run_id':run_id,'round':round_idx,'agent':i,'model':p.get('model',''),'provider':p.get('provider','none'),'strategy':p.get('strategy',''),'note':p.get('note',''),'code':p.get('code',''),'prompt':p.get('prompt',''),'retrieved_ids':[m['_id'] for m in contexts[i]],'memory_context':contexts[i],'parent_id':champion_id,'status':r.status,'error_snippet':r.error_snippet,'dev_tps':r.tps,'dev_speedup':harness.speedup(r,b),'val_speedup':None,'llm_tokens':p.get('tokens',0),'promoted':False}
                    scored.append(doc)
                ok=sorted([d for d in scored if d['status']=='ok'],key=lambda d:-d['dev_speedup'])
                if ok and ok[0]['dev_speedup']>harness.speedup(current,b)*1.05:
                    best=ok[0]
                    bv=evaluate(baseline,val,deadline)
                    cv=evaluate(champion,val,deadline)
                    nv=evaluate(best['code'],val,deadline)
                    best['val_speedup']=harness.speedup(nv,bv)
                    if nv.status=='ok' and cv.status=='ok' and best['val_speedup']>harness.speedup(cv,bv): best['promoted']=True
                for doc in scored:
                    doc_id=mem.add(doc);doc['_id']=doc_id
                    rows.append(doc)
                    if doc['promoted']: champion=doc['code'];champion_id=doc_id
                rounds.append({'round':round_idx,'n_total':len(scored),'n_ok':len(ok),'champion_id':champion_id})
                save(out/f'{run_id}.json',{'condition':condition,'rounds':rounds,'candidates':rows,'champion_code':champion})
                print(f'{run_id} round {round_idx}: {len(ok)}/{len(scored)} passed',flush=True)
            states.append({'run_id':run_id,'condition':condition,'replicate':rep+1,'rounds_completed':len(rounds),'attempts':len(rows),'passed':sum(d['status']=='ok' for d in rows),'code_failures':sum(d['status'] in ('compile_error','wrong_output','rejected','crash') for d in rows),'no_code':sum(d['status']=='no_code' for d in rows),'tokens':sum(d['llm_tokens'] for d in rows),'best_dev_speedup':max([d['dev_speedup'] for d in rows]+[1]),'champion_code':champion,'champion_id':champion_id})
            save(out/'progress.json',states)
    # Optimization is over: freeze winners before using fresh-test outcomes.
    frozen=[{'run_id':s['run_id'],'kernel_sha256':hashlib.sha256(s['champion_code'].encode()).hexdigest()} for s in states]
    save(out/'frozen.json',frozen)
    base_fresh=evaluate(baseline,fresh,deadline)
    for s in states:
        result=evaluate(s.pop('champion_code'),fresh,deadline)
        s['fresh_status']=result.status
        s['fresh_speedup']=harness.speedup(result,base_fresh) if result.status=='ok' and base_fresh.status=='ok' else None
        s['fresh_tps']=result.tps
    complete=proposals==args.replicates*args.rounds*args.agents*2 and all(s['rounds_completed']==args.rounds and s['fresh_status']=='ok' for s in states) and base_fresh.status=='ok'
    save(out/'summary.json',{'protocol_sha256':hashlib.sha256(committed).hexdigest(),'fresh_sha256':digest,'complete':complete,'proposals':proposals,'baseline_fresh_status':base_fresh.status,'baseline_fresh_tps':base_fresh.tps,'conditions':states,'interpretation':protocol['interpretation'],'terminated_at_budget':time.monotonic()>=deadline})
    print(f'Study complete={complete}; {proposals} proposals; artifacts in {out}',flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('--repair-only',action='store_true')
    ap.add_argument('--replicates',type=int,default=2)
    ap.add_argument('--rounds',type=int,default=2)
    ap.add_argument('--agents',type=int,default=3)
    ap.add_argument('--max-minutes',type=float,default=25)
    ap.add_argument('--output-dir',default='results/learning-study')
    args=ap.parse_args()
    if args.worker:
        print(json.dumps(worker(json.loads(sys.stdin.read()))));return
    if args.repair_only: repair(Path(args.output_dir))
    else: study(args)
if __name__=='__main__': main()

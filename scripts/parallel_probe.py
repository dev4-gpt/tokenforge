"""Small observed parallel-vs-serial Luminal proposal study; never promotes a kernel."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from learning_study import invoke, evaluate
from tokenforge import harness

def main():
    output=ROOT/'results/parallelism.json'
    if output.exists(): raise RuntimeError('Probe already recorded; do not overwrite evidence')
    started=datetime.now(timezone.utc).isoformat()
    deadline=time.monotonic()+300
    conditions=[]
    # Same original baseline, strategy slots, mode, output budget and empty memory in both arms.
    for condition in ('parallel','serial'):
        origin=time.monotonic()
        def job(agent):
            start=time.monotonic()-origin
            p=invoke({'task':'propose','agent':agent,'round':0,'code':harness.BASELINE_KERNEL,'tps':0,'memories':[]},deadline)
            end=time.monotonic()-origin
            return {'agent':agent,'start_seconds':start,'end_seconds':end,'duration_seconds':end-start,**p}
        if condition=='parallel':
            with ThreadPoolExecutor(3) as pool: rows=list(pool.map(job,[0,2,4]))
        else: rows=[job(agent) for agent in [0,2,4]]
        conditions.append({'condition':condition,'proposal_wall_seconds':time.monotonic()-origin,'proposals':rows})
        print(condition,round(conditions[-1]['proposal_wall_seconds'],2),flush=True)
        output.write_text(json.dumps({'started_utc':started,'conditions':conditions,'complete':False},indent=2))
    dev=harness.load_splits()['dev'];harness.build_reference(dev)
    baseline=evaluate(harness.BASELINE_KERNEL,dev,deadline,runs=1)
    for condition in conditions:
        for row in condition['proposals']:
            result=evaluate(row.get('code',''),dev,deadline,runs=1) if row.get('code') else harness.Result('no_code',error_snippet=row.get('error',''))
            row['evaluation']={'status':result.status,'tps':result.tps,'dev_speedup':harness.speedup(result,baseline),'error':result.error_snippet}
        condition['valid_candidates']=sum(row['evaluation']['status']=='ok' for row in condition['proposals'])
        condition['recorded_tokens']=sum(row.get('tokens',0) for row in condition['proposals'])
    complete=baseline.status=='ok' and all(row.get('provider')=='luminal' and row.get('code') for c in conditions for row in c['proposals'])
    result={'started_utc':started,'source_run_id':'r-20261011-170439','baseline_sha256':hashlib.sha256(harness.BASELINE_KERNEL.encode()).hexdigest(),'conditions':conditions,'complete':bool(complete),'wall_ratio_serial_over_parallel':conditions[1]['proposal_wall_seconds']/conditions[0]['proposal_wall_seconds'],'interpretation':'One matched three-proposal batch per arm, parallel first. This measures observed proposal latency and validity, not a causal quality advantage or a six-agent scaling estimate. CPU evaluations remain sequential. No kernel was promoted.'}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('complete','wall_ratio_serial_over_parallel')}),flush=True)
if __name__=='__main__':main()

"""Paired, randomized measurements of the recorded promotions; never changes the champion."""
import argparse
import hashlib
import json
import platform
import random
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from tokenforge import harness
from tokenforge.reporting import load_bundle

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',default='r-20261011-170439')
    ap.add_argument('--blocks',type=int,default=10)
    ap.add_argument('--output',default='results/comparison.json')
    args=ap.parse_args()
    if args.blocks<2: ap.error('at least two blocks required')
    data=load_bundle(args.run)
    splits=harness.load_splits()
    items=splits['dev']+splits['validation']
    oracle=harness.build_reference(items)
    kernels={'baseline':(data['baseline_code'],False),'openmp':(data['baseline_code'],True)}
    promos=sorted([c for c in data['candidates'] if c.get('promoted')],key=lambda c:c['round'])
    kernels.update({f"round-{c['round']}":(c['code'],False) for c in promos})
    samples=[]
    rng=random.Random(42)
    with tempfile.TemporaryDirectory() as tmp:
        binaries={}
        for name,(code,omp) in kernels.items():
            work=Path(tmp)/name;work.mkdir()
            binary,error=harness.compile_kernel(code,work,omp)
            if not binary: raise RuntimeError(f'{name}: {error}')
            binaries[name]=binary
            for item in items:
                text,t=harness.run_once(binary,item)
                if text!=oracle[harness.key(item)]: raise RuntimeError(f'{name}: wrong output')
        for block in range(args.blocks):
            for item in items:
                order=list(kernels);rng.shuffle(order)
                for position,name in enumerate(order):
                    text,t=harness.run_once(binaries[name],item)
                    if text!=oracle[harness.key(item)]: raise RuntimeError(f'{name}: wrong output')
                    samples.append({'block':block,'position':position,'kernel':name,'item':harness.key(item),'tps':t})
            print(f'block {block+1}/{args.blocks}',flush=True)
    index={(s['block'],s['item'],s['kernel']):s['tps'] for s in samples}
    summary={}
    previous='baseline'
    for name in kernels:
        scores={}
        for split in ('dev','validation'):
            paired=[statistics.geometric_mean(index[b,harness.key(it),name]/index[b,harness.key(it),'baseline'] for it in splits[split]) for b in range(args.blocks)]
            scores[split]={'median_speedup':statistics.median(paired),'min':min(paired),'max':max(paired)}
        if name.startswith('round-'):
            dev=[statistics.geometric_mean(index[b,harness.key(it),name]/index[b,harness.key(it),previous] for it in splits['dev']) for b in range(args.blocks)]
            val=[statistics.geometric_mean(index[b,harness.key(it),name]/index[b,harness.key(it),previous] for it in splits['validation']) for b in range(args.blocks)]
            scores['vs_previous']={'kernel':previous,'dev_median':statistics.median(dev),'dev_min':min(dev),'dev_max':max(dev),'validation_median':statistics.median(val),'validation_min':min(val),'validation_max':max(val),'clears_margin_in_every_block':min(dev)>1.05 and min(val)>1}
            previous=name
        summary[name]=scores
    result={'run_id':args.run,'blocks':args.blocks,'order_seed':42,'platform':platform.platform(),'compiler':subprocess.check_output(['clang','--version'],text=True).splitlines()[0],'flags':harness.COMPILE_FLAGS,'steps':harness.STEPS,'model_sha256':{it.model:hashlib.sha256((harness.MODELS/it.model).read_bytes()).hexdigest() for it in items},'kernel_sha256':{name:hashlib.sha256(code.encode()).hexdigest() for name,(code,_) in kernels.items()},'correctness':'generated text matched baseline on all measured items','summary':summary,'samples':samples,'interpretation':'Ranges describe observed blocks, not confidence intervals. Later promotions require contemporaneous evidence.'}
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()

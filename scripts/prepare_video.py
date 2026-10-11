"""Export recorded measurements into the reproducible video project."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from tokenforge.reporting import load_bundle
bundle=load_bundle('r-20261011-170439')
probe=bundle['parallelism']
video={
 'heldout':bundle['heldout'],
 'rounds':[{'round':0,'speedup':1,'promotion':False}]+[{'round':r['round'],'speedup':r['champion_dev_speedup'],'promotion':bool(r['promoted_id'])} for r in bundle['rounds']],
 'parallelism':{'ratio':probe['wall_ratio_serial_over_parallel'],'conditions':[{'name':c['condition'],'wall':c['proposal_wall_seconds'],'valid':c['valid_candidates'],'intervals':[{'agent':r['agent'],'start':r['start_seconds'],'end':r['end_seconds']} for r in c['proposals']]} for c in probe['conditions']]},
 'repair':{k:bundle['repair'][k] for k in ('source_id','repair_id','original_status','repair_status','retrieval_method','lesson')},
 'kernel_sha256':bundle['kernel_sha256'],'run_id':bundle['run_id'],
 'candidate_count':len(bundle['candidates']),'correct_count':sum(c['status']=='ok' for c in bundle['candidates'])}
(ROOT/'video/src/evidence.json').write_text(json.dumps(video,indent=2)+'\n')
print('Exported validated video data')

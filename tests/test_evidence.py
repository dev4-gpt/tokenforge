import json
from pathlib import Path
from unittest.mock import patch
import pytest
from tokenforge import harness
from tokenforge.memory import Memory
from tokenforge.reporting import load_bundle

def test_comment_and_string_checks():
    assert harness.static_check('void matmul(){ /* system( and execve( are prose */ const char *s="system("; }') == ''
    assert harness.static_check('void matmul(){ system("true"); }').startswith('blocked')
    assert harness.static_check('#include "other.h"\nvoid matmul(){}').startswith('blocked')

@pytest.mark.parametrize('oracle',[{}, {'x::y':None}, {'x::y':''}])
def test_missing_oracle_fails_before_compile(oracle):
    with patch.object(harness,'reference_outputs',return_value=oracle), patch.object(harness,'compile_kernel') as compiler:
        result=harness.evaluate(harness.BASELINE_KERNEL,[harness.Item('x','y')],runs=1)
    assert result.status=='invalid_evaluation'
    compiler.assert_not_called()

@pytest.mark.parametrize('throughput',[0,-1,float('inf'),float('nan')])
def test_invalid_timing(throughput):
    item=harness.Item('x','y')
    with patch.object(harness,'reference_outputs',return_value={harness.key(item):'text'}), patch.object(harness,'compile_kernel',return_value=(Path('/unused'),'')),patch.object(harness,'run_once',return_value=('text',throughput)):
        assert harness.evaluate(harness.BASELINE_KERNEL,[item],runs=1).status=='invalid_evaluation'

def test_missing_timing_marker():
    with patch.object(harness.subprocess,'run',return_value=type('Completed',(),{'returncode':0,'stdout':'text','stderr':''})()):
        with pytest.raises(ValueError,match='missing throughput'):
            harness.run_once(Path('/unused'),harness.Item('x','y'))

def test_speedup_requires_matching_valid_measurements():
    assert harness.speedup(harness.Result('ok',[1]),harness.Result('ok',[1,2]))==0
    assert harness.speedup(harness.Result('ok',[1]),harness.Result('crash',[1]))==0

def test_offline_bundle_and_run_matching(monkeypatch):
    monkeypatch.delenv('MONGODB_URI',raising=False)
    bundle=load_bundle('r-20261011-170439')
    assert len(bundle['candidates'])==48
    assert sum(c['promoted'] for c in bundle['candidates'])==3
    assert all(r['n_ok']+r['n_failed']==6 for r in bundle['rounds'])
    assert bundle['champion_stats']['count']==4
    assert load_bundle('r-20261011-163001')['heldout'] is None

def test_bundle_refuses_mismatched_counts(tmp_path):
    root=Path(__file__).resolve().parent.parent
    (tmp_path/'results').mkdir()
    data=json.loads((root/'results/r-20261011-170439.json').read_text())
    (tmp_path/'results/r-20261011-170439.json').write_text(json.dumps(data))
    with pytest.raises(ValueError,match='counts disagree'):
        load_bundle('r-20261011-170439',tmp_path)

def test_memory_mirror_and_isolation(tmp_path):
    mem=Memory(tmp_path/'mirror.jsonl',connect=False)
    first=mem.add({'run_id':'a','status':'ok','note':'worked','dev_speedup':2})
    mem.add({'run_id':'b','status':'compile_error','note':'other run'})
    rows=mem.retrieve('worked','a')
    assert [r['_id'] for r in rows]==[first]
    assert rows[0]['retrieval_method']=='local'
    assert len(mem.all())==2

def test_vector_query_and_fallback_are_run_scoped(tmp_path):
    mem=Memory(tmp_path/'mirror.jsonl',connect=False)
    class Fake:
        def aggregate(self,pipeline):
            assert pipeline[0]['$vectorSearch']['filter']['run_id']=='a'
            raise RuntimeError('not ready')
        def find(self,q,projection):
            assert q['run_id']=='a'
            return Cursor()
    class Cursor:
        def limit(self,k): return self
        def sort(self,*args): return self
        def __iter__(self): return iter([])
    mem.col=Fake()
    with patch.object(mem,'_vector_ready',return_value=True),patch('tokenforge.memory.embed',return_value=[1.0]):
        assert mem.retrieve('query','a')==[]

def test_successful_atlas_write_is_also_mirrored(tmp_path):
    mem=Memory(tmp_path/'mirror.jsonl',connect=False)
    inserted=[]
    class Fake:
        def insert_one(self,doc): inserted.append(doc)
    mem.col=Fake()
    with patch('tokenforge.memory.embed',return_value=[1.0]):
        identity=mem.add({'run_id':'a','status':'ok','note':'test'})
    assert inserted[0]['_id']==identity
    assert json.loads(mem.path.read_text())['_id']==identity
    assert 'embedding' not in json.loads(mem.path.read_text())

def test_study_expired_deadline_does_not_spawn():
    import time
    from learning_study import invoke
    with patch('learning_study.subprocess.Popen') as spawn:
        assert invoke({'task':'propose'},time.monotonic()-1)['status']=='timeout'
    spawn.assert_not_called()

def test_study_timeout_terminates_process_group():
    import time,subprocess
    from learning_study import invoke
    class Process:
        pid=987654
        calls=0
        def communicate(self,*args,**kwargs):
            self.calls+=1
            if self.calls==1: raise subprocess.TimeoutExpired('worker',1)
            return '',''
    with patch('learning_study.subprocess.Popen',return_value=Process()),patch('learning_study.os.killpg') as kill:
        assert invoke({'task':'propose'},time.monotonic()+1)['status']=='timeout'
    kill.assert_called_once()


def test_bundle_refuses_changed_champion(tmp_path):
    import shutil
    root=Path(__file__).resolve().parent.parent
    (tmp_path/'results').mkdir()
    identity='r-20261011-170439'
    shutil.copy(root/f'results/{identity}.candidates.jsonl',tmp_path/'results')
    data=json.loads((root/f'results/{identity}.json').read_text())
    data['champion_code']='void matmul(){}'
    (tmp_path/f'results/{identity}.json').write_text(json.dumps(data))
    with pytest.raises(ValueError,match='champion code'):
        load_bundle(identity,tmp_path)

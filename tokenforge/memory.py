"""Run-isolated Atlas retrieval with durable local mirrors and provenance."""
from __future__ import annotations
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / 'results' / 'candidates.jsonl'
OLLAMA = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EMBED_MODEL = 'nomic-embed-text'
DIMS = 768
INDEX = 'note_vectors_v2'

def embed(text):
    try:
        r = requests.post(f'{OLLAMA}/api/embed', json={'model': EMBED_MODEL, 'input': text}, timeout=10)
        r.raise_for_status()
        return r.json()['embeddings'][0]
    except Exception as e:
        print(f'[memory] embedding unavailable: {type(e).__name__}', file=sys.stderr)
        return None

class Memory:
    def __init__(self, jsonl_path=None, connect=True):
        self.path = Path(jsonl_path) if jsonl_path else JSONL
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.col = self.runs = None
        self.retrieval = 'recent'
        self._checked = 0.0
        uri = os.getenv('MONGODB_URI') if connect else None
        if uri:
            try:
                from pymongo import MongoClient
                db = MongoClient(uri, serverSelectionTimeoutMS=5000)['tokenforge']
                db.command('ping')
                self.col, self.runs = db['candidates'], db['runs']
                self._ensure_indexes()
            except Exception as e:
                print(f'[memory] Atlas unavailable: {type(e).__name__}; local mirror active', file=sys.stderr)
                self.col = self.runs = None

    @property
    def backend(self):
        return f'mongodb ({self.retrieval})' if self.col is not None else 'jsonl'

    def _ensure_indexes(self):
        self.col.create_index([('note', 'text'), ('error_snippet', 'text')])
        self.retrieval = 'text'
        try:
            from pymongo.operations import SearchIndexModel
            names = {i['name'] for i in self.col.list_search_indexes()}
            if INDEX not in names:
                self.col.create_search_index(SearchIndexModel(name=INDEX, type='vectorSearch', definition={'fields': [
                    {'type': 'vector', 'path': 'embedding', 'numDimensions': DIMS, 'similarity': 'cosine'},
                    {'type': 'filter', 'path': 'status'}, {'type': 'filter', 'path': 'run_id'}]}))
            self._vector_ready()
        except Exception as e:
            print(f'[memory] text fallback: {type(e).__name__}', file=sys.stderr)

    def _vector_ready(self):
        if self.col is None:
            return False
        if time.monotonic() - self._checked < 5:
            return self.retrieval == 'vector'
        self._checked = time.monotonic()
        try:
            ready = any(i.get('name') == INDEX and i.get('queryable') for i in self.col.list_search_indexes())
            self.retrieval = 'vector' if ready else 'text'
        except Exception:
            self.retrieval = 'text'
        return self.retrieval == 'vector'

    def add(self, doc):
        doc = dict(doc)
        doc.setdefault('_id', uuid.uuid4().hex)
        doc.setdefault('ts', datetime.now(timezone.utc).isoformat(timespec='seconds'))
        with self.path.open('a') as f:
            f.write(json.dumps({k: v for k, v in doc.items() if k != 'embedding'}, default=str) + '\n')
        if self.col is not None:
            doc['embedding'] = embed(f"{doc.get('strategy','')} | {doc.get('note','')} | {doc.get('error_snippet','')}")
            try:
                self.col.insert_one(doc)
            except Exception as e:
                print(f'[memory] Atlas insert unavailable: {type(e).__name__}; mirrored locally', file=sys.stderr)
        return str(doc['_id'])

    def log_round(self, doc):
        if self.runs is not None:
            try:
                self.runs.insert_one(dict(doc))
            except Exception as e:
                print(f'[memory] round log unavailable: {type(e).__name__}', file=sys.stderr)

    def _local(self, run_id):
        rows = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()] if self.path.exists() else []
        return [r for r in rows if not run_id or r.get('run_id') == run_id]

    def retrieve(self, query, run_id, k_wins=2, k_fails=1):
        projection = {k: 1 for k in ('_id', 'run_id', 'note', 'status', 'dev_speedup', 'error_snippet', 'model', 'lesson')}
        out = []
        vector = embed(query) if self._vector_ready() else None
        for want_ok, k in ((True, k_wins), (False, k_fails)):
            if k <= 0:
                continue
            q = {'run_id': run_id, 'status': 'ok' if want_ok else {'$ne': 'ok'}}
            found, method = [], 'local'
            if self.col is not None:
                if vector:
                    try:
                        found = list(self.col.aggregate([{'$vectorSearch': {'index': INDEX, 'path': 'embedding',
                            'queryVector': vector, 'numCandidates': 100, 'limit': k, 'filter': q}}, {'$project': projection}]))
                        method = 'vector'
                    except Exception:
                        pass
                if not found:
                    try:
                        found = list(self.col.find({**q, '$text': {'$search': query}}, projection).limit(k))
                        method = 'text'
                    except Exception:
                        pass
                if not found:
                    try:
                        found = list(self.col.find(q, projection).sort('ts', -1).limit(k))
                        method = 'recent'
                    except Exception:
                        pass
            if not found:
                rows = [r for r in self._local(run_id) if (r.get('status') == 'ok') == want_ok]
                found = sorted(rows, key=lambda r: -(r.get('dev_speedup') or 0))[:k] if want_ok else rows[-k:]
                method = 'local'
            for row in found:
                if row.get('run_id') != run_id:
                    continue
                out.append({**row, '_id': str(row.get('_id', '')), 'retrieval_method': method})
        return out

    def all(self, run_id=None):
        rows = self._local(run_id)
        if self.col is not None:
            try:
                rows += list(self.col.find({'run_id': run_id} if run_id else {}, {'embedding': 0}).sort('ts', 1))
            except Exception:
                pass
        unique = {str(r.get('_id', i)): r for i, r in enumerate(rows)}
        return sorted(unique.values(), key=lambda r: r.get('ts', ''))

"""Team memory. Every attempt (wins and failures) goes to MongoDB Atlas; before proposing, each
agent retrieves the most relevant past attempts via Atlas Vector Search over on-device
(Ollama nomic-embed-text) embeddings. Falls back to $text search, then to a local JSONL file.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "results" / "candidates.jsonl"
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
DIMS = 768
INDEX = "note_vectors"


def embed(text: str) -> list[float] | None:
    try:
        r = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": text}, timeout=30)
        r.raise_for_status()
        return r.json()["embeddings"][0]
    except Exception as e:
        print(f"[memory] embed skipped: {e}", file=sys.stderr)
        return None


class Memory:
    def __init__(self) -> None:
        self.col = None
        self.runs = None
        self.retrieval = "recent"
        uri = os.getenv("MONGODB_URI")
        if uri:
            try:
                from pymongo import MongoClient
                db = MongoClient(uri, serverSelectionTimeoutMS=5000)["tokenforge"]
                db.command("ping")
                self.col, self.runs = db["candidates"], db["runs"]
                self._ensure_indexes()
            except Exception as e:
                print(f"[memory] Mongo unavailable, using {JSONL}: {e}", file=sys.stderr)
                self.col = None
        JSONL.parent.mkdir(exist_ok=True)

    @property
    def backend(self) -> str:
        return f"mongodb ({self.retrieval})" if self.col is not None else "jsonl"

    def _ensure_indexes(self) -> None:
        self.col.create_index([("note", "text"), ("error_snippet", "text")])
        self.retrieval = "text"
        try:
            from pymongo.operations import SearchIndexModel
            names = {i["name"] for i in self.col.list_search_indexes()}
            if INDEX not in names:
                self.col.create_search_index(SearchIndexModel(name=INDEX, type="vectorSearch", definition={
                    "fields": [{"type": "vector", "path": "embedding", "numDimensions": DIMS, "similarity": "cosine"},
                               {"type": "filter", "path": "status"}]}))
            self.retrieval = "vector"
        except Exception as e:
            print(f"[memory] vector index unavailable, using $text: {e}", file=sys.stderr)

    def add(self, doc: dict) -> str:
        doc = dict(doc)
        doc.setdefault("_id", uuid.uuid4().hex)
        doc["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        doc["embedding"] = embed(f"{doc.get('strategy','')} | {doc.get('note','')} | {doc.get('error_snippet','')}")
        if self.col is not None:
            try:
                self.col.insert_one(doc)
                return doc["_id"]
            except Exception as e:
                print(f"[memory] insert failed, writing jsonl: {e}", file=sys.stderr)
        with JSONL.open("a") as f:
            f.write(json.dumps({k: v for k, v in doc.items() if k != "embedding"}) + "\n")
        return doc["_id"]

    def log_round(self, doc: dict) -> None:
        if self.runs is not None:
            try:
                self.runs.insert_one(dict(doc))
            except Exception as e:
                print(f"[memory] round log failed: {e}", file=sys.stderr)

    def retrieve(self, query: str, run_id: str, k_wins: int = 2, k_fails: int = 1) -> list[dict]:
        proj = {"_id": 0, "note": 1, "status": 1, "dev_speedup": 1, "error_snippet": 1, "model": 1}
        if self.col is None:
            rows = [json.loads(l) for l in JSONL.read_text().splitlines()] if JSONL.exists() else []
            rows = [r for r in rows if r.get("run_id") == run_id and r.get("note")]
            wins = sorted([r for r in rows if r["status"] == "ok"], key=lambda r: -(r.get("dev_speedup") or 0))
            fails = [r for r in rows if r["status"] != "ok"][-k_fails:]
            return wins[:k_wins] + fails
        out: list[dict] = []
        for want_ok, k in ((True, k_wins), (False, k_fails)):
            status_f = {"status": "ok"} if want_ok else {"status": {"$ne": "ok"}}
            try:
                if self.retrieval == "vector" and (vec := embed(query)):
                    pipe = [{"$vectorSearch": {"index": INDEX, "path": "embedding", "queryVector": vec,
                                               "numCandidates": 100, "limit": k,
                                               "filter": status_f}}, {"$project": proj}]
                    out += list(self.col.aggregate(pipe))
                    continue
            except Exception as e:  # index still building, etc.
                print(f"[memory] vector search failed, falling back: {e}", file=sys.stderr)
            q = {**status_f, "run_id": run_id}
            if self.retrieval in ("text", "vector"):
                try:
                    out += list(self.col.find({**q, "$text": {"$search": query}}, proj).limit(k))
                    continue
                except Exception:
                    pass
            out += list(self.col.find(q, proj).sort("ts", -1).limit(k))
        return out

    def all(self, run_id: str | None = None) -> list[dict]:
        if self.col is not None:
            q = {"run_id": run_id} if run_id else {}
            return list(self.col.find(q, {"embedding": 0}).sort("ts", 1))
        rows = [json.loads(l) for l in JSONL.read_text().splitlines()] if JSONL.exists() else []
        return [r for r in rows if not run_id or r.get("run_id") == run_id]

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from app.business import DomainIssue

SCHEMA = """CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, report TEXT NOT NULL, created TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', revision INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '', reviewed TEXT,
    blocked INTEGER NOT NULL DEFAULT 0
);"""


class Store:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=15)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute(SCHEMA)
            columns = {row[1] for row in db.execute("PRAGMA table_info(runs)")}
            if "blocked" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN blocked INTEGER NOT NULL DEFAULT 0")
            yield db

    def register(self, run_id, report):
        blocked = 1 if report.get("closure", {}).get("blocked") else 0
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs(id,report,created,blocked) VALUES (?,?,?,?) ON CONFLICT(id) DO NOTHING",
                (
                    run_id,
                    json.dumps(report, ensure_ascii=False),
                    report["manifest"]["created"],
                    blocked,
                ),
            )
        return self.load(run_id)

    def load(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise DomainIssue("RUN_NOT_FOUND")
        result = dict(row)
        result["blocked"] = bool(result["blocked"])
        result["report"] = json.loads(result["report"])
        return result

    def list(self):
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,created,status,revision,note,blocked FROM runs ORDER BY created DESC,id LIMIT 50"
            ).fetchall()
        return [dict(r, blocked=bool(r["blocked"])) for r in rows]

    def latest_approved(self):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM runs WHERE status='APPROVED' ORDER BY created DESC,id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["blocked"] = bool(result["blocked"])
        result["report"] = json.loads(result["report"])
        return result

    def revise(self, run_id, revision, status, note, now):
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE runs SET status=?,note=?,reviewed=?,revision=revision+1 WHERE id=? AND revision=?",
                (status, note, now, run_id, revision),
            )
            if cursor.rowcount != 1:
                raise DomainIssue("STALE_REVIEW")
        return self.load(run_id)

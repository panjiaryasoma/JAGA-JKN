"""Transactional SQLite store. Case changes, events, and receipts commit together."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

from packages.data.snapshot import Snapshot
from packages.domain.cases import (
    PRIVILEGED,
    TERMINAL,
    TRANSITIONS,
    Actor,
    CaseDetail,
    CaseEvent,
    CaseSummary,
    Intervention,
    MutationResult,
    WorkflowError,
)
from packages.domain.read_models import MonthlyEvidence

SCHEMA = """
CREATE TABLE cases (
    case_id TEXT PRIMARY KEY,
    id_badan_usaha TEXT NOT NULL,
    periode_bulan TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('OPEN','IN_REVIEW','WAITING_EVIDENCE','RESOLVED','DISMISSED')),
    version INTEGER NOT NULL CHECK(version >= 1),
    reason TEXT NOT NULL,
    status_reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    recurrence_of TEXT REFERENCES cases(case_id),
    dataset_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);
CREATE UNIQUE INDEX one_active_case ON cases(id_badan_usaha, periode_bulan)
    WHERE status IN ('OPEN','IN_REVIEW','WAITING_EVIDENCE');
CREATE TABLE case_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    version INTEGER NOT NULL CHECK(version >= 1),
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL CHECK(actor_role IN ('REVIEWER','SUPERVISOR')),
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(case_id, version)
);
CREATE TABLE interventions (
    intervention_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    kind TEXT NOT NULL CHECK(kind IN ('REQUEST_DOCUMENTS','CONTACT_REVIEW','FOLLOW_UP')),
    status TEXT NOT NULL CHECK(status IN ('PLANNED','COMPLETED','CANCELLED')),
    note TEXT NOT NULL,
    due_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    completed_at TEXT,
    outcome_note TEXT
);
CREATE INDEX interventions_by_case ON interventions(case_id, created_at, intervention_id);
CREATE TABLE mutation_receipts (
    actor_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    response_json TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    PRIMARY KEY(actor_id, idempotency_key)
);
PRAGMA user_version=1;
"""


@dataclass(frozen=True)
class MutationReceipt:
    result: MutationResult
    status_code: int
    replayed: bool = False


@dataclass(frozen=True)
class CaseStore:
    path: Path

    def initialize(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection(allow_create=True) as connection:
                self._enable_wal(connection)
                # Serialize the version decision too: two workers may start together.
                connection.execute("BEGIN IMMEDIATE")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    # executescript would commit the lock before running the DDL.
                    for statement in SCHEMA.split(";"):
                        if statement.strip():
                            connection.execute(statement)
                elif version != 1:
                    raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE")
                self._check_schema(connection)
                if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE")
        except OSError as exc:
            raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE") from exc

    @staticmethod
    def _enable_wal(connection):
        # Journal mode changes can return SQLITE_BUSY without honoring busy_timeout.
        # Retry only lock contention, before any schema/write transaction has begun.
        deadline = monotonic() + 5
        while True:
            try:
                mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if mode != "wal":
                    raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE")
                return
            except sqlite3.OperationalError as exc:
                if (getattr(exc, "sqlite_errorcode", 0) & 0xFF) not in {
                    sqlite3.SQLITE_BUSY,
                    sqlite3.SQLITE_LOCKED,
                } or monotonic() >= deadline:
                    raise
                sleep(0.05)

    @staticmethod
    def _check_schema(connection):
        if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE")
        for table in ("cases", "case_events", "interventions", "mutation_receipts"):
            connection.execute(f"SELECT 1 FROM {table} LIMIT 0")

    def check_ready(self):
        with self._connection(write=False) as connection:
            self._check_schema(connection)

    @contextmanager
    def _connection(self, *, write: bool | None = None, allow_create: bool = False):
        connection = None
        try:
            mode = "rwc" if allow_create else "rw"
            connection = sqlite3.connect(
                self.path.resolve().as_uri() + f"?mode={mode}",
                uri=True,
                timeout=5,
                isolation_level=None,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            if write is not None:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            if connection.in_transaction:
                connection.commit()
        except sqlite3.Error as exc:
            raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE") from exc
        finally:
            if connection is not None:
                try:
                    if connection.in_transaction:
                        connection.rollback()
                finally:
                    connection.close()

    @staticmethod
    def _case(connection, case_id):
        row = connection.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            raise WorkflowError(404, "NOT_FOUND")
        return row

    @staticmethod
    def _summary(row):
        values = {key: row[key] for key in CaseSummary.model_fields if key != "dataset"}
        values["dataset"] = json.loads(row["dataset_json"])
        return values

    @staticmethod
    def _active_exists(connection, company_id, period, *, exclude=""):
        return (
            connection.execute(
                "SELECT 1 FROM cases WHERE id_badan_usaha=? AND periode_bulan=? "
                "AND status IN ('OPEN','IN_REVIEW','WAITING_EVIDENCE') AND case_id!=?",
                (company_id, period, exclude),
            ).fetchone()
            is not None
        )

    def get_case(self, case_id: str) -> CaseDetail:
        with self._connection(write=False) as connection:
            row = self._case(connection, case_id)
            interventions = tuple(
                Intervention.model_validate(dict(item))
                for item in connection.execute(
                    "SELECT * FROM interventions WHERE case_id=? ORDER BY created_at,intervention_id",
                    (case_id,),
                )
            )
            return CaseDetail.model_validate(
                {
                    **self._summary(row),
                    "evidence_snapshot": MonthlyEvidence.model_validate_json(row["evidence_json"]),
                    "interventions": interventions,
                }
            )

    def list_cases(self, *, page, page_size, status=None, company_id=None, period=None):
        terms, parameters = [], []
        for column, value in (
            ("status", status),
            ("id_badan_usaha", company_id),
            ("periode_bulan", period),
        ):
            if value is not None:
                terms.append(f"{column}=?")
                parameters.append(value)
        where = " WHERE " + " AND ".join(terms) if terms else ""
        with self._connection(write=False) as connection:
            total = connection.execute("SELECT count(*) FROM cases" + where, parameters).fetchone()[
                0
            ]
            rows = connection.execute(
                "SELECT * FROM cases" + where + " ORDER BY created_at,case_id LIMIT ? OFFSET ?",
                [*parameters, page_size, (page - 1) * page_size],
            )
            return tuple(CaseSummary.model_validate(self._summary(row)) for row in rows), total

    def list_events(self, case_id, *, page, page_size):
        with self._connection(write=False) as connection:
            self._case(connection, case_id)
            total = connection.execute(
                "SELECT count(*) FROM case_events WHERE case_id=?",
                (case_id,),
            ).fetchone()[0]
            events = []
            for row in connection.execute(
                "SELECT * FROM case_events WHERE case_id=? ORDER BY version LIMIT ? OFFSET ?",
                (case_id, page_size, (page - 1) * page_size),
            ):
                values = dict(row)
                values["payload"] = json.loads(values.pop("payload_json"))
                events.append(CaseEvent.model_validate(values))
            return tuple(events), total

    def mutate(
        self,
        *,
        actor: Actor,
        key: str,
        fingerprint: str,
        operation: str,
        payload: dict,
        case_id: str | None = None,
        expected_version: int | None = None,
        intervention_id: str | None = None,
        snapshot: Snapshot | None = None,
        dataset_error: str = "DATASET_UNAVAILABLE",
    ) -> MutationReceipt:
        if (
            operation == "TRANSITION"
            and payload["action"] in PRIVILEGED
            and actor.role != "SUPERVISOR"
        ):
            raise WorkflowError(403, "FORBIDDEN")
        with self._connection(write=True) as connection:
            receipt = connection.execute(
                "SELECT * FROM mutation_receipts WHERE actor_id=? AND idempotency_key=?",
                (actor.actor_id, key),
            ).fetchone()
            if receipt is not None:
                if receipt["fingerprint"] != fingerprint:
                    raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
                return MutationReceipt(
                    MutationResult.model_validate(json.loads(receipt["response_json"])),
                    receipt["status_code"],
                    True,
                )
            now = datetime.now(UTC).isoformat(timespec="microseconds")
            event_id = str(uuid4())
            event_payload = dict(payload)
            status_code = 200
            if operation == "CREATE":
                if snapshot is None:
                    raise WorkflowError(503, dataset_error)
                company_id, period = payload["id_badan_usaha"], payload["periode_bulan"]
                evidence = snapshot.evidence_index.get((company_id, period))
                if evidence is None:
                    raise WorkflowError(404, "NOT_FOUND")
                if self._active_exists(connection, company_id, period):
                    raise WorkflowError(409, "CASE_ALREADY_OPEN")
                parent_id = payload["recurrence_of"]
                if parent_id is not None:
                    parent = self._case(connection, parent_id)
                    if (
                        parent["status"] != "RESOLVED"
                        or parent["id_badan_usaha"] != company_id
                        or parent["periode_bulan"] >= period
                    ):
                        raise WorkflowError(409, "INVALID_RECURRENCE")
                case_id, version, state = str(uuid4()), 1, "OPEN"
                connection.execute(
                    "INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        case_id,
                        company_id,
                        period,
                        state,
                        version,
                        payload["reason"],
                        payload["reason"],
                        now,
                        now,
                        actor.actor_id,
                        parent_id,
                        snapshot.ref.model_dump_json(),
                        evidence.model_dump_json(),
                    ),
                )
                action, status_code = "CASE_OPENED", 201
            else:
                row = self._case(connection, case_id)
                if row["version"] != expected_version:
                    raise WorkflowError(412, "VERSION_CONFLICT")
                version, state = row["version"] + 1, row["status"]
                status_reason = row["status_reason"]
                if operation == "TRANSITION":
                    action = payload["action"]
                    target = TRANSITIONS.get((state, action))
                    if target is None:
                        raise WorkflowError(409, "INVALID_TRANSITION")
                    if (
                        target in TERMINAL
                        and connection.execute(
                            "SELECT 1 FROM interventions WHERE case_id=? AND status='PLANNED'",
                            (case_id,),
                        ).fetchone()
                    ):
                        raise WorkflowError(409, "OPEN_INTERVENTIONS")
                    if action == "REOPEN" and self._active_exists(
                        connection,
                        row["id_badan_usaha"],
                        row["periode_bulan"],
                        exclude=case_id,
                    ):
                        raise WorkflowError(409, "CASE_ALREADY_OPEN")
                    state, status_reason = target, payload["reason"]
                elif operation == "NOTE":
                    action = "NOTE_ADDED"
                elif operation == "INTERVENTION":
                    if state not in {"IN_REVIEW", "WAITING_EVIDENCE"}:
                        raise WorkflowError(409, "INVALID_TRANSITION")
                    intervention_id = str(uuid4())
                    connection.execute(
                        "INSERT INTO interventions VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            intervention_id,
                            case_id,
                            payload["kind"],
                            "PLANNED",
                            payload["note"],
                            payload["due_at"],
                            now,
                            actor.actor_id,
                            None,
                            None,
                        ),
                    )
                    event_payload["intervention_id"] = intervention_id
                    action, status_code = "INTERVENTION_PLANNED", 201
                elif operation == "OUTCOME":
                    intervention = connection.execute(
                        "SELECT * FROM interventions WHERE intervention_id=? AND case_id=?",
                        (intervention_id, case_id),
                    ).fetchone()
                    if intervention is None:
                        raise WorkflowError(404, "NOT_FOUND")
                    if state in TERMINAL or intervention["status"] != "PLANNED":
                        raise WorkflowError(409, "INVALID_TRANSITION")
                    connection.execute(
                        "UPDATE interventions SET status=?,completed_at=?,outcome_note=? "
                        "WHERE intervention_id=? AND case_id=?",
                        (payload["outcome"], now, payload["note"], intervention_id, case_id),
                    )
                    event_payload["intervention_id"] = intervention_id
                    action = "INTERVENTION_" + payload["outcome"]
                else:
                    raise ValueError("Unknown internal mutation operation")
                connection.execute(
                    "UPDATE cases SET status=?,status_reason=?,version=?,updated_at=? WHERE case_id=?",
                    (state, status_reason, version, now, case_id),
                )
            connection.execute(
                "INSERT INTO case_events VALUES (?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    case_id,
                    version,
                    actor.actor_id,
                    actor.role,
                    action,
                    json.dumps(event_payload, separators=(",", ":")),
                    now,
                ),
            )
            result = MutationResult(
                case_id=case_id,
                status=state,
                version=version,
                event_id=event_id,
                intervention_id=intervention_id,
            )
            connection.execute(
                "INSERT INTO mutation_receipts VALUES (?,?,?,?,?)",
                (actor.actor_id, key, fingerprint, result.model_dump_json(), status_code),
            )
            return MutationReceipt(result, status_code)

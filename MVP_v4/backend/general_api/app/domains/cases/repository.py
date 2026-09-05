"""V4-only Shared Case persistence. Authorization stays above this repository."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from backend.config import Settings
from backend.contracts.case import (
    ActorContext, ActorRole, BankCaseWorkspace, CaseContextFeature, CaseDelta, CaseEntityUpsert, CaseEvent,
    CaseFact, CaseListItem, CaseParticipant, CaseProjection, CaseStatus, CaseVerification, CreateCaseRequest,
    CreateEventRequest, CreateMlIntakeRequest, EntityType, EventType, SharedCase, Visibility,
)
from backend.database import database_engine
from backend.contracts.tasks import CaseTask, TaskSuggestion


class CaseNotFound(Exception):
    pass


class CaseAccessDenied(Exception):
    pass


class VersionConflict(Exception):
    pass


class IdempotencyConflict(Exception):
    pass


def _canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value or {})


@dataclass
class CaseRepository:
    settings: Settings

    def __post_init__(self) -> None:
        self.engine: Engine = database_engine(self.settings)

    def close(self) -> None:
        self.engine.dispose()

    def create_case(self, actor: ActorContext, request: CreateCaseRequest) -> CaseProjection:
        if actor.role == ActorRole.CUSTOMER:
            if request.customer_participant_id not in {None, actor.actor_id}:
                raise CaseAccessDenied()
            customer_id = actor.actor_id
        elif actor.role == ActorRole.BANK_STAFF:
            if not request.customer_participant_id:
                raise CaseAccessDenied()
            customer_id = request.customer_participant_id
        else:
            raise CaseAccessDenied()

        # A create retry has no case id yet. Deriving its V4 case id from the UUID request key
        # lets the existing case-scoped unique idempotency constraint work on MySQL and SQLite.
        case_id = request.client_request_id
        operation = "CREATE_CASE"
        fingerprint = _canonical_hash({
            "actor_id": actor.actor_id, "actor_role": actor.role.value, "customer_id": customer_id,
            "mode": request.mode.value, "loss_status": request.loss_status.value,
            "title": request.title, "summary": request.summary,
        })
        with self.engine.begin() as connection:
            existing = self._idempotency(connection, case_id, request.client_request_id, operation)
            if existing:
                self._assert_same_fingerprint(existing, fingerprint)
                return self._projection(connection, case_id, actor)
            case_row = self._case(connection, case_id)
            if case_row:
                raise IdempotencyConflict()
            case_fingerprint = self._case_fingerprint(case_id, request.mode.value, request.loss_status.value, 1, 1)
            connection.execute(text("""
                INSERT INTO cases (id, case_number, status, mode, loss_status, revision, fingerprint, version, created_by, updated_by, title, summary)
                VALUES (:id, :case_number, :status, :mode, :loss_status, 1, :fingerprint, 1, :actor_id, :actor_id, :title, :summary)
            """), {
                "id": str(case_id), "case_number": f"CSR-{case_id.hex[:12].upper()}", "status": CaseStatus.TRIAGE.value,
                "mode": request.mode.value, "loss_status": request.loss_status.value, "fingerprint": case_fingerprint,
                "actor_id": actor.actor_id,
                "title": request.title, "summary": request.summary,
            })
            self._insert_participant(connection, case_id, customer_id, ActorRole.CUSTOMER, actor.actor_id)
            if actor.role == ActorRole.BANK_STAFF:
                self._insert_participant(connection, case_id, actor.actor_id, ActorRole.BANK_STAFF, actor.actor_id)
            event_id = uuid4()
            self._insert_event(
                connection, event_id, case_id, EventType.CASE_CREATED, EntityType.CASE, actor,
                Visibility.CUSTOMER, 1, {"mode": request.mode.value, "loss_status": request.loss_status.value},
            )
            self._insert_idempotency(connection, case_id, request.client_request_id, operation, fingerprint, EntityType.CASE, case_id)
            return self._projection(connection, case_id, actor)

    def append_event(self, case_id: UUID, actor: ActorContext, request: CreateEventRequest) -> CaseProjection:
        if actor.role != ActorRole.BANK_STAFF or request.visibility == Visibility.AI_PRIVATE:
            raise CaseAccessDenied()
        operation = "CREATE_EVENT"
        request_fingerprint = _canonical_hash({
            "event_type": request.event_type.value, "entity_type": request.entity_type.value,
            "entity_id": str(request.entity_id) if request.entity_id else None,
            "visibility": request.visibility.value, "payload": request.payload,
        })
        with self.engine.begin() as connection:
            self._require_participant(connection, case_id, actor)
            existing = self._idempotency(connection, case_id, request.client_request_id, operation)
            if existing:
                self._assert_same_fingerprint(existing, request_fingerprint)
                return self._projection(connection, case_id, actor)
            case = self._case(connection, case_id)
            if not case:
                raise CaseNotFound()
            if request.expected_version is not None and case["version"] != request.expected_version:
                raise VersionConflict()
            revision = int(case["revision"]) + 1
            version = int(case["version"]) + 1
            case_fingerprint = self._case_fingerprint(case_id, case["mode"], case["loss_status"], revision, version)
            event_id = uuid4()
            self._insert_event(connection, event_id, case_id, request.event_type, request.entity_type, actor,
                               request.visibility, revision, request.payload, request.entity_id)
            connection.execute(text("""
                UPDATE cases SET revision = :revision, version = :version, fingerprint = :fingerprint,
                    updated_at = :updated_at, updated_by = :actor_id WHERE id = :case_id
            """), {"revision": revision, "version": version, "fingerprint": case_fingerprint,
                   "updated_at": datetime.now(UTC), "actor_id": actor.actor_id, "case_id": str(case_id)})
            self._insert_idempotency(connection, case_id, request.client_request_id, operation,
                                     request_fingerprint, request.entity_type, event_id)
            return self._projection(connection, case_id, actor)

    def projection(self, case_id: UUID, actor: ActorContext) -> CaseProjection:
        with self.engine.connect() as connection:
            self._require_participant(connection, case_id, actor)
            return self._projection(connection, case_id, actor)

    def list_bank_cases(self, actor: ActorContext, deleted: bool = False) -> list[CaseListItem]:
        if actor.role != ActorRole.BANK_STAFF:
            raise CaseAccessDenied()
        with self.engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT cases.id, cases.case_number, cases.status, cases.mode, cases.loss_status, cases.revision,
                    cases.version, cases.updated_at, cases.created_at, cases.title, cases.summary, cases.deleted_at
                FROM cases JOIN case_participants ON case_participants.case_id = cases.id
                WHERE case_participants.participant_id = :actor_id
                    AND case_participants.role = :role AND case_participants.deleted_at IS NULL
                    AND ((:deleted = 0 AND cases.deleted_at IS NULL) OR (:deleted = 1 AND cases.deleted_at IS NOT NULL))
                ORDER BY cases.updated_at DESC, cases.id DESC
            """), {"actor_id": actor.actor_id, "role": ActorRole.BANK_STAFF.value, "deleted": int(deleted)}).mappings().all()
            return [self._case_list_item(connection, dict(row)) for row in rows]

    def bank_workspace(self, case_id: UUID, actor: ActorContext) -> BankCaseWorkspace:
        if actor.role != ActorRole.BANK_STAFF:
            raise CaseAccessDenied()
        with self.engine.connect() as connection:
            self._require_participant(connection, case_id, actor)
            projection = self._projection(connection, case_id, actor)
            context_rows = connection.execute(text("""
                SELECT id, case_id, source_event_id, schema_version, feature_fingerprint, payload, received_at, version
                FROM context_features WHERE case_id = :case_id AND deleted_at IS NULL
                ORDER BY received_at DESC, id DESC
            """), {"case_id": str(case_id)}).mappings()
            feature_items = [CaseContextFeature.model_validate({**dict(row), "payload": _decode_json(row["payload"])})
                             for row in context_rows]
            facts = [CaseFact.model_validate({**dict(row), "value": _decode_json(row["value"])})
                     for row in connection.execute(text("""
                        SELECT id, field_key, value, status, visibility, version FROM facts
                        WHERE case_id = :case_id AND visibility IN (:customer_visibility, :internal_visibility)
                            AND deleted_at IS NULL ORDER BY created_at, id
                     """), {"case_id": str(case_id), "customer_visibility": Visibility.CUSTOMER.value,
                               "internal_visibility": Visibility.BANK_INTERNAL.value}).mappings()]
            verifications = [CaseVerification.model_validate(dict(row))
                             for row in connection.execute(text("""
                                SELECT id, claim, status, result_summary, customer_visible, visibility, version
                                FROM verifications WHERE case_id = :case_id
                                    AND visibility IN (:customer_visibility, :internal_visibility) AND deleted_at IS NULL
                                ORDER BY created_at, id
                             """), {"case_id": str(case_id), "customer_visibility": Visibility.CUSTOMER.value,
                                       "internal_visibility": Visibility.BANK_INTERNAL.value}).mappings()]
            return BankCaseWorkspace(case=projection.case, participants=projection.participants, events=projection.events,
                                     context_features=feature_items, facts=facts, verifications=verifications,
                                     tasks=self._tasks(connection, case_id), suggestions=self._suggestions(connection, case_id))

    def record_ml_intake(self, case_id: UUID, actor: ActorContext, request: CreateMlIntakeRequest,
                         prediction: dict[str, Any], provenance: dict[str, Any]) -> CaseProjection:
        if actor.role != ActorRole.BANK_STAFF:
            raise CaseAccessDenied()
        operation = "ML_INTAKE"
        feature_fingerprint = _canonical_hash({"features": request.features, "prediction": prediction, "provenance": provenance})
        with self.engine.begin() as connection:
            self._require_participant(connection, case_id, actor)
            duplicate = connection.execute(text("""
                SELECT id, payload FROM context_features WHERE case_id = :case_id AND source_event_id = :source_event_id
            """), {"case_id": str(case_id), "source_event_id": request.source_event_id}).mappings().first()
            if duplicate:
                stored = _decode_json(duplicate["payload"])
                if stored.get("feature_fingerprint") != feature_fingerprint:
                    raise IdempotencyConflict()
                return self._projection(connection, case_id, actor)
            case = self._case(connection, case_id)
            if not case:
                raise CaseNotFound()
            if request.expected_version is not None and case["version"] != request.expected_version:
                raise VersionConflict()
            revision, version = int(case["revision"]) + 1, int(case["version"]) + 1
            feature_id = uuid4()
            payload = {"schema_version": "ml-intake.v1", "values": request.features, "feature_fingerprint": feature_fingerprint,
                       "model_result": prediction, "provenance": provenance}
            connection.execute(text("""
                INSERT INTO context_features (id, case_id, source_event_id, schema_version, feature_fingerprint, payload, created_by, updated_by)
                VALUES (:id, :case_id, :source_event_id, :schema_version, :feature_fingerprint, :payload, :actor_id, :actor_id)
            """), {"id": str(feature_id), "case_id": str(case_id), "source_event_id": request.source_event_id,
                   "schema_version": "ml-intake.v1", "feature_fingerprint": feature_fingerprint,
                   "payload": json.dumps(payload, ensure_ascii=False), "actor_id": actor.actor_id})
            self._insert_event(connection, uuid4(), case_id, EventType.ENTITY_CREATED, EntityType.CONTEXT_FEATURE, actor,
                               Visibility.BANK_INTERNAL, revision,
                               {"source_event_id": request.source_event_id, "risk_score": prediction["final_risk_score"],
                                "classification": prediction["label"], "model_version": provenance["model_version"]}, feature_id)
            fingerprint = self._case_fingerprint(case_id, case["mode"], case["loss_status"], revision, version)
            connection.execute(text("""UPDATE cases SET revision=:revision, version=:version, fingerprint=:fingerprint,
                updated_at=:updated_at, updated_by=:actor_id WHERE id=:case_id"""),
                {"revision": revision, "version": version, "fingerprint": fingerprint, "updated_at": datetime.now(UTC),
                 "actor_id": actor.actor_id, "case_id": str(case_id)})
            self._insert_idempotency(connection, case_id, request.client_request_id, operation, feature_fingerprint,
                                     EntityType.CONTEXT_FEATURE, feature_id)
            return self._projection(connection, case_id, actor)

    def delta(self, case_id: UUID, actor: ActorContext, known_revision: int, known_fingerprint: str | None) -> CaseDelta:
        with self.engine.connect() as connection:
            self._require_participant(connection, case_id, actor)
            projection = self._projection(connection, case_id, actor)
            case = projection.case
            if known_fingerprint == case.fingerprint:
                return CaseDelta(case_id=case_id, revision=case.revision, fingerprint=case.fingerprint, unchanged=True)
            upserts = [CaseEntityUpsert(entity_type=EntityType.CASE, entity_id=case.id, version=case.version,
                                        data=case.model_dump(mode="json"))]
            upserts.extend(CaseEntityUpsert(entity_type=EntityType.PARTICIPANT, entity_id=item.id, version=item.version,
                                            data=item.model_dump(mode="json")) for item in projection.participants)
            upserts.extend(CaseEntityUpsert(entity_type=EntityType.CASE if item.entity_type == EntityType.CASE else item.entity_type,
                                            entity_id=item.id, version=item.case_revision,
                                            data=item.model_dump(mode="json"))
                           for item in projection.events if item.case_revision > known_revision)
            if actor.role == ActorRole.BANK_STAFF:
                upserts.extend(CaseEntityUpsert(entity_type=EntityType.TASK, entity_id=item.id, version=item.version,
                    data=item.model_dump(mode='json')) for item in self._tasks(connection, case_id))
                upserts.extend(CaseEntityUpsert(entity_type=EntityType.AI_SUGGESTION, entity_id=item.id, version=item.version,
                    data=item.model_dump(mode='json')) for item in self._suggestions(connection, case_id))
            deleted_rows = connection.execute(text("""
                SELECT id FROM case_events WHERE case_id = :case_id AND deleted_at IS NOT NULL AND case_revision > :revision
            """), {"case_id": str(case_id), "revision": known_revision}).scalars()
            return CaseDelta(case_id=case_id, revision=case.revision, fingerprint=case.fingerprint, unchanged=False,
                             upserts=upserts, deleted_entity_ids=[UUID(value) for value in deleted_rows])

    @staticmethod
    def _tasks(connection: Connection, case_id: UUID) -> list[CaseTask]:
        return [CaseTask.model_validate(dict(row)) for row in connection.execute(text('''
            SELECT id,case_id,title,status,result,cancel_reason,version,updated_at FROM tasks
            WHERE case_id=:cid AND deleted_at IS NULL ORDER BY created_at,id
        '''), {'cid': str(case_id)}).mappings()]

    @staticmethod
    def _suggestions(connection: Connection, case_id: UUID) -> list[TaskSuggestion]:
        return [TaskSuggestion.model_validate({**dict(row), 'proposal': _decode_json(row['proposal'])})
            for row in connection.execute(text('''
                SELECT id,case_id,proposal,source_revision,status,version,updated_at FROM ai_suggestions
                WHERE case_id=:cid AND suggestion_type='TASK' AND deleted_at IS NULL
                    AND visibility IN ('CUSTOMER','BANK_INTERNAL') ORDER BY created_at,id
            '''), {'cid': str(case_id)}).mappings()]

    def _case_list_item(self, connection: Connection, row: dict[str, Any]) -> CaseListItem:
        latest_feature = connection.execute(text("""
            SELECT payload FROM context_features WHERE case_id = :case_id AND deleted_at IS NULL
            ORDER BY received_at DESC, id DESC LIMIT 1
        """), {"case_id": row["id"]}).scalar()
        result = _decode_json(latest_feature).get("model_result", {}) if latest_feature is not None else {}
        latest_event = connection.execute(text("""
            SELECT event_type FROM case_events WHERE case_id = :case_id
                AND visibility IN (:customer_visibility, :internal_visibility) AND deleted_at IS NULL
            ORDER BY case_revision DESC, created_at DESC, id DESC LIMIT 1
        """), {"case_id": row["id"], "customer_visibility": Visibility.CUSTOMER.value,
               "internal_visibility": Visibility.BANK_INTERNAL.value}).scalar()
        return CaseListItem.model_validate({**row, "latest_event_type": latest_event,
            "risk_score": result.get("final_risk_score"), "risk_classification": result.get("label")})

    @staticmethod
    def _case_fingerprint(case_id: UUID, mode: str, loss_status: str, revision: int, version: int) -> str:
        return _canonical_hash({"case_id": str(case_id), "mode": mode, "loss_status": loss_status,
                                "revision": revision, "version": version})

    @staticmethod
    def _case(connection: Connection, case_id: UUID) -> dict[str, Any] | None:
        row = connection.execute(text("""
            SELECT id, status, mode, loss_status, primary_assignee_id, revision, fingerprint, version, created_at, updated_at
            FROM cases WHERE id = :case_id
        """), {"case_id": str(case_id)}).mappings().first()
        return dict(row) if row else None

    def _require_participant(self, connection: Connection, case_id: UUID, actor: ActorContext, *, include_deleted: bool = False) -> None:
        if actor.role not in {ActorRole.CUSTOMER, ActorRole.BANK_STAFF}:
            raise CaseAccessDenied()
        participant = connection.execute(text("""
            SELECT id FROM case_participants
            WHERE case_id = :case_id AND participant_id = :actor_id AND role = :role AND deleted_at IS NULL
        """), {"case_id": str(case_id), "actor_id": actor.actor_id, "role": actor.role.value}).first()
        if not participant:
            raise CaseNotFound()
        if not include_deleted and connection.execute(text("SELECT deleted_at FROM cases WHERE id=:id"), {"id": str(case_id)}).scalar() is not None:
            raise CaseNotFound()

    @staticmethod
    def _idempotency(connection: Connection, case_id: UUID, request_id: UUID, operation: str) -> dict[str, Any] | None:
        row = connection.execute(text("""
            SELECT request_fingerprint, response_entity_type, response_entity_id FROM idempotency_keys
            WHERE case_id = :case_id AND client_request_id = :request_id AND operation = :operation
        """), {"case_id": str(case_id), "request_id": str(request_id), "operation": operation}).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _assert_same_fingerprint(existing: dict[str, Any], fingerprint: str) -> None:
        if existing["request_fingerprint"] != fingerprint:
            raise IdempotencyConflict()

    @staticmethod
    def _insert_participant(connection: Connection, case_id: UUID, participant_id: str, role: ActorRole, actor_id: str) -> None:
        connection.execute(text("""
            INSERT INTO case_participants (id, case_id, participant_id, role, created_by, updated_by)
            VALUES (:id, :case_id, :participant_id, :role, :actor_id, :actor_id)
        """), {"id": str(uuid4()), "case_id": str(case_id), "participant_id": participant_id,
               "role": role.value, "actor_id": actor_id})

    @staticmethod
    def _insert_event(connection: Connection, event_id: UUID, case_id: UUID, event_type: EventType,
                      entity_type: EntityType, actor: ActorContext, visibility: Visibility, revision: int,
                      payload: dict[str, Any], entity_id: UUID | None = None) -> None:
        connection.execute(text("""
            INSERT INTO case_events (id, case_id, visibility, event_type, entity_type, entity_id, actor_role, actor_id,
                case_revision, payload, created_by, updated_by)
            VALUES (:id, :case_id, :visibility, :event_type, :entity_type, :entity_id, :actor_role, :actor_id,
                :case_revision, :payload, :actor_id, :actor_id)
        """), {"id": str(event_id), "case_id": str(case_id), "visibility": visibility.value,
               "event_type": event_type.value, "entity_type": entity_type.value,
               "entity_id": str(entity_id) if entity_id else None, "actor_role": actor.role.value,
               "actor_id": actor.actor_id, "case_revision": revision, "payload": json.dumps(payload, ensure_ascii=False),})

    @staticmethod
    def _insert_idempotency(connection: Connection, case_id: UUID, request_id: UUID, operation: str,
                            request_fingerprint: str, entity_type: EntityType, entity_id: UUID) -> None:
        connection.execute(text("""
            INSERT INTO idempotency_keys (id, case_id, client_request_id, operation, request_fingerprint,
                response_entity_type, response_entity_id)
            VALUES (:id, :case_id, :request_id, :operation, :fingerprint, :entity_type, :entity_id)
        """), {"id": str(uuid4()), "case_id": str(case_id), "request_id": str(request_id), "operation": operation,
               "fingerprint": request_fingerprint, "entity_type": entity_type.value, "entity_id": str(entity_id)})

    def _projection(self, connection: Connection, case_id: UUID, actor: ActorContext) -> CaseProjection:
        case = self._case(connection, case_id)
        if not case:
            raise CaseNotFound()
        case_model = SharedCase.model_validate(case)
        if actor.role == ActorRole.CUSTOMER:
            case_model = case_model.model_copy(update={"primary_assignee_id": None})
            participant_rows = connection.execute(text("""
                SELECT id, case_id, participant_id, role, version FROM case_participants
                WHERE case_id = :case_id AND participant_id = :actor_id AND role = 'CUSTOMER' AND deleted_at IS NULL
            """), {"case_id": str(case_id), "actor_id": actor.actor_id}).mappings()
            allowed_visibility = (Visibility.CUSTOMER.value,)
        else:
            participant_rows = connection.execute(text("""
                SELECT id, case_id, participant_id, role, version FROM case_participants
                WHERE case_id = :case_id AND deleted_at IS NULL ORDER BY created_at, id
            """), {"case_id": str(case_id)}).mappings()
            allowed_visibility = (Visibility.CUSTOMER.value, Visibility.BANK_INTERNAL.value)
        participants = [CaseParticipant.model_validate(dict(row)) for row in participant_rows]
        if actor.role == ActorRole.CUSTOMER:
            event_query = text("""
                SELECT id, case_id, event_type, entity_type, entity_id, actor_role, actor_id, visibility,
                    case_revision, payload, created_at
                FROM case_events WHERE case_id = :case_id AND visibility = :customer_visibility AND deleted_at IS NULL
                ORDER BY case_revision, created_at, id
            """)
            event_params = {"case_id": str(case_id), "customer_visibility": Visibility.CUSTOMER.value}
        else:
            event_query = text("""
                SELECT id, case_id, event_type, entity_type, entity_id, actor_role, actor_id, visibility,
                    case_revision, payload, created_at
                FROM case_events
                WHERE case_id = :case_id AND visibility IN (:customer_visibility, :internal_visibility) AND deleted_at IS NULL
                ORDER BY case_revision, created_at, id
            """)
            event_params = {"case_id": str(case_id), "customer_visibility": Visibility.CUSTOMER.value,
                            "internal_visibility": Visibility.BANK_INTERNAL.value}
        event_rows = connection.execute(event_query, event_params).mappings()
        events = [CaseEvent.model_validate({**dict(row), "payload": _decode_json(row["payload"])}) for row in event_rows]
        return CaseProjection(case=case_model, participants=participants, events=events)

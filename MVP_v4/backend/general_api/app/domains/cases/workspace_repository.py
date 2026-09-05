"""Workspace mutations preserve the shared Case source and server actor boundary."""
from datetime import UTC, datetime
import hashlib
import hmac
from uuid import UUID, uuid4

from sqlalchemy import text

from backend.contracts.case import ActorContext, ActorRole, CaseTrashRequest, EntityType, EventType, Visibility
from backend.general_api.app.domains.cases.repository import (
    CaseRepository, CaseAccessDenied, VersionConflict, _canonical_hash,
)


class AdminCredentialUnavailable(Exception):
    pass


class AdminCredentialRejected(Exception):
    pass


class WorkspaceRepository(CaseRepository):
    def set_trash(self, case_id: UUID, actor: ActorContext, request: CaseTrashRequest) -> dict:
        if actor.role != ActorRole.BANK_STAFF:
            raise CaseAccessDenied()
        configured = self.settings.admin_case_password
        if not configured:
            raise AdminCredentialUnavailable()
        supplied = request.admin_password.get_secret_value()
        if not hmac.compare_digest(hashlib.sha256(configured.encode()).digest(), hashlib.sha256(supplied.encode()).digest()):
            raise AdminCredentialRejected()
        operation = "TRASH_CASE"
        fingerprint = _canonical_hash({"actor_id": actor.actor_id, "deleted": request.deleted})
        with self.engine.begin() as connection:
            self._require_participant(connection, case_id, actor, include_deleted=True)
            existing = self._idempotency(connection, case_id, request.client_request_id, operation)
            if existing:
                self._assert_same_fingerprint(existing, fingerprint)
                return {"case_id": str(case_id), "replayed": True}
            case = self._case(connection, case_id)
            if case["version"] != request.expected_version:
                raise VersionConflict()
            current_deleted = connection.execute(text("SELECT deleted_at FROM cases WHERE id=:id"), {"id": str(case_id)}).scalar() is not None
            if current_deleted != request.deleted:
                now = datetime.now(UTC)
                revision, version = case["revision"] + 1, case["version"] + 1
                result = connection.execute(text("""UPDATE cases SET deleted_at=:deleted_at, deleted_by=:deleted_by,
                    revision=:revision, version=:version, fingerprint=:fingerprint, updated_at=:now, updated_by=:actor
                    WHERE id=:id AND version=:expected"""), {
                    "deleted_at": now if request.deleted else None, "deleted_by": actor.actor_id if request.deleted else None,
                    "revision": revision, "version": version, "fingerprint": self._case_fingerprint(case_id, case["mode"], case["loss_status"], revision, version),
                    "now": now, "actor": actor.actor_id, "id": str(case_id), "expected": request.expected_version,
                })
                if result.rowcount != 1:
                    raise VersionConflict()
                self._insert_event(connection, uuid4(), case_id, EventType.CASE_UPDATED, EntityType.CASE, actor,
                                   Visibility.BANK_INTERNAL, revision, {"change": "CASE_DELETED" if request.deleted else "CASE_RESTORED"})
            self._insert_idempotency(connection, case_id, request.client_request_id, operation, fingerprint, EntityType.CASE, case_id)
            return {"case_id": str(case_id), "replayed": False}

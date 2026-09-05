"""Workspace mutations preserve the shared Case source and server actor boundary."""
from datetime import UTC, datetime
import hashlib
import hmac
from uuid import UUID, uuid4

from sqlalchemy import text

from backend.contracts.case import ActorContext, ActorRole, CaseTrashRequest, EntityType, EventType, Visibility
from backend.contracts.personal import CreatePersonalNote, SetPersonalBookmark, PersonalWorkspace, PersonalNote, PersonalBookmark
from backend.general_api.app.domains.cases.repository import (
    CaseRepository, CaseAccessDenied, CaseNotFound, VersionConflict, _canonical_hash,
)


class AdminCredentialUnavailable(Exception):
    pass


class AdminCredentialRejected(Exception):
    pass


class WorkspaceRepository(CaseRepository):
    def _bank_scope(self, connection, case_id: UUID, actor: ActorContext):
        if actor.role != ActorRole.BANK_STAFF:
            raise CaseAccessDenied()
        self._require_participant(connection, case_id, actor)

    def personal(self, case_id: UUID, actor: ActorContext) -> PersonalWorkspace:
        with self.engine.connect() as connection:
            self._bank_scope(connection, case_id, actor)
            return self._personal(connection, case_id, actor)

    @staticmethod
    def _personal(connection, case_id: UUID, actor: ActorContext) -> PersonalWorkspace:
        params = {"case_id": str(case_id), "owner": actor.actor_id}
        notes = [PersonalNote.model_validate(dict(row)) for row in connection.execute(text("""
            SELECT id, content, version, created_at FROM personal_notes
            WHERE case_id=:case_id AND owner_id=:owner AND deleted_at IS NULL ORDER BY created_at DESC, id DESC
        """), params).mappings()]
        bookmarks = [PersonalBookmark.model_validate(dict(row)) for row in connection.execute(text("""
            SELECT b.id, b.target_entity_type, b.target_entity_id, b.version,
                CASE WHEN b.deleted_at IS NULL THEN 1 ELSE 0 END AS active,
                CASE WHEN e.id IS NOT NULL THEN 1 ELSE 0 END AS available
            FROM bookmarks b LEFT JOIN case_events e ON b.target_entity_type='EVENT' AND e.id=b.target_entity_id
                AND e.case_id=b.case_id AND e.deleted_at IS NULL AND e.visibility IN ('CUSTOMER','BANK_INTERNAL')
            WHERE b.case_id=:case_id AND b.owner_id=:owner AND b.target_entity_type='EVENT'
            ORDER BY b.created_at, b.id
        """), params).mappings()]
        return PersonalWorkspace(actor_id=actor.actor_id, notes=notes, bookmarks=bookmarks)

    def _lock_personal_write(self, connection, case_id: UUID, actor: ActorContext):
        self._bank_scope(connection, case_id, actor)
        # Serialize Case-scoped personal writes (including absent bookmark row) without advancing Shared Case state.
        locked = connection.execute(text("UPDATE cases SET version=version WHERE id=:id AND deleted_at IS NULL"), {"id": str(case_id)})
        if locked.rowcount != 1:
            raise CaseNotFound()
        self._bank_scope(connection, case_id, actor)

    def add_note(self, case_id: UUID, actor: ActorContext, request: CreatePersonalNote) -> PersonalWorkspace:
        operation = "PERSONAL_NOTE"
        fingerprint = _canonical_hash({"actor": actor.actor_id, "content": request.content})
        with self.engine.begin() as connection:
            self._lock_personal_write(connection, case_id, actor)
            existing = self._idempotency(connection, case_id, request.client_request_id, operation)
            if existing:
                self._assert_same_fingerprint(existing, fingerprint)
                return self._personal(connection, case_id, actor)
            note_id = uuid4()
            connection.execute(text("""INSERT INTO personal_notes (id, case_id, owner_id, content, created_by, updated_by)
                VALUES (:id,:case_id,:owner,:content,:owner,:owner)"""), {
                "id": str(note_id), "case_id": str(case_id), "owner": actor.actor_id, "content": request.content,
            })
            self._insert_idempotency(connection, case_id, request.client_request_id, operation, fingerprint, EntityType.NOTE, note_id)
            return self._personal(connection, case_id, actor)

    def set_bookmark(self, case_id: UUID, actor: ActorContext, request: SetPersonalBookmark) -> PersonalWorkspace:
        operation = "PERSONAL_BOOKMARK"
        fingerprint = _canonical_hash({"actor": actor.actor_id, "target": str(request.target_entity_id), "active": request.active})
        with self.engine.begin() as connection:
            self._lock_personal_write(connection, case_id, actor)
            existing = self._idempotency(connection, case_id, request.client_request_id, operation)
            if existing:
                self._assert_same_fingerprint(existing, fingerprint)
                return self._personal(connection, case_id, actor)
            params = {"case_id": str(case_id), "owner": actor.actor_id, "target": str(request.target_entity_id)}
            bookmark = connection.execute(text("""SELECT id,version FROM bookmarks WHERE case_id=:case_id
                AND owner_id=:owner AND target_entity_type='EVENT' AND target_entity_id=:target"""), params).mappings().first()
            version = bookmark["version"] if bookmark else 0
            if version != request.expected_version:
                raise VersionConflict()
            target = connection.execute(text("""SELECT id FROM case_events WHERE id=:target AND case_id=:case_id
                AND deleted_at IS NULL AND visibility IN ('CUSTOMER','BANK_INTERNAL')"""), params).scalar()
            if request.active and not target:
                raise CaseNotFound()
            bookmark_id = UUID(bookmark["id"]) if bookmark else uuid4()
            now = datetime.now(UTC)
            if bookmark:
                connection.execute(text("""UPDATE bookmarks SET deleted_at=:deleted, version=version+1,
                    updated_at=:now, updated_by=:owner WHERE id=:id AND version=:version"""), {
                    "id": str(bookmark_id), "version": version, "owner": actor.actor_id,
                    "deleted": None if request.active else now, "now": now,
                })
            elif request.active:
                connection.execute(text("""INSERT INTO bookmarks (id,case_id,owner_id,target_entity_type,target_entity_id,created_by,updated_by)
                    VALUES (:id,:case_id,:owner,'EVENT',:target,:owner,:owner)"""), {**params, "id": str(bookmark_id)})
            self._insert_idempotency(connection, case_id, request.client_request_id, operation, fingerprint, EntityType.BOOKMARK, bookmark_id)
            return self._personal(connection, case_id, actor)

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

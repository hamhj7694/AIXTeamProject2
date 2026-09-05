from datetime import UTC, datetime
from uuid import UUID, uuid4
from sqlalchemy import text

from backend.contracts.case import ActorContext, EntityType, EventType, Visibility
from backend.contracts.tasks import TaskCreate, TaskUpdate, SuggestionDecision
from backend.general_api.app.domains.cases.repository import CaseNotFound, VersionConflict, _canonical_hash, _decode_json
from backend.general_api.app.domains.cases.workspace_repository import WorkspaceRepository


class StaleSuggestion(Exception):
    pass


class InvalidTaskProposal(Exception):
    pass


class TaskRepository(WorkspaceRepository):
    def mutate(self, case_id: UUID, actor: ActorContext, request: TaskCreate | TaskUpdate | SuggestionDecision,
               *, task_id: UUID | None = None, suggestion_id: UUID | None = None) -> dict:
        operation = 'DECIDE_SUGGESTION' if suggestion_id else 'UPDATE_TASK' if task_id else 'CREATE_TASK'
        fingerprint = _canonical_hash({'actor': actor.actor_id, 'task': str(task_id), 'suggestion': str(suggestion_id),
            'request': request.model_dump(mode='json', exclude={'client_request_id','expected_case_version','expected_version'})})
        with self.engine.begin() as connection:
            self._lock_personal_write(connection, case_id, actor)
            previous = self._idempotency(connection, case_id, request.client_request_id, operation)
            if previous:
                self._assert_same_fingerprint(previous, fingerprint)
                return {'case_id': str(case_id), 'entity_id': previous['response_entity_id'], 'replayed': True}
            query = 'SELECT revision,version,mode,loss_status FROM cases WHERE id=:id'
            if connection.dialect.name == 'mysql':
                query += ' FOR UPDATE'
            case = connection.execute(text(query), {'id': str(case_id)}).mappings().one()
            if case['version'] != request.expected_case_version:
                raise VersionConflict()
            now = datetime.now(UTC)
            revision, version = case['revision'] + 1, case['version'] + 1
            if suggestion_id:
                row = connection.execute(text("""SELECT * FROM ai_suggestions WHERE id=:id AND case_id=:cid
                    AND suggestion_type='TASK' AND deleted_at IS NULL AND visibility IN ('CUSTOMER','BANK_INTERNAL')"""), {'id': str(suggestion_id), 'cid': str(case_id)}).mappings().first()
                if not row:
                    raise CaseNotFound()
                if row['version'] != request.expected_version or row['status'] != 'PENDING':
                    raise VersionConflict()
                if request.decision != 'REJECT' and row['source_revision'] != case['revision']:
                    raise StaleSuggestion()
                task_id = None
                if request.decision != 'REJECT':
                    proposal = _decode_json(row['proposal'])
                    proposed = request.title if request.decision == 'EDIT' else proposal.get('title')
                    if not isinstance(proposed, str) or not 0 < len(proposed.strip()) <= 300:
                        raise InvalidTaskProposal()
                    task_id = self._new_task(connection, case_id, actor, request.client_request_id, proposed.strip())
                    self._insert_event(connection, uuid4(), case_id, EventType.ENTITY_CREATED, EntityType.TASK, actor,
                        Visibility.BANK_INTERNAL, revision, {'suggestion_id': str(suggestion_id)}, task_id)
                status = {'ACCEPT':'ACCEPTED','EDIT':'EDITED','REJECT':'REJECTED'}[request.decision]
                connection.execute(text("UPDATE ai_suggestions SET status=:status,version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"),
                    {'status': status, 'now': now, 'actor': actor.actor_id, 'id': str(suggestion_id)})
                self._insert_event(connection, uuid4(), case_id, EventType.ENTITY_UPDATED, EntityType.AI_SUGGESTION, actor,
                    Visibility.BANK_INTERNAL, revision, {'decision': status, 'task_id': str(task_id) if task_id else None}, suggestion_id)
                entity_id, entity_type = suggestion_id, EntityType.AI_SUGGESTION
            elif task_id:
                row = connection.execute(text('SELECT version FROM tasks WHERE id=:id AND case_id=:cid AND deleted_at IS NULL'),
                    {'id': str(task_id), 'cid': str(case_id)}).mappings().first()
                if not row:
                    raise CaseNotFound()
                if row['version'] != request.expected_version:
                    raise VersionConflict()
                connection.execute(text("""UPDATE tasks SET title=:title,status=:status,result=:result,cancel_reason=:reason,
                    version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"""), {
                    'title': request.title, 'status': request.status, 'result': request.result,
                    'reason': request.cancel_reason, 'now': now, 'actor': actor.actor_id, 'id': str(task_id)})
                self._insert_event(connection, uuid4(), case_id, EventType.ENTITY_UPDATED, EntityType.TASK, actor,
                    Visibility.BANK_INTERNAL, revision, {'status': request.status}, task_id)
                entity_id, entity_type = task_id, EntityType.TASK
            else:
                entity_id = self._new_task(connection, case_id, actor, request.client_request_id, request.title)
                entity_type = EntityType.TASK
                self._insert_event(connection, uuid4(), case_id, EventType.ENTITY_CREATED, EntityType.TASK, actor,
                    Visibility.BANK_INTERNAL, revision, {}, entity_id)
            connection.execute(text("""UPDATE cases SET revision=:revision,version=:version,fingerprint=:fp,
                updated_at=:now,updated_by=:actor WHERE id=:id"""), {'revision': revision, 'version': version,
                'fp': self._case_fingerprint(case_id, case['mode'], case['loss_status'], revision, version),
                'now': now, 'actor': actor.actor_id, 'id': str(case_id)})
            self._insert_idempotency(connection, case_id, request.client_request_id, operation, fingerprint, entity_type, entity_id)
            return {'case_id': str(case_id), 'entity_id': str(entity_id), 'replayed': False}

    @staticmethod
    def _new_task(connection, case_id, actor, request_id, title):
        task_id = uuid4()
        connection.execute(text("""INSERT INTO tasks (id,case_id,title,client_request_id,created_by,updated_by)
            VALUES (:id,:cid,:title,:request,:actor,:actor)"""), {'id': str(task_id), 'cid': str(case_id),
            'title': title, 'request': str(request_id), 'actor': actor.actor_id})
        return task_id

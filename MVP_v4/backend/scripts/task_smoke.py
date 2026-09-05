"""P3-002 concurrency checks against a disposable MySQL owned by phase0_smoke."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from backend.contracts.case import ActorContext, ActorRole, CreateCaseRequest
from backend.contracts.tasks import TaskCreate
from backend.general_api.app.domains.cases.repository import VersionConflict
from backend.general_api.app.domains.cases.tasks_repository import TaskRepository


def check_task_contention(settings):
    actor = ActorContext(actor_id="task-contention-staff", role=ActorRole.BANK_STAFF)
    repository = TaskRepository(settings)
    try:
        cid = uuid4()
        repository.create_case(actor, CreateCaseRequest(client_request_id=cid, customer_participant_id="task-customer"))
        request = TaskCreate(client_request_id=uuid4(), expected_case_version=1, title="Concurrent duplicate")
        barrier = Barrier(4)

        def same_request(_):
            barrier.wait(timeout=10)
            return repository.mutate(cid, actor, request)

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(same_request, range(4)))
        assert len({result["entity_id"] for result in results}) == 1
        assert sum(not result["replayed"] for result in results) == 1
        assert repository.bank_workspace(cid, actor).case.revision == 2
        barrier = Barrier(2)

        def competing_request(_):
            candidate = TaskCreate(client_request_id=uuid4(), expected_case_version=2, title="Competing change")
            barrier.wait(timeout=10)
            try:
                repository.mutate(cid, actor, candidate)
                return "committed"
            except VersionConflict:
                return "stale"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(competing_request, range(2)))
        assert sorted(results) == ["committed", "stale"]
        workspace = repository.bank_workspace(cid, actor)
        assert workspace.case.revision == 3 and len(workspace.tasks) == 2 and len(workspace.events) == 3
        return "PASS: four simultaneous duplicates commit once; two competing versions yield one commit/one conflict"
    finally:
        repository.close()

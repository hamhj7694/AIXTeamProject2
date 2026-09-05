from dataclasses import replace
import json
from uuid import uuid4

from sqlalchemy import text
from backend.contracts.case import ActorContext, ActorRole
from backend.database import database_engine
from backend.general_api.app.main import get_settings
from test_case_api import case_api, create_staff_case


def test_trash_password_version_replay_restore_and_audit(case_api):
    client, settings, actor = case_api
    settings = replace(settings, admin_case_password='test-administrator')
    client.app.dependency_overrides[get_settings] = lambda: settings
    case_id, created = create_staff_case(client)
    request = dict(client_request_id=str(uuid4()), expected_version=1, deleted=True, admin_password='wrong')
    url = f'/api/v4/cases/{case_id}/trash'
    assert client.post(url, json=request).status_code == 403
    assert client.get(f'/api/v4/cases/{case_id}').json()['case']['version'] == 1
    request['admin_password'] = 'test-administrator'
    assert client.post(url, json={**request, 'expected_version': 99}).status_code == 409
    assert client.post(url, json=request).status_code == 200
    assert client.post(url, json=request).json()['replayed'] is True
    assert client.get('/api/v4/cases').json() == []
    assert client.get('/api/v4/cases?deleted=true').json()[0]['version'] == 2
    assert client.get(f'/api/v4/cases/{case_id}').status_code == 404
    assert client.get(f'/api/v4/cases/{case_id}/delta').status_code == 404
    assert client.get(f'/api/v4/cases/{case_id}/workspace').status_code == 404
    restore = {**request, 'client_request_id': str(uuid4()), 'expected_version': 2, 'deleted': False}
    assert client.post(url, json=restore).status_code == 200
    assert client.get('/api/v4/cases?deleted=true').json() == []
    assert client.get('/api/v4/cases').json()[0]['version'] == 3
    projection = client.get(f'/api/v4/cases/{case_id}').json()
    assert [event['payload'].get('change') for event in projection['events'][1:]] == ['CASE_DELETED', 'CASE_RESTORED']
    assert all(event['actor_id'] == 'staff-1' and event['created_at'] for event in projection['events'])
    assert 'test-administrator' not in json.dumps(projection)
    assert 'test-administrator' not in client.post(url, json={**restore, 'expected_version': 0}).text
    actor['value'] = ActorContext(actor_id='customer-1', role=ActorRole.CUSTOMER)
    assert client.post(url, json=restore).status_code == 403
    assert len(client.get(f'/api/v4/cases/{case_id}').json()['events']) == 1
    actor['value'] = ActorContext(actor_id='other-staff', role=ActorRole.BANK_STAFF)
    assert client.get('/api/v4/cases?deleted=true').json() == []
    assert client.post(url, json=restore).status_code == 404


def test_user_metadata_is_explicit_not_private_payload_search(case_api):
    client, settings, _ = case_api
    cid = str(uuid4())
    assert client.post('/api/v4/cases', json=dict(client_request_id=cid, customer_participant_id='customer-1',
        title='사칭 전화 상담', summary='송금 여부 확인 중')).status_code == 201
    engine = database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO case_events (id,case_id,visibility,event_type,entity_type,actor_role,case_revision,payload)
                VALUES (:id,:cid,'AI_PRIVATE','ENTITY_CREATED','FACT','AI',1,:payload)"""),
                dict(id=str(uuid4()),cid=cid,payload=json.dumps({'private':'private-search-secret'})))
        row = client.get('/api/v4/cases').json()[0]
        assert row['title'] == '사칭 전화 상담' and row['created_at']
        assert 'private-search-secret' not in json.dumps(row)
    finally:
        engine.dispose()


def test_unconfigured_admin_has_no_default(case_api):
    client, _, _ = case_api
    cid, _ = create_staff_case(client)
    assert client.post(f'/api/v4/cases/{cid}/trash', json=dict(client_request_id=str(uuid4()),
        expected_version=1, deleted=True, admin_password='arbitrary')).status_code == 503

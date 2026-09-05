from uuid import uuid4
from sqlalchemy import text
from backend.contracts.case import ActorContext, ActorRole
from backend.database import database_engine
from test_case_api import case_api, create_staff_case


def test_notes_private_owner_idempotency_and_no_case_revision(case_api):
    client, settings, actor = case_api
    cid, initial = create_staff_case(client)
    url = f'/api/v4/cases/{cid}/personal'
    request = {'client_request_id': str(uuid4()), 'content': 'My private working note'}
    first = client.post(url+'/notes', json=request)
    assert first.status_code == 200
    assert first.json()['notes'][0]['content'] == request['content']
    assert len(client.post(url+'/notes', json=request).json()['notes']) == 1
    assert client.post(url+'/notes', json={**request,'content':'changed'}).status_code == 409
    assert client.post(url+'/notes', json={**request,'owner_id':'other'}).status_code == 422
    assert client.post(url+'/notes', json={**request,'content':'  '}).status_code == 422
    assert client.get(f'/api/v4/cases/{cid}').json() == initial
    assert request['content'] not in client.get(f'/api/v4/cases/{cid}/workspace').text
    engine=database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO case_participants (id,case_id,participant_id,role) VALUES (:id,:cid,'staff-2','BANK_STAFF')"),{'id':str(uuid4()),'cid':str(cid)})
        actor['value']=ActorContext(actor_id='staff-2',role=ActorRole.BANK_STAFF)
        assert client.get(url).json()['notes'] == []
        assert client.post(url+'/notes',json=request).status_code == 409
        actor['value']=ActorContext(actor_id='customer-1',role=ActorRole.CUSTOMER)
        assert client.get(url).status_code == 403
        assert client.post(url+'/notes',json=request).status_code == 403
        assert request['content'] not in client.get(f'/api/v4/cases/{cid}').text
    finally: engine.dispose()


def test_bookmark_toggle_reference_version_visibility_missing_target(case_api):
    client,settings,actor=case_api
    cid,initial=create_staff_case(client)
    target=initial['events'][0]['id']; url=f'/api/v4/cases/{cid}/personal'
    request={'client_request_id':str(uuid4()),'target_entity_id':target,'active':True,'expected_version':0}
    first=client.post(url+'/bookmarks',json=request)
    assert first.status_code == 200,first.text
    bookmark=first.json()['bookmarks'][0]
    assert bookmark['active'] and bookmark['available'] and bookmark['version']==1
    assert set(bookmark) == {'id','target_entity_type','target_entity_id','version','active','available'}
    assert client.post(url+'/bookmarks',json=request).json()['bookmarks'][0]['version']==1
    assert client.post(url+'/bookmarks',json={**request,'client_request_id':str(uuid4())}).status_code==409
    cancel={**request,'client_request_id':str(uuid4()),'expected_version':1,'active':False}
    assert not client.post(url+'/bookmarks',json=cancel).json()['bookmarks'][0]['active']
    activate={**request,'client_request_id':str(uuid4()),'expected_version':2}
    assert client.post(url+'/bookmarks',json=activate).json()['bookmarks'][0]['active']
    assert client.get(f'/api/v4/cases/{cid}').json() == initial
    engine=database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE case_events SET visibility='AI_PRIVATE' WHERE id=:id"),{'id':target})
        assert not client.get(url).json()['bookmarks'][0]['available']
        assert client.post(url+'/bookmarks',json={**request,'client_request_id':str(uuid4()),'expected_version':3}).status_code==404
        assert client.post(url+'/bookmarks',json={**cancel,'client_request_id':str(uuid4()),'expected_version':3}).status_code==200
        other_id,other=create_staff_case(client)
        assert client.post(f'/api/v4/cases/{other_id}/personal/bookmarks',json=request).status_code==404
        actor['value']=ActorContext(actor_id='customer-1',role=ActorRole.CUSTOMER)
        assert client.get(url).status_code==403
        assert client.post(url+'/bookmarks',json=request).status_code==403
    finally:engine.dispose()

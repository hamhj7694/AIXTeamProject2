import json
from uuid import uuid4
import pytest
from sqlalchemy import text
from backend.contracts.case import ActorContext, ActorRole
from backend.database import database_engine
from test_case_api import case_api, create_staff_case


def test_task_lifecycle_result_reason_same_id_replay_stale_and_customer_scope(case_api):
    client,settings,actor=case_api
    cid,initial=create_staff_case(client);base=f'/api/v4/cases/{cid}'
    create={'client_request_id':str(uuid4()),'expected_case_version':1,'title':'거래 사실 확인'}
    first=client.post(base+'/tasks',json=create);assert first.status_code==200,first.text
    tid=first.json()['entity_id']
    assert client.post(base+'/tasks',json=create).json()['entity_id']==tid
    workspace=client.get(base+'/workspace').json()
    assert len(workspace['tasks'])==1 and workspace['case']['version']==2
    assert not workspace['suggestions']
    update={'client_request_id':str(uuid4()),'expected_case_version':2,'expected_version':1,'title':'거래 확인 완료','status':'COMPLETED'}
    assert client.post(base+f'/tasks/{tid}',json=update).status_code==422
    assert client.post(base+f'/tasks/{tid}',json={**update,'status':'CANCELLED'}).status_code==422
    update['result']='고객 확인 답변을 검토했습니다.'
    assert client.post(base+f'/tasks/{tid}',json=update).status_code==200
    assert client.post(base+f'/tasks/{tid}',json=update).json()['replayed']
    assert client.post(base+f'/tasks/{tid}',json={**update,'client_request_id':str(uuid4())}).status_code==409
    reopen={**update,'client_request_id':str(uuid4()),'expected_case_version':3,'expected_version':2,'status':'IN_PROGRESS'}
    assert client.post(base+f'/tasks/{tid}',json=reopen).status_code==200
    cancel={**reopen,'client_request_id':str(uuid4()),'expected_case_version':4,'expected_version':3,'status':'CANCELLED','cancel_reason':'중복 업무 확인'}
    assert client.post(base+f'/tasks/{tid}',json=cancel).status_code==200
    data=client.get(base+'/workspace').json()
    assert data['tasks'][0]['id']==tid and data['tasks'][0]['version']==4
    delta=client.get(base+'/delta?known_revision=1').json()
    assert any(item['entity_id']==tid and item['data']['status']=='CANCELLED' for item in delta['upserts'])
    engine=database_engine(settings)
    try:
        with engine.connect() as connection:
            assert connection.execute(text('SELECT COUNT(*) FROM customer_progress')).scalar()==0
    finally:engine.dispose()
    actor['value']=ActorContext(actor_id='customer-1',role=ActorRole.CUSTOMER)
    assert client.get(base).json()['events']==initial['events']
    assert all(item['entity_id']!=tid for item in client.get(base+'/delta').json()['upserts'])
    assert client.post(base+'/tasks',json=create).status_code==403


@pytest.mark.parametrize('decision', ['ACCEPT','EDIT','REJECT'])
def test_persisted_suggestion_only_adoption_creates_task_and_preserves_original(case_api, decision):
    client,settings,_=case_api
    cid,_=create_staff_case(client);sid=str(uuid4());base=f'/api/v4/cases/{cid}'
    engine=database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO ai_suggestions (id,case_id,suggestion_type,proposal,source_revision)
                VALUES (:id,:cid,'TASK',:proposal,1)"""),{'id':sid,'cid':str(cid),'proposal':json.dumps({'title':'제안 원안'})})
        assert client.get(base+'/workspace').json()['tasks']==[]
        request={'client_request_id':str(uuid4()),'expected_case_version':1,'expected_version':1,'decision':decision}
        if decision=='EDIT':request['title']='직원 수정안'
        url=base+f'/suggestions/{sid}/decision'
        assert client.post(url,json=request).status_code==200
        assert client.post(url,json=request).json()['replayed']
        assert client.post(url,json={**request,'client_request_id':str(uuid4()),'expected_case_version':2}).status_code==409
        data=client.get(base+'/workspace').json()
        assert len(data['tasks'])==(0 if decision=='REJECT' else 1)
        assert data['suggestions'][0]['proposal']['title']=='제안 원안'
        if decision=='EDIT':assert data['tasks'][0]['title']=='직원 수정안'
        assert data['case']['revision']==2
        audit = next(event for event in data['events'] if event['entity_id'] == sid and event['entity_type'] == 'AI_SUGGESTION')
        assert audit['payload']['decision']=={'ACCEPT':'ACCEPTED','EDIT':'EDITED','REJECT':'REJECTED'}[decision]
    finally:engine.dispose()


def test_stale_and_private_suggestions_cannot_be_adopted(case_api):
    client,settings,_=case_api
    cid,_=create_staff_case(client);sid=str(uuid4());base=f'/api/v4/cases/{cid}'
    engine=database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO ai_suggestions (id,case_id,suggestion_type,proposal,source_revision)
                VALUES (:id,:cid,'TASK',:proposal,1)"""),{'id':sid,'cid':str(cid),'proposal':json.dumps({'title':'제안'})})
        client.post(base+'/tasks',json={'client_request_id':str(uuid4()),'expected_case_version':1,'title':'추가 확인'})
        request={'client_request_id':str(uuid4()),'expected_case_version':2,'expected_version':1,'decision':'ACCEPT'}
        response=client.post(base+f'/suggestions/{sid}/decision',json=request)
        assert response.status_code==409 and response.json()['detail']['code']=='SUGGESTION_STALE'
        assert client.get(base+'/workspace').json()['case']['revision']==2
        with engine.begin() as connection:
            connection.execute(text("UPDATE ai_suggestions SET visibility='AI_PRIVATE' WHERE id=:id"),{'id':sid})
        assert client.get(base+'/workspace').json()['suggestions']==[]
        assert client.post(base+f'/suggestions/{sid}/decision',json=request).status_code==404
    finally:engine.dispose()

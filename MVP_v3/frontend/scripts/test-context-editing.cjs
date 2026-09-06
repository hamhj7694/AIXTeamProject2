const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const {buildSync} = require('esbuild');
const React = require('react');

// Run the production component's handlers with in-memory hooks/API boundaries.
// This checks persistence commands, not browser layout or a copied algorithm.
function component(file, name, props, initialState = [], bindings = {}, context = null) {
  const state = [...initialState], refs = [];
  let cursor = 0, refCursor = 0;
  const react = {...React, useEffect() {}, useContext: () => context,
    useState(initial) {
      const index = cursor++;
      if (!(index in state)) state[index] = typeof initial === 'function' ? initial() : initial;
      return [state[index], value => {state[index] = typeof value === 'function' ? value(state[index]) : value;}];
    },
    useRef(initial) { const index = refCursor++; return refs[index] ??= {current: initial}; },
  };
  const result = buildSync({entryPoints:[path.resolve(__dirname, '../src/components', file)], bundle:true, platform:'node', format:'cjs', packages:'external', write:false,
    external:['../api/client', '../api/cases', '../api/contextWorkspace'], define:{'import.meta.env':'{}'}});
  const module = {exports:{}};
  vm.runInNewContext(result.outputFiles[0].text, {module, exports:module.exports, crypto:webcrypto, Error,
    require: id => id === 'react' ? react : bindings[id] ?? ({'../api/client':{}, '../api/cases':{CURRENT_BANK_USER:{user_id:'test-staff'}}})[id] ?? require(id)});
  return {state, render() {cursor = 0; refCursor = 0; return module.exports[name](props);}};
}
function find(element, predicate) {
  if (!element || typeof element !== 'object') return null;
  if (Array.isArray(element)) return element.map(child => find(child, predicate)).find(Boolean);
  if (predicate(element)) return element;
  return find(element.props?.children, predicate);
}
const text = value => Array.isArray(value) ? value.map(text).join('')
  : value && typeof value === 'object' ? text(value.props?.children)
  : typeof value === 'string' ? value : '';
const button = (tree, label) => {
  const found = find(tree, node => node.type === 'button' && (node.props['aria-label'] === label || text(node).includes(label)));
  assert.ok(found, 'Missing control: ' + label);
  return found;
};
const flush = () => new Promise(resolve => setImmediate(resolve));
const empty = {
  case_id:'TEST',context_revision:1,permissions_mode:'MVP_OPEN',can_write:true,can_review:true,
  confirmed_facts:[],proposed_facts:[],open_gaps:[],archived_gaps:[],ai_suggestions:[],reviewed_suggestions:[],
  active_tasks:[],archived_tasks:[],recent_decisions:[],legacy_facts:[],legacy_suggestions:[],legacy_gaps:[],
  legacy_records:[],legacy_archived_suggestions:[],
};

(async () => {
  const writes = [];
  let archiveSequence = 0;
  const context = {ready:true, items:[], async save(section, operation, version, text) {
    writes.push({section,operation,version,text});
    const current = context.items.find(item => item.semantic_key === 'display');
    assert.equal(version, current?.item_version ?? 0);
    const item = {item_id:current?.item_id ?? `display-${section}`,section,semantic_key:'display',item_version:version + 1,staff_text:operation === 'EDIT' ? text : current?.staff_text ?? null,deleted_by:operation === 'DELETE' ? 'staff' : null};
    context.items = [...context.items.filter(entry => entry.semantic_key !== 'display'),item]; return item;
  }, async archiveLine(section, version, text, archivedText, archiveIndex) {
    writes.push({section,operation:'ARCHIVE',version,text,archivedText,archiveIndex});
    const current = context.items.find(item => item.semantic_key === 'display');
    assert.equal(version, current?.item_version ?? 0);
    const display = {item_id:current?.item_id ?? `display-${section}`,section,semantic_key:'display',item_version:version + 1,staff_text:text ?? null,deleted_by:text ? null : 'staff'};
    const archive = {item_id:`archive-${++archiveSequence}`,section,semantic_key:`display-archive:${archiveSequence}`,item_version:1,staff_text:archivedText,deleted_by:'staff',archive_index:archiveIndex};
    context.items = [...context.items.filter(entry => entry.semantic_key !== 'display'),display,archive];
  }, async restoreArchive(section, version, archive) {
    writes.push({section,operation:'RESTORE_ARCHIVE',version,archiveItemId:archive.item_id});
    const current = context.items.find(item => item.semantic_key === 'display');
    assert.equal(version,current.item_version);
    const lines = current.deleted_by ? [] : current.staff_text.split('\n');
    lines.splice(Math.min(archive.archive_index,lines.length),0,archive.staff_text);
    const display = {...current,item_version:current.item_version + 1,staff_text:lines.join('\n'),deleted_by:null};
    context.items = [...context.items.filter(entry => entry.item_id !== current.item_id && entry.item_id !== archive.item_id),display];
  }};
  const edit = component('EditableContext.tsx','EditableContext',{section:'SUMMARY',title:'요약',lines:['첫째','둘째','셋째']},[],{},context);
  button(edit.render(),'요약 2번째 항목 삭제').props.onClick(); await flush();
  assert.deepEqual(writes.at(-1), {section:'SUMMARY',operation:'ARCHIVE',version:0,text:'첫째\n셋째',archivedText:'둘째',archiveIndex:1});
  const remount = component('EditableContext.tsx','EditableContext',{section:'SUMMARY',title:'요약',lines:['새 AI 내용']},[],{},context);
  assert.equal(find(remount.render(), node => node.props?.className === 'context-line-text').props.children, '첫째');
  button(edit.render(),'요약 1번째 항목 수정').props.onClick();
  find(edit.render(), node => node.type === 'textarea').props.onChange({target:{value:'직원 수정'}});
  find(edit.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(writes.at(-1).text,'직원 수정\n셋째');
  button(edit.render(),'요약 2번째 항목 삭제').props.onClick(); await flush();
  button(edit.render(),'요약 1번째 항목 삭제').props.onClick(); await flush();
  assert.equal(writes.at(-1).operation,'ARCHIVE');
  assert.equal(find(edit.render(), node => node.type === 'li' && node.props?.className === 'context-line'), undefined);
  for (const [section, title] of [['SUMMARY','사건 요약'],['EXPOSURE','피해·노출'],['CLAIM','상대방 주장'],['DEMAND','상대방 요구']]) {
    const hiddenContext = {ready:true,items:[
      {item_id:`display-${section}`,section,semantic_key:'display',item_version:1,staff_text:null,deleted_by:'staff'},
      {item_id:`archive-${section}`,section,semantic_key:`display-archive:${section}`,item_version:1,staff_text:'삭제된 내용',deleted_by:'staff',archive_index:0},
    ],save:context.save,archiveLine:context.archiveLine,restoreArchive:context.restoreArchive};
    const hidden = component('EditableContext.tsx','EditableContext',{section,title,lines:[]},[],{},hiddenContext);
    assert.equal(find(hidden.render(), node => node.type === 'button' && node.props['aria-label'] === `${title} 삭제 취소`), undefined);
    assert.ok(find(hidden.render(), node => node.type === 'summary' && node.props.children === '완료·삭제'));
    assert.ok(find(hidden.render(), node => node.type === 'button' && node.props['aria-label'] === `${title} 삭제 항목 복원`));
  }
  button(edit.render(),'요약 추가').props.onClick();
  find(edit.render(), node => node.type === 'textarea').props.onChange({target:{value:'새 기록'}});
  find(edit.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(writes.at(-2).operation,'RESTORE');
  assert.equal(writes.at(-1).text,'새 기록');
  assert.equal(context.items.find(item => item.semantic_key === 'display').deleted_by,null);
  while (context.items.some(item => item.semantic_key.startsWith('display-archive:') && item.deleted_by)) {
    button(edit.render(),'요약 삭제 항목 복원').props.onClick(); await flush();
  }
  assert.equal(find(edit.render(), node => node.type === 'summary' && node.props.children === '완료·삭제'), undefined);

  button(edit.render(),'요약 1번째 항목 수정').props.onClick();
  const previousSave = context.save;
  context.save = async () => {throw new Error('다른 직원이 수정했습니다.');};
  find(edit.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.ok(find(edit.render(), node => node.type === 'textarea'));
  assert.equal(find(edit.render(), node => node.props?.role === 'alert').props.children,'다른 직원이 수정했습니다.');
  context.save = previousSave;

  const commands = [];
  const row = {task_id:'task-1',title:'확인',description:'확인',version:3,status:'TODO'};
  const workspace = {...empty,active_tasks:[row]};
  const tasks = component('ContextWorkspace.tsx','ContextWorkspace',{caseId:'TEST',refreshKey:'1',institutions:null,onOpenParticipants(){}},[workspace,'',false,null],{
    '../api/contextWorkspace':{loadContextWorkspace:async () => workspace,saveContextCommand:async (...args) => {commands.push(args);}},
  });
  button(tasks.render(),'결과 기록').props.onClick();
  assert.equal(commands.length,0); // check opens result entry; no invented completion
  assert.equal(button(tasks.render(),'저장').props.disabled,true);
  find(tasks.render(), node => node.type === 'textarea').props.onChange({target:{value:'고객과 확인함'}});
  find(tasks.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(commands[0][1],'tasks/task-1/complete');
  assert.equal(commands[0][3].expected_version,3);
  assert.equal(commands[0][3].result_summary,'고객과 확인함');
  button(tasks.render(),'취소').props.onClick();
  find(tasks.render(), node => node.type === 'textarea').props.onChange({target:{value:'직원이 할 일 목록에서 삭제'}});
  find(tasks.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(commands.at(-1)[1],'tasks/task-1/cancel');
  assert.equal(commands.at(-1)[3].reason,'직원이 할 일 목록에서 삭제');
  workspace.active_tasks = []; workspace.archived_tasks = [{...row,status:'CANCELLED',version:4}];
  button(tasks.render(),'다시 진행').props.onClick();
  find(tasks.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(commands.at(-1)[3].status,'TODO');
  assert.equal(commands.at(-1)[3].expected_version,4);
  workspace.legacy_records = [{id:'old-1',title:'기존 메모',status:'REQUESTED'}];
  assert.ok(find(tasks.render(), node => node.props?.children === '기존 메모'));
  button(tasks.render(),'업무 추가').props.onClick();
  find(tasks.render(), node => node.type === 'input').props.onChange({target:{value:'새 업무'}});
  find(tasks.render(), node => node.type === 'textarea').props.onChange({target:{value:'새 업무 상세'}});
  find(tasks.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(commands.at(-1)[1],'tasks');
  assert.equal(commands.at(-1)[3].title,'새 업무');
  assert.equal(commands.at(-1)[3].description,'새 업무 상세');
  assert.ok(commands.at(-1)[3].client_request_id);

  const composerWrites = [];
  let attempt = 0, done = 0, closed = 0;
  const action = component('CaseActionDialogs.tsx','ActionDialog',{caseId:'TEST',recovery:false,onDone:async () => {done++;},onClose:() => {closed++;}},[],{
    '../api/cases':{casesApi:{createAction:async (...args) => {composerWrites.push(args); if (attempt++ === 0) throw new Error('temporary');}}},
    '../api/contextWorkspace':{saveContextCommand:async () => {}},
  });
  find(action.render(), node => node.type === 'textarea').props.onChange({target:{value:'고객에게 송금 여부 확인'}});
  find(action.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  find(action.render(), node => node.type === 'form').props.onSubmit({preventDefault(){}}); await flush();
  assert.equal(composerWrites.length,2);
  assert.deepEqual(composerWrites[0],['TEST','CUSTOMER_CALLBACK','고객에게 송금 여부 확인']);
  assert.deepEqual(composerWrites[1],composerWrites[0]);
  assert.equal(done,1); assert.equal(closed,1);
  console.log('Context editing: row CRUD, task result/cancel/restore/create, legacy visibility and current action API retry passed');
})().catch(error => {console.error(error); process.exitCode = 1;});

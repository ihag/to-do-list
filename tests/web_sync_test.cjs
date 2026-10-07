const assert = require('node:assert/strict');
globalThis.crypto = require('node:crypto').webcrypto;
require('../web/store.js');
require('../web/sync.js');
const copy = value => JSON.parse(JSON.stringify(value));
const memory = () => { const map = new Map(); return {getItem: key => map.get(key) || null, setItem: (key, value) => map.set(key, value), removeItem: key => map.delete(key)}; };
const initial = {version: 1, topics: [{id: 't', name: '업무', open: true, todos: [{id: 'a', title: '원래 할 일', done: false, due: ''}]}]};
let server = {revision: 0, state: copy(initial)}, offline = false, expired = false, deferred = null;
const mockFetch = async (url, options) => {
  if (offline) throw new Error('Offline');
  if (expired) return {ok: false, status: 401};
  if (url.endsWith('/users/me')) return {ok: true, json: async () => ({id: 1, username: 'alice'})};
  if (options.method === 'PUT') {
    const body = JSON.parse(options.body);
    if (deferred) { const hold = deferred; deferred = null; await hold.promise; }
    if (body.revision !== server.revision) return {ok: false, status: 409};
    server = {revision: server.revision + 1, state: copy(body.state)};
  }
  return {ok: true, json: async () => copy(server)};
};
const create = (storage = memory(), session = memory()) => {
  let rendered, conflict, status;
  const client = new TaskSync.SyncClient({base: 'https://api.example', fetch: mockFetch, storage, session,
    onState: state => { rendered = state; }, onStatus: value => { status = value; }, onAccount: () => {}, onConflict: value => { conflict = value; }});
  return {client, storage, session, state: () => copy(rendered), conflict: () => conflict, status: () => status};
};
(async () => {
  const a = create(), b = create();
  await a.client.connect('token'); await b.client.connect('token');
  const desktop = a.state(); desktop.topics[0].todos[0].done = true;
  a.client.change(desktop); await a.client.flush();
  assert.equal(a.client.dirty, false);
  await b.client.refresh(); assert.equal(b.state().topics[0].todos[0].done, true);
  // 동시 수정: 다른 항목의 변경을 합치고 같은 항목은 명시적 선택 후 처리한다.
  const phone = b.state(); phone.topics[0].name = '휴대폰 주제';
  b.client.change(phone);
  desktop.topics[0].todos.push({id: 'b', title: 'PC 추가', done: false, due: ''});
  a.client.change(desktop); await a.client.flush(); await b.client.flush();
  assert.ok(b.conflict()); assert.equal(server.state.topics[0].name, '업무');
  const conflictReload = create(b.storage, memory());
  await conflictReload.client.connect('token');
  assert.ok(conflictReload.conflict(), 'Reload must preserve the conflict instead of overwriting remote changes');
  conflictReload.client.logout();
  b.client.resolve(true); await b.client.flush();
  assert.equal(server.state.topics[0].name, '휴대폰 주제');
  assert.equal(server.state.topics[0].todos.length, 2);
  // 저장 요청 도중의 추가 편집도 별도 버전으로 이어서 저장한다.
  await a.client.refresh();
  let release; deferred = {promise: new Promise(resolve => { release = resolve; })};
  const edit = a.state(); edit.topics[0].name = '첫 변경'; a.client.change(edit);
  const saving = a.client.flush();
  edit.topics[0].name = '추가 변경'; a.client.change(edit); release(); await saving;
  assert.equal(server.state.topics[0].name, '추가 변경'); assert.equal(a.client.dirty, false);
  // 오프라인의 미저장 변경은 로그아웃/새 로그인 후 복원한다.
  offline = true; edit.topics[0].name = '오프라인 변경'; a.client.change(edit); await a.client.flush();
  assert.equal(a.client.dirty, true); assert.equal(JSON.parse(a.storage.getItem('taskflow.cloud.1')).dirty, true);
  a.client.logout(); offline = false;
  const reopened = create(a.storage, a.session); await reopened.client.connect('token'); await reopened.client.flush();
  assert.equal(server.state.topics[0].name, '오프라인 변경');
  // 만료된 토큰도 브라우저 게스트 목록을 덮어쓰지 않는다.
  reopened.storage.setItem(TaskStore.KEY, JSON.stringify(initial)); expired = true;
  const pending = reopened.state(); pending.topics[0].name = '만료 후 변경'; reopened.client.change(pending); await reopened.client.flush();
  assert.equal(reopened.client.expired, true); assert.equal(reopened.client.dirty, true);
  assert.deepEqual(JSON.parse(reopened.storage.getItem(TaskStore.KEY)), initial);
  assert.equal(reopened.storage.getItem('taskflow.cloud.1').includes('token'), false);
  expired = false; await reopened.client.connect('new-token'); await reopened.client.flush();
  assert.equal(server.state.topics[0].name, '만료 후 변경');
  // 삭제가 포함된 3방향 병합에서 원격 추가와 수정은 유지한다.
  const local = copy(initial); local.topics[0].todos = [];
  const remote = copy(initial); remote.topics[0].todos.push({id:'c', title:'원격 추가', done:false, due:''});
  assert.deepEqual(TaskSync.mergeWorkspace(initial, local, remote).topics[0].todos.map(todo => todo.id), ['c']);
  const noStorage = create({getItem: () => null, setItem: () => {throw new Error('Quota');}, removeItem: () => {}});
  await noStorage.client.connect('token'); offline = true;
  const memoryEdit = noStorage.state(); memoryEdit.topics[0].name = '기기 백업 실패'; noStorage.client.change(memoryEdit); await noStorage.client.flush();
  assert.equal(noStorage.client.cached, false);
  assert.ok(noStorage.status().includes('탭을 닫지 마세요'));
  offline = false; await noStorage.client.connect('token'); await noStorage.client.flush();
  assert.equal(server.state.topics[0].name, '기기 백업 실패', 'Same-account login must retain edits in memory even when backup fails');
  noStorage.client.logout();
  [a, b, reopened].forEach(item => item.client.logout());
  console.log('Sync tests passed: two clients, conflict merge, in-flight edits, offline recovery, token expiry, guest isolation, deletion merge.');
})().catch(error => { console.error(error); process.exit(1); });

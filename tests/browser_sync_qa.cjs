const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const url = process.env.TASKFLOW_QA_URL || 'http://127.0.0.1:8081/';
(async () => {
  const version = await (await fetch('http://127.0.0.1:9227/json/version')).json();
  const socket = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise(resolve => socket.addEventListener('open', resolve, {once:true}));
  let id = 0; const pending = new Map(), errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
    if (message.id) { const promise = pending.get(message.id); pending.delete(message.id); message.error ? promise.reject(message.error) : promise.resolve(message.result); }
    if (message.method === 'Page.javascriptDialogOpening') call('Page.handleJavaScriptDialog', {accept: true}, message.sessionId).catch(() => {});
  });
  const call = (method, params = {}, sessionId) => new Promise((resolve, reject) => { const current = ++id; pending.set(current, {resolve,reject}); socket.send(JSON.stringify({id:current,method,params,...(sessionId ? {sessionId} : {})})); });
  const create = async (width, height) => {
    const context = await call('Target.createBrowserContext');
    const target = await call('Target.createTarget', {url:'about:blank',browserContextId:context.browserContextId});
    const {sessionId} = await call('Target.attachToTarget', {targetId:target.targetId,flatten:true});
    const evaluate = async expression => {
      if (/\bawait\b/.test(expression)) expression = `(async()=>{${expression}})()`;
      const response = await call('Runtime.evaluate', {expression,returnByValue:true,awaitPromise:true},sessionId);
      if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
      return response.result.value;
    };
    const wait = async condition => {
      const ready = await evaluate(`new Promise(resolve => {const deadline=Date.now()+30000; const check=()=>{if(${condition})resolve(true);else if(Date.now()>deadline)resolve(false);else setTimeout(check,50)};check()})`);
      assert.equal(ready,true,'Timed out waiting for ' + condition);
    };
    await call('Runtime.enable',{},sessionId); await call('Page.enable',{},sessionId); await call('Network.enable',{},sessionId);
    await call('Network.setCacheDisabled',{cacheDisabled:true},sessionId);
    await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600},sessionId);
    await call('Page.navigate',{url},sessionId);
    await wait(`document.querySelector('#account-button') && typeof sync !== 'undefined' && sync`);
    return {sessionId,context,evaluate,wait};
  };
  const desktop = await create(1440,1100), phone = await create(390,844);
  const username = 'qa_' + Date.now().toString(36), password = crypto.randomBytes(20).toString('hex');
  const login = async (page, signup) => {
    await page.evaluate(`document.querySelector('#account-button').click();${signup ? "document.querySelector('#auth-switch').click();" : ''} document.querySelector('#auth-username').value=${JSON.stringify(username)};document.querySelector('#auth-password').value=${JSON.stringify(password)};document.querySelector('#auth-form').requestSubmit()`);
    await page.wait(`sync.user && !document.querySelector('#auth-dialog').open`);
  };
  const addTopic = async (page, name) => {
    await page.evaluate(`document.querySelector('#bottom-add').click();document.querySelector('#topic-name').value=${JSON.stringify(name)};document.querySelector('#topic-form').requestSubmit();`);
  };
  await login(desktop, true);
  assert.equal(await desktop.evaluate(`state.topics.length`),0);
  await addTopic(desktop,'PC에서 만든 주제');
  await desktop.evaluate(`const form=document.querySelector('.task-form');form.querySelector('input[type=text]').value='휴대폰에서 완료하기';form.requestSubmit()`);
  await desktop.wait(`!sync.dirty && !sync.busy`);
  await login(phone, false);
  assert.equal(await phone.evaluate(`document.querySelector('.topic-title').textContent`),'PC에서 만든 주제');
  assert.equal(await phone.evaluate(`document.querySelector('.todo-label').textContent`),'휴대폰에서 완료하기');
  await phone.evaluate(`document.querySelector('.todo-row input[type=checkbox]').click()`);
  await phone.wait(`!sync.dirty && !sync.busy`); await desktop.evaluate(`sync.refresh()`);
  assert.equal(await desktop.evaluate(`document.querySelector('.todo-row').classList.contains('done')`),true);
  // 두 기기에서 서로 다른 항목을 동시에 추가한다.
  await phone.evaluate(`TaskStore.addTopic(state,'폰의 동시 변경','🎯');sync.change(state);clearTimeout(sync.timer);render()`);
  await desktop.evaluate(`TaskStore.addTopic(state,'PC의 동시 변경','💻');sync.change(state);clearTimeout(sync.timer);await sync.flush();render()`);
  await phone.evaluate(`await sync.flush()`);
  assert.equal(await phone.evaluate(`document.querySelector('#sync-conflict').hidden`),false);
  await phone.evaluate(`document.querySelector('#merge-changes').click()`); await phone.wait(`!sync.dirty && !sync.busy`);
  await desktop.evaluate(`sync.refresh()`);
  assert.equal(await desktop.evaluate(`state.topics.some(t=>t.name==='폰의 동시 변경') && state.topics.some(t=>t.name==='PC의 동시 변경')`),true);
  // 오프라인 변경을 보관한 뒤 재연결하면 다른 기기에서도 확인한다.
  await call('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:-1,uploadThroughput:-1},phone.sessionId);
  await addTopic(phone,'오프라인에서 작성'); await phone.evaluate(`clearTimeout(sync.timer);await sync.flush()`);
  assert.equal(await phone.evaluate(`sync.dirty && JSON.parse(localStorage.getItem(sync.key())).dirty`),true);
  await call('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1},phone.sessionId);
  await phone.evaluate(`sync.refresh()`); await phone.wait(`!sync.dirty && !sync.busy`);
  await desktop.evaluate(`sync.refresh()`); assert.equal(await desktop.evaluate(`state.topics.some(t=>t.name==='오프라인에서 작성')`),true);
  await call('Page.reload',{},phone.sessionId); await phone.wait(`typeof sync !== 'undefined' && sync?.user && !document.querySelector('.content').inert`);
  assert.equal(await phone.evaluate(`state.topics.some(t=>t.name==='오프라인에서 작성')`),true);
  // 가져오기 전후로 게스트 목록이 그대로 유지된다.
  const guest = await desktop.evaluate(`localStorage.getItem(TaskStore.KEY)`);
  await desktop.evaluate(`document.querySelector('#account-button').click();document.querySelector('#import-local').click()`);
  await desktop.wait(`!sync.dirty && !sync.busy && !document.querySelector('#account-dialog').open`);
  assert.equal(await desktop.evaluate(`localStorage.getItem(TaskStore.KEY)`),guest);
  assert.equal(await desktop.evaluate(`state.topics.length`),7);
  await phone.evaluate(`sync.refresh()`);
  for (const [width,height] of [[320,568],[360,800],[375,667],[390,844],[393,852],[412,915],[430,932],[844,390]]) {
    await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:true},phone.sessionId);
    assert.equal(await phone.evaluate(`document.documentElement.scrollWidth <= innerWidth`),true,`overflow at ${width}`);
    await phone.evaluate(`document.querySelector('#account-button').click()`);
    assert.equal(await phone.evaluate(`document.querySelector('#account-dialog').getBoundingClientRect().right <= innerWidth`),true);
    await phone.evaluate(`document.querySelector('#close-account').click()`);
  }
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true},phone.sessionId);
  fs.mkdirSync('artifacts',{recursive:true});
  const shot = await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},phone.sessionId);
  fs.writeFileSync('artifacts/taskflow-sync-mobile.png',Buffer.from(shot.data,'base64'));
  const deskShot = await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},desktop.sessionId);
  fs.writeFileSync('artifacts/taskflow-sync-desktop.png',Buffer.from(deskShot.data,'base64'));
  await desktop.evaluate(`document.querySelector('#account-button').click();document.querySelector('#logout-button').click()`); await desktop.wait(`!sync.user`);
  assert.equal(await desktop.evaluate(`localStorage.getItem(TaskStore.KEY)`),guest);
  assert.equal(await desktop.evaluate(`state.topics.length`),3);
  assert.equal(errors.length,0,JSON.stringify(errors));
  await call('Target.disposeBrowserContext',{browserContextId:desktop.context.browserContextId});
  await call('Target.disposeBrowserContext',{browserContextId:phone.context.browserContextId});
  socket.close();
  console.log('Browser sync QA passed: isolated PC/mobile login, real API persistence, completion, conflict merge, offline retry, reload, guest import and logout, 8 phone sizes, no runtime errors.');
})().catch(error => {console.error(error);process.exit(1);});

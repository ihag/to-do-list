const assert = require('node:assert/strict');
const fs = require('node:fs');
const baseUrl = process.env.TASKFLOW_QA_URL || 'http://127.0.0.1:8080/';
const sizes = [[320,568],[360,800],[375,667],[390,844],[393,852],[412,915],[430,932],[568,320],[844,390],[768,1024],[1440,1100]];
(async () => {
  const tabs = await (await fetch('http://127.0.0.1:9227/json')).json();
  const socket = new WebSocket(tabs[0].webSocketDebuggerUrl);
  await new Promise(resolve => socket.addEventListener('open', resolve, {once:true}));
  let id = 0; const pending = new Map(); const errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
    if (message.id) {const item = pending.get(message.id); pending.delete(message.id); message.error ? item.reject(message.error) : item.resolve(message.result);}
  });
  const call = (method,params={}) => new Promise((resolve,reject) => {const current=++id;pending.set(current,{resolve,reject});socket.send(JSON.stringify({id:current,method,params}));});
  const evaluate = async expression => {
    const result = await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const checkArtwork = async (selector, label) => {
    const results = await evaluate(`(async()=>{const buttons=[...document.querySelectorAll(${JSON.stringify(selector)})];return await Promise.all(buttons.map(async button=>{
      const image=button.querySelector('.emoji-image');if(!image)throw new Error('Missing image');await image.decode();
      const b=button.getBoundingClientRect(),g=image.getBoundingClientRect();const canvas=document.createElement('canvas');canvas.width=canvas.height=160;const context=canvas.getContext('2d');context.drawImage(image,0,0,160,160);
      const pixels=context.getImageData(0,0,160,160).data;let minX=160,minY=160,maxX=-1,maxY=-1;
      for(let y=0;y<160;y++)for(let x=0;x<160;x++)if(pixels[(y*160+x)*4+3]>32){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
      if(maxX<0)throw new Error('Empty artwork');const centerX=g.x+((minX+maxX+1)/2/160)*g.width,centerY=g.y+((minY+maxY+1)/2/160)*g.height;
      return {emoji:button.textContent,dx:Math.abs(centerX-b.x-b.width/2),dy:Math.abs(centerY-b.y-b.height/2),loaded:image.naturalWidth>0};
    }));})()`);
    for (const result of results) assert.ok(result.loaded&&result.dx<0.6&&result.dy<0.6,`${label}: actual artwork off-center ${JSON.stringify(result)}`);
  };
  await call('Page.enable'); await call('Runtime.enable'); await call('Network.enable');
  await call('Network.setCacheDisabled',{cacheDisabled:true});
  await call('Page.navigate',{url:baseUrl});
  await evaluate(`new Promise((resolve,reject)=>{let attempts=0;const check=()=>location.href.startsWith(${JSON.stringify(baseUrl)})&&document.querySelector('.emoji-glyph')?resolve():++attempts>200?reject(new Error('Updated emoji page did not load')):setTimeout(check,50);check();})`);
  await evaluate(`localStorage.clear(); location.reload()`);
  await new Promise(resolve => setTimeout(resolve,300));
  fs.mkdirSync('artifacts',{recursive:true});
  for (const [width,height] of sizes) {
    await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:width<500?3:1,mobile:width<900});
    await evaluate(`state.topics[0].name='모바일에서도 길어진 주제 제목과 이모티콘 정렬 확인';render();window.scrollTo(0,0)`);
    assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true,`${width}x${height}: page overflow`);
    for (const emoji of await evaluate('TaskStore.EMOJIS')) {
      await evaluate(`state.topics[0].emoji=${JSON.stringify(emoji)};render()`);
      const measure = await evaluate(`(()=>{const button=document.querySelector('.topic-icon');const glyph=button.querySelector('.emoji-glyph');const b=button.getBoundingClientRect(),g=glyph.getBoundingClientRect();return {dx:Math.abs(g.x+g.width/2-b.x-b.width/2),dy:Math.abs(g.y+g.height/2-b.y-b.height/2),inside:g.x>=b.x&&g.right<=b.right&&g.y>=b.y&&g.bottom<=b.bottom,padding:getComputedStyle(button).padding};})()`);
      assert.ok(measure.dx < 0.6 && measure.dy < 0.6 && measure.inside,`${width}x${height} ${emoji}: ${JSON.stringify(measure)}`);
      assert.equal(measure.padding,'0px');
      await checkArtwork('.topic-icon',`${width}x${height} ${emoji}`);
    }
    await evaluate(`document.querySelector('.topic-icon').click()`);
    const choices = await evaluate(`Array.from(document.querySelectorAll('.emoji-choice')).map(button=>{const b=button.getBoundingClientRect(),g=button.querySelector('.emoji-glyph').getBoundingClientRect();return {emoji:button.textContent,dx:Math.abs(g.x+g.width/2-b.x-b.width/2),dy:Math.abs(g.y+g.height/2-b.y-b.height/2),inside:g.x>=b.x&&g.right<=b.right&&g.y>=b.y&&g.bottom<=b.bottom};})`);
    for (const measure of choices) assert.ok(measure.dx<0.6&&measure.dy<0.6&&measure.inside,`${width}x${height} picker: ${JSON.stringify(measure)}`);
    await checkArtwork('.emoji-choice',`${width}x${height} picker`);
    assert.equal(await evaluate(`document.querySelector('#topic-dialog').scrollWidth<=document.querySelector('#topic-dialog').clientWidth`),true,`${width}x${height}: dialog overflow`);
    if ([320,390,430].includes(width)) {
      const capture=await call('Page.captureScreenshot',{format:'png'});
      fs.writeFileSync(`artifacts/emoji-picker-${width}.png`,Buffer.from(capture.data,'base64'));
    }
    await evaluate(`document.querySelector('#close-dialog').click()`);
    await evaluate(`document.querySelector('.topic-icon').click();[...document.querySelectorAll('.emoji-choice')].find(button=>button.textContent==='❤️').click();document.querySelector('#topic-form').requestSubmit()`);
    assert.equal(await evaluate(`document.querySelector('.topic-icon').textContent`),'❤️');
  }
  assert.equal(errors.length,0,JSON.stringify(errors));
  await evaluate(`localStorage.clear();location.reload()`);
  socket.close();
  console.log(`Emoji layout passed at ${sizes.map(size=>size.join('x')).join(', ')}: actual rasterized artwork of all 16 emoji centered within 0.6px in topic buttons and picker; long titles, no horizontal overflow, selection works; zero runtime errors. URL: ${baseUrl}`);
})().catch(error=>{console.error(error);process.exit(1);});

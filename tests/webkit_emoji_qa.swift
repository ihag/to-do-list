import AppKit
import WebKit

final class EmojiQA: NSObject, WKNavigationDelegate {
    let sizes = [(320,568),(360,800),(375,667),(390,844),(393,852),(412,915),(430,932),(568,320),(844,390),(721,900),(768,1024),(900,700),(1050,800),(1440,1100),(1920,1080)]
    let web: WKWebView
    let window: NSWindow
    let url: URL
    var index = 0
    var started = false
    init(url: URL) {
        self.url = url
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        web = WKWebView(frame: NSRect(x:0,y:0,width:320,height:568), configuration:configuration)
        window = NSWindow(contentRect:NSRect(x:0,y:0,width:320,height:568),styleMask:[.borderless],backing:.buffered,defer:false)
        super.init()
        window.contentView = web
        web.navigationDelegate = self
        web.customUserAgent = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
    }
    func start() { web.load(URLRequest(url:url, cachePolicy:.reloadIgnoringLocalCacheData)) }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if started { return }
        started = true
        testNext()
    }
    func fail(_ message:String) { print("WebKit QA failed: " + message); exit(1) }
    func testNext() {
        if index == sizes.count { print("WebKit QA passed: all 16 emoji images centered at 15 viewport sizes, including workspace selector, long names, workspace emoji picker and dialog, narrow screens and landscape. URL: " + url.absoluteString); exit(0) }
        let size = sizes[index]
        window.setContentSize(NSSize(width:size.0,height:size.1))
        web.frame = NSRect(x:0,y:0,width:size.0,height:size.1)
        let script = """
        await new Promise(resolve=>setTimeout(resolve,60));
        document.querySelector('#overall-progress').style.transition='none';
        state = TaskStore.initialState();state.topics[0].name='모바일에서 긴 주제 제목과 이모티콘 정렬 확인';render();
        const logo=document.querySelector('.brand-icon'),vector=logo.querySelector('svg'),l=logo.getBoundingClientRect(),v=vector.getBoundingClientRect();if(vector.getAttribute('viewBox')!=='0 0 24 24'||logo.textContent.trim()||Math.abs(v.left+v.width/2-l.left-l.width/2)>.5||Math.abs(v.top+v.height/2-l.top-l.height/2)>.5)throw new Error('Logo vector alignment');
        if(document.documentElement.scrollWidth>innerWidth) throw new Error('Page overflow');
        const box=document.querySelector('.workspace-selector').getBoundingClientRect(),aside=document.querySelector('.sidebar').getBoundingClientRect();if(box.width<=0||box.left<aside.left||box.right>aside.right||document.querySelector('#workspace-select').getBoundingClientRect().width<60)throw new Error('Workspace selector bounds');const before=box.top;const added=TaskStore.addWorkspace(state,'가'.repeat(60),'🎯');selectedWorkspace=added.id;render();if(Math.abs(document.querySelector('.workspace-selector').getBoundingClientRect().top-before)>.5||document.documentElement.scrollWidth>innerWidth)throw new Error('Workspace selector moved');state=TaskStore.initialState();selectedWorkspace='default';render();
        {(()=>{const bar=document.querySelector('.stats'),cells=[...bar.children],labels=cells.map(c=>c.firstElementChild.getBoundingClientRect()),values=cells.map(c=>c.querySelector('strong').getBoundingClientRect());if(document.querySelector('.stat-symbol'))throw new Error('Stat icon remains');if(bar.getBoundingClientRect().height>86||getComputedStyle(bar).columnGap!=='0px')throw new Error('Summary bar size');for(const group of [labels,values]){const center=group[0].top+group[0].height/2;if(group.some(r=>Math.abs(r.top+r.height/2-center)>.5))throw new Error('Summary text centers');}return true})();}
        const cards=[...document.querySelectorAll('.stats>div')].map(card=>card.getBoundingClientRect());
        if(cards.length!==4||cards.some(card=>Math.abs(card.top-cards[0].top)>1))throw new Error('Stats must stay in one row');
        if(parseFloat(getComputedStyle(document.querySelector('#today')).fontSize)<20)throw new Error('Date too small');
        const track=document.querySelector('.progress-track'),fill=document.querySelector('#overall-progress');
        if(track.getAttribute('aria-valuenow')!=='20'||Math.abs(fill.getBoundingClientRect().width/track.getBoundingClientRect().width-.2)>.02)throw new Error('Progress mismatch');
        if(document.querySelector('footer,.topbar,.list-heading')||document.querySelector('#workspace-edit').textContent.trim())throw new Error('Removed copy remains');const add=document.querySelector('#bottom-add'),a=add.getBoundingClientRect();if(a.width!==48||a.height!==48||getComputedStyle(add).borderRadius!=='50%'||!add.querySelector('svg'))throw new Error('Topic add circle');for(const form of document.querySelectorAll('.topic[open] .task-form')){const rects=[...form.children].map(e=>e.getBoundingClientRect()),middle=rects[1].top+rects[1].height/2;if(rects.some(r=>Math.abs(r.top+r.height/2-middle)>1)||form.scrollWidth>form.clientWidth||!form.querySelector('.calendar-control svg')||getComputedStyle(form.querySelector('input[type=date]')).opacity!=='0')throw new Error('Task input row');const plus=form.querySelector('.task-add-icon svg').getBoundingClientRect(),field=form.querySelector('input[type=text]').getBoundingClientRect();if(Math.abs(plus.top+plus.height/2-field.top-field.height/2)>.5)throw new Error('Task plus center');}if(Number(getComputedStyle(document.querySelector('.brand')).fontWeight)<700||getComputedStyle(document.querySelector('.brand')).fontFamily.indexOf('Arial')<0)throw new Error('Brand weight');
        for(const message of ['이 브라우저에 저장됨','모든 기기에 동기화됨','서버 미저장 · 이 기기에 보관됨']){
          document.querySelector('#save-status').textContent=message;
          document.querySelector('#sync-now').hidden=message==='이 브라우저에 저장됨';
          document.querySelector('#account-button').textContent=message==='이 브라우저에 저장됨'?'로그인':'나의 계정';
          const header=document.querySelector('.app-header'),tools=document.querySelector('.account-tools'),status=document.querySelector('#save-status');
          const h=header.getBoundingClientRect(),t=tools.getBoundingClientRect(),s=status.getBoundingClientRect(),b=document.querySelector('.brand').getBoundingClientRect(),group=document.querySelector('.account-area').getBoundingClientRect(),edge=h.right-parseFloat(getComputedStyle(header).paddingRight);
          if(!(Math.abs(t.right-edge)<1&&Math.abs((group.top+group.height/2)-(b.top+b.height/2))<1&&b.right<t.left&&Math.abs(s.right-edge)<1&&s.bottom<=t.top&&h.height===(innerWidth>720?77:85)&&document.documentElement.scrollWidth<=innerWidth))throw new Error('Status alignment: '+message);
        }
        async function measure(button){
          const image=button.querySelector('.emoji-image');if(!image)throw new Error('No image');await image.decode();
          const b=button.getBoundingClientRect(),g=image.getBoundingClientRect();
          const c=document.createElement('canvas');c.width=c.height=160;const ctx=c.getContext('2d');ctx.drawImage(image,0,0,160,160);
          const pixels=ctx.getImageData(0,0,160,160).data;let minX=160,minY=160,maxX=-1,maxY=-1;
          for(let y=0;y<160;y++)for(let x=0;x<160;x++)if(pixels[(y*160+x)*4+3]>32){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
          const dx=Math.abs(g.x+((minX+maxX+1)/2/160)*g.width-b.x-b.width/2),dy=Math.abs(g.y+((minY+maxY+1)/2/160)*g.height-b.y-b.height/2);
          if(maxX<0||dx>.6||dy>.6)throw new Error('Artwork offset '+button.textContent+' '+JSON.stringify({dx,dy,button:[b.x,b.y,b.width,b.height],image:[g.x,g.y,g.width,g.height],bounds:[minX,minY,maxX,maxY]}));
        }
        for(const emoji of TaskStore.EMOJIS){state.topics[0].emoji=emoji;render();await measure(document.querySelector('.topic-icon'));}
        document.querySelector('.edit-topic').click();
        for(const button of document.querySelectorAll('.emoji-choice'))await measure(button);
        const dialog=document.querySelector('#topic-dialog');if(dialog.scrollWidth>dialog.clientWidth)throw new Error('Dialog overflow');
        document.querySelector('#close-dialog').click();
        await measure(document.querySelector('#workspace-emoji'));
        document.querySelector('#workspace-edit').click();
        for(const button of document.querySelectorAll('#workspace-emoji-picker .emoji-choice'))await measure(button);
        const workspaceDialog=document.querySelector('#workspace-dialog'),bounds=workspaceDialog.getBoundingClientRect();
        if(workspaceDialog.scrollWidth>workspaceDialog.clientWidth||bounds.left<0||bounds.right>innerWidth||bounds.height>innerHeight)throw new Error('Workspace dialog overflow');
        document.querySelector('#workspace-close').click();
        if(document.querySelector('#all-topics,#nav-count')||document.querySelector('#workspace-dialog p'))throw new Error('Removed workspace copy');for(const editing of [true,false]){openWorkspaceDialog(editing?currentWorkspace():null);for(const name of ['나의 할 일','가'.repeat(60)]){document.querySelector('#workspace-name').value=name;const d=document.querySelector('#workspace-dialog'),buttons=[document.querySelector('#workspace-delete'),document.querySelector('#workspace-cancel'),d.querySelector('button[type=submit]')].filter(e=>!e.hidden).map(e=>e.getBoundingClientRect()),center=buttons[0].top+buttons[0].height/2;if(buttons.some(r=>Math.abs(r.top+r.height/2-center)>.5)||d.scrollWidth>d.clientWidth)throw new Error('Workspace actions not centered');}document.querySelector('#workspace-close').click();}
        {const other=TaskStore.addWorkspace(state,'하늘색 공간','🌿');TaskStore.addWorkspace(state,'가'.repeat(60),'💼');render();document.querySelector('#workspace-select').click();const menu=document.querySelector('#workspace-menu'),bounds=menu.getBoundingClientRect();if(menu.hidden||bounds.left<0||bounds.right>innerWidth||bounds.top<0||bounds.bottom>innerHeight||menu.scrollWidth>menu.clientWidth||menu.querySelectorAll('[role=option]').length!==3||!menu.querySelector('[aria-selected=true] .workspace-option-check'))throw new Error('Workspace menu layout');menu.dispatchEvent(new KeyboardEvent('keydown',{key:'End',bubbles:true}));if(document.activeElement!==menu.lastElementChild)throw new Error('Workspace menu keyboard');menu.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));if(!menu.hidden||document.activeElement!==document.querySelector('#workspace-select'))throw new Error('Workspace menu escape');document.querySelector('#workspace-select').click();menu.querySelectorAll('[role=option]')[1].click();if(currentWorkspace().id!==other.id||workspaceTopics().length!==0||!menu.hidden)throw new Error('Workspace menu selection');document.querySelector('#workspace-select').click();document.body.dispatchEvent(new Event('pointerdown',{bubbles:true}));if(!menu.hidden)throw new Error('Workspace menu outside close');state=TaskStore.initialState();selectedWorkspace='default';render();}
        {if(document.querySelector('.topic-empty,.delete-topic')||document.querySelector('.topic summary>.chevron'))throw new Error('Old topic controls');for(const card of document.querySelectorAll('.topic')){const icon=card.querySelector('.topic-icon').getBoundingClientRect(),arrow=card.querySelector('.topic-actions .chevron').getBoundingClientRect(),edit=card.querySelector('.edit-topic').getBoundingClientRect(),mid=icon.top+icon.height/2;if(Math.abs(arrow.top+arrow.height/2-mid)>.5||Math.abs(edit.top+edit.height/2-mid)>.5||arrow.left<icon.right)throw new Error('Topic header centers');}document.querySelector('.topic-icon').click();if(document.querySelector('#topic-dialog').open)throw new Error('Icon opened editor');for(const editing of [true,false]){openTopicDialog(editing?workspaceTopics()[0]:null);const d=document.querySelector('#topic-dialog'),buttons=[document.querySelector('#topic-delete'),document.querySelector('#cancel-dialog'),d.querySelector('button[type=submit]')].filter(e=>!e.hidden).map(e=>e.getBoundingClientRect()),mid=buttons[0].top+buttons[0].height/2;if(buttons.some(r=>Math.abs(r.top+r.height/2-mid)>.5)||d.scrollWidth>d.clientWidth)throw new Error('Topic editor buttons');document.querySelector('#close-dialog').click();}window.scrollTo(0,300);if(Math.abs(document.querySelector('.app-header').getBoundingClientRect().top)>.5||(innerWidth>720&&Math.abs(document.querySelector('.sidebar').getBoundingClientRect().top-document.querySelector('.app-header').getBoundingClientRect().bottom)>.5))throw new Error('Header sidebar scroll gap');window.scrollTo(0,0);state=TaskStore.initialState();selectedWorkspace='default';render();}
        {document.querySelector('.topic .todo-edit').click();const editInput=document.querySelector('.todo-edit-input'),editStyle=getComputedStyle(editInput);if(editStyle.outlineStyle!=='none'||editStyle.borderTopStyle!=='solid'||editStyle.borderTopColor!=='rgb(40, 120, 239)'||editStyle.boxShadow!=='none')throw new Error('Edit input border');editInput.blur();editInput.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));window.scrollTo(0,0);await new Promise(resolve=>setTimeout(resolve,30));}
        {const base=JSON.parse(JSON.stringify(state));const space=currentWorkspace();space.topics[0].todos.push(...Array.from({length:8},(_,i)=>({id:crypto.randomUUID(),title:'긴 주제의 할 일 '+i,done:false,due:''})));space.topics[1].open=false;TaskStore.addTopic(space,'다음 주제');TaskStore.addTopic(space,'다음 주제 2');render();layoutTopics();const cards=[...document.querySelectorAll('.topic')].map(e=>e.getBoundingClientRect()),columns=getComputedStyle(document.querySelector('#topics')).gridTemplateColumns.split(' ').length;for(const left of new Set(cards.map(c=>Math.round(c.left)))){const stack=cards.filter(c=>Math.round(c.left)===left).sort((a,b)=>a.top-b.top);for(let i=1;i<stack.length;i++){const gap=stack[i].top-stack[i-1].bottom;if(gap<17.5||gap>19.5)throw new Error('Topic masonry gap '+gap);}}if(columns===2&&Math.abs(cards[2].left-cards[1].left)>1)throw new Error('Next topic must fill shorter column');space.topics[0].open=false;render();layoutTopics();if(document.documentElement.scrollWidth>innerWidth)throw new Error('Masonry overflow');state=base;render();}
        {const checkbox=document.querySelector('.todo-row input[type=checkbox]');for(const checked of [true,false]){checkbox.checked=checked;const style=getComputedStyle(checkbox),r=checkbox.getBoundingClientRect();if(style.appearance!=='none'||style.backgroundPosition!=='50% 50%'||r.width!==r.height||(checked?!style.backgroundImage.includes('svg+xml'):style.backgroundImage!=='none')||getComputedStyle(checkbox,'::after').content!=='none')throw new Error('Checkbox vector rendering');}render();}
        return {width:innerWidth,height:innerHeight,count:TaskStore.EMOJIS.length};
        """
        web.callAsyncJavaScript(script,arguments:[:],in:nil,in:.page) { result in
            switch result {
            case .success(let value):
                print("WebKit " + String(size.0) + "x" + String(size.1) + " passed: " + String(describing:value))
                self.index += 1
                self.testNext()
            case .failure(let error): self.fail(String(size.0) + "x" + String(size.1) + ": " + String(describing:(error as NSError).userInfo))
            }
        }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error:Error) {fail(error.localizedDescription)}
}

let app = NSApplication.shared
app.setActivationPolicy(.prohibited)
let runner = EmojiQA(url:URL(string:CommandLine.arguments.count>1 ? CommandLine.arguments[1] : "http://127.0.0.1:8080/")!)
runner.start()
DispatchQueue.main.asyncAfter(deadline:.now()+55){print("WebKit QA timeout");exit(1)}
app.run()

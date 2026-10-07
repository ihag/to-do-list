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
        if index == sizes.count { print("WebKit QA passed: all 16 emoji images centered at 15 viewport sizes, including narrow screens and landscape. URL: " + url.absoluteString); exit(0) }
        let size = sizes[index]
        window.setContentSize(NSSize(width:size.0,height:size.1))
        web.frame = NSRect(x:0,y:0,width:size.0,height:size.1)
        let script = """
        await new Promise(resolve=>setTimeout(resolve,60));
        document.querySelector('#overall-progress').style.transition='none';
        state = TaskStore.initialState();state.topics[0].name='모바일에서 긴 주제 제목과 이모티콘 정렬 확인';render();
        if(document.documentElement.scrollWidth>innerWidth) throw new Error('Page overflow');
        const cards=[...document.querySelectorAll('.stats>div')].map(card=>card.getBoundingClientRect());
        if(cards.length!==4||cards.some(card=>Math.abs(card.top-cards[0].top)>1))throw new Error('Stats must stay in one row');
        if(parseFloat(getComputedStyle(document.querySelector('#today')).fontSize)<20)throw new Error('Date too small');
        const track=document.querySelector('.progress-track'),fill=document.querySelector('#overall-progress');
        if(track.getAttribute('aria-valuenow')!=='20'||Math.abs(fill.getBoundingClientRect().width/track.getBoundingClientRect().width-.2)>.02)throw new Error('Progress mismatch');
        for(const message of ['이 브라우저에 저장됨','모든 기기에 동기화됨','서버 미저장 · 이 기기에 보관됨']){
          document.querySelector('#save-status').textContent=message;
          document.querySelector('#sync-now').hidden=message==='이 브라우저에 저장됨';
          document.querySelector('#account-button').textContent=message==='이 브라우저에 저장됨'?'로그인':'나의 계정';
          const header=document.querySelector('.topbar'),tools=document.querySelector('.account-tools'),status=document.querySelector('#save-status');
          const h=header.getBoundingClientRect(),t=tools.getBoundingClientRect(),s=status.getBoundingClientRect(),b=document.querySelector('.workspace-path').getBoundingClientRect(),edge=h.right-parseFloat(getComputedStyle(header).paddingRight);
          if(Math.abs(t.right-edge)>1||Math.abs(s.top-b.top)>1||b.right>s.left+1||(innerWidth>1050?s.right>t.left:Math.abs(s.right-edge)>1||t.top<s.bottom)||document.documentElement.scrollWidth>innerWidth)throw new Error('Status alignment: '+message);
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
        document.querySelector('.topic-icon').click();
        for(const button of document.querySelectorAll('.emoji-choice'))await measure(button);
        const dialog=document.querySelector('#topic-dialog');if(dialog.scrollWidth>dialog.clientWidth)throw new Error('Dialog overflow');
        document.querySelector('#close-dialog').click();
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

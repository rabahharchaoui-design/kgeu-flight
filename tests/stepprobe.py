# Stepstall 1: the step probe. A page side recorder for what a step change costs: a lesson's step card (#lesI's text),
# a tasking's stage (TASK.si), a mission pill's step (its 1/4, WAVE 2/4, AIRDROP...), a voice line going on the air
# (RADIO.log). Loaded by tests/harness.py when PFS_STEPPROBE names an output file (every check that flies a lesson, a
# tasking or a mission then feeds it, unchanged), and by tests/stepstall_check.py.
#
# Two paths, because the checks drive the game both ways:
#  - held frames (__kgeu.stepFrame): the wrapper times each call (the frame's CPU work, the render when it renders) and
#    compares the state before and after. On a change it then times a forced style and layout (what the browser must do
#    for the DOM the step changed before it can paint) and makes the next held frame render (the meshes, materials and
#    shaders a step adds show there), and records the counters below for that frame. Every 50th quiet frame gets the
#    same treatment as a control, so a step frame is judged against the same kind of frame.
#  - real frames (the rAF loop): a rAF hook registered before the game's runs first in each frame, so the change made by
#    frame k is seen at the start of frame k+1 and the gap k to k+1 is that frame's whole cost (tick, render, style,
#    layout, paint); the two gaps after it are kept too (work pushed to the next frame is still a hitch).
# Counters (reset each frame): localStorage writes (keys), fetch and sendBeacon calls, speechSynthesis speak, cancel and
# getVoices (with their ms), Web Audio nodes and buffers created, layout reads (getBoundingClientRect, offset*/client*/
# scroll* getters, getComputedStyle), shader programs linked (__kgeu.progN().compiles), textures and geometries uploaded.
# Schoolhud: any read of window.speechSynthesis at all (SP.ssr, in every record as ssr: the game must never touch it); at a
# held step, right after the step's frame, whether the new instruction is already readable (vis: the lesson card's
# instruction or the pill's text in the DOM, on screen, at least half opaque) and, on the frame after it, what the top caption and the bottom task
# card overlap (lap: each other, the controls, the readouts, the map).
# Records go to the console as '[stepprobe] {json}' (the harness writes them to the file).
PROBE = r"""(()=>{if(window.__sp)return;
const SP=window.__sp={ev:[],ctl:[],last:null,n:0,frames:0,pend:null,ctlN:0,raf:{prev:0,gaps:[],open:[]}};
const now=()=>performance.now();
const C=SP.C={ls:0,lsMs:0,lsKeys:[],fetch:0,beacon:0,speak:0,cancel:0,voices:0,spMs:0,an:0,bcr:0,lay:0,F:{}};
// a call made while the game's frame runs its tick (__kgeu.inFrame) is also counted in C.F: in the frame, not after it
const inF=()=>{const K=window.__kgeu;return !!(K&&K.inFrame&&K.inFrame());};
const cnt=k=>{C[k]++;if(inF())C.F[k]=(C.F[k]||0)+1;};
function cReset(){C.F={};C.ls=0;C.lsMs=0;C.lsKeys=[];C.fetch=0;C.beacon=0;C.speak=0;C.cancel=0;C.voices=0;C.spMs=0;C.an=0;C.bcr=0;C.lay=0;}
function cCopy(){return {F:Object.assign({},C.F),ls:C.ls,lsMs:+C.lsMs.toFixed(2),lsKeys:C.lsKeys.slice(),fetch:C.fetch,beacon:C.beacon,speak:C.speak,cancel:C.cancel,voices:C.voices,spMs:+C.spMs.toFixed(2),an:C.an,bcr:C.bcr,lay:C.lay};}
const W=(o,k,f)=>{try{const g=o&&o[k];if(typeof g!=='function')return;o[k]=function(){return f.call(this,g,arguments);};}catch(e){}};
W(Storage.prototype,'setItem',function(g,a){const t=now();try{return g.apply(this,a);}finally{cnt('ls');C.lsMs+=now()-t;if(C.lsKeys.length<8)C.lsKeys.push(String(a[0]));if(inF())(C.F.keys=C.F.keys||[]).push(String(a[0]));}});
W(window,'fetch',function(g,a){cnt('fetch');return g.apply(this,a);});
if(navigator.sendBeacon)W(navigator,'sendBeacon',function(g,a){cnt('beacon');return g.apply(this,a);});
const SS=window.speechSynthesis;SP.ssr=0;
try{Object.defineProperty(window,'speechSynthesis',{configurable:true,get(){SP.ssr++;return SS;}});}catch(e){}
if(SS){for(const k of ['speak','cancel','getVoices']){const g=SS[k];if(typeof g!=='function')continue;
  SS[k]=function(){const t=now();try{return g.apply(SS,arguments);}finally{cnt(k==='getVoices'?'voices':k);C.spMs+=now()-t;}};}}
const AC=window.BaseAudioContext||window.AudioContext||window.webkitAudioContext;
if(AC)for(const k of ['createBufferSource','createGain','createOscillator','createBuffer','createBiquadFilter','createDynamicsCompressor','createConvolver','createStereoPanner','createPanner','decodeAudioData'])
  W(AC.prototype,k,function(g,a){C.an++;return g.apply(this,a);});
const LAYG={};
W(Element.prototype,'getBoundingClientRect',function(g,a){C.bcr++;return g.apply(this,a);});
W(window,'getComputedStyle',function(g,a){C.lay++;return g.apply(this,a);});
for(const [P,ks] of [[HTMLElement.prototype,['offsetWidth','offsetHeight','offsetTop','offsetLeft']],[Element.prototype,['clientWidth','clientHeight','scrollHeight','scrollWidth','scrollTop']]])
  for(const k of ks){const d=Object.getOwnPropertyDescriptor(P,k);if(!d||!d.get)continue;LAYG[k]=d.get;
    Object.defineProperty(P,k,{configurable:true,enumerable:d.enumerable,get(){C.lay++;return d.get.call(this);},set:d.set});}
// a forced style and layout, timed, not counted
function layMs(){const t=now();LAYG.offsetHeight.call(document.body);return +(now()-t).toFixed(2);}
const pill=/^(\d+\/\d+|[A-Z]{2,}(?: [A-Z]{2,})*(?: \d+\/\d+)?)/;
function snap(K){const li=document.getElementById('lesI'),mt=document.getElementById('missT'),me=document.getElementById('miss'),L=K.RADIO&&K.RADIO.log;
  const T=K.TASK||{},mo=!!(me&&me.classList.contains('on')),m=mo&&mt?((pill.exec(mt.textContent)||[''])[0]):'';
  const LS=K.LES||{},ph=LS.on?String(LS.ph)+'|'+(LS.d&&LS.d.s!=null?LS.d.s:''):'';
  return {ph:ph,les:(K.LES&&K.LES.on)||'',i:li&&K.LES&&K.LES.on?li.textContent:'',task:T.on?T.id:'',si:T.on?T.si:-1,m:m,mt:mo&&mt?mt.textContent:'',
    v:L&&L.length?L[L.length-1]:null,vt:L&&L.length?(L[L.length-1].who+': '+L[L.length-1].text).slice(0,90):'',
    ride:!!(K.RIDE&&K.RIDE.on),cr:!!(K.state&&K.state().crashed)};}
function diff(a,b){const k=[];if(!a)return k;
  // a lesson's step: its phase moving on (the frame that does the work: Dana's line, the tower's) or the card's text
  if(a.les!==b.les)k.push(b.les?'lesson start':'lesson end');else if((a.i!==b.i||a.ph!==b.ph)&&b.les)k.push('step');
  if(a.task!==b.task)k.push(b.task?'task start':'task end');else if(a.si!==b.si&&b.task)k.push('stage');
  if(a.m!==b.m&&b.m&&a.m)k.push('mstep');else if(a.m!==b.m)k.push(b.m?'pill on':'pill off');
  if(a.v!==b.v&&b.v)k.push('voice');return k;}
function gpu(K){let c=0,t=0,g=0;try{c=K.progN().compiles;const b=K.boot();t=b.texN;g=b.geoN;}catch(e){}return [c,t,g];}
function label(s,kinds){return {kinds:kinds,les:s.les,i:s.i.slice(0,80),task:s.task,si:s.si,m:s.mt.slice(0,60),v:kinds.indexOf('voice')>=0?s.vt:''};}
// schoolhud: the step's instruction readable from its frame, and the caption and the card clear of everything
const opq=e=>{let o=1;for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden')return 0;o*=parseFloat(s.opacity);}return o;};
function visOf(s){const K=window.__kgeu,want=s.les&&s.i?'les':s.m?'miss':'';if(!want)return null;
  const mp=document.getElementById('miss'),e=want==='les'?document.getElementById('lesI'):mp.classList.contains('call')?document.querySelector('#jumpLt b'):document.getElementById('missT'),r=e.getBoundingClientRect();   // a jump call (GREEN LIGHT) stands in the pill's text while it is on
  return {k:want,ok:r.width>0&&r.height>0&&opq(e)>=0.5&&r.bottom>0&&r.top<innerHeight&&(want==='les'?e.textContent===s.i:!!e.textContent),op:+opq(e).toFixed(2)};}
function lapOf(){const q=s=>[...document.querySelectorAll(s)].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&opq(e)>0.05;});
  const A=q('#atc.on, #dfSub.on span, #lesson.on, #cap > #miss.on, #topCol > #miss.on'),C=q('#dock button, #dfW button, #thr, #stickHint, #map, #hud .card, #bPause, #lookPad, #tcas.on, #hDest:not([hidden]), #navLog, #tkReply.on button, #divCard.on');
  const out=[];const nm=e=>e.id||(e.parentElement&&e.parentElement.id)||e.tagName;
  for(let i=0;i<A.length;i++){const a=A[i].getBoundingClientRect();
    for(const b of A.slice(i+1).concat(C)){if(A[i].contains(b)||b.contains(A[i]))continue;const c=b.getBoundingClientRect();
      if(a.left<c.right-0.5&&c.left<a.right-0.5&&a.top<c.bottom-0.5&&c.top<a.bottom-0.5)out.push(nm(A[i])+' x '+nm(b));}}
  return out;}
SP.visOf=visOf;SP.lapOf=lapOf;   // part C asks for them directly
function emit(r){r.ssr=SP.ssr;SP.ev.push(r);try{console.log('[stepprobe] '+JSON.stringify(r));}catch(e){}}
function hook(){const K=window.__kgeu;if(!K||!K.stepFrame||K.__spWrapped)return false;K.__spWrapped=true;
  const sf=K.stepFrame;
  K.stepFrame=function(dt,release,skip){
    if(release){SP.last=snap(K);return sf.apply(this,arguments);}
    const P=SP.pend;let force=false;if(P){force=true;skip=false;}
    const s0=SP.last||snap(K),g0=gpu(K);cReset();const t0=now();
    const r=sf.call(this,dt,release,skip);
    const ms=+(now()-t0).toFixed(2),cc=cCopy(),g1=gpu(K),s1=snap(K);SP.last=s1;SP.frames++;
    if(P){SP.pend=null;P.render={ms:ms,prog:g1[0]-g0[0],tex:g1[1]-g0[1],geo:g1[2]-g0[2],c:cc};
      if(P.lapNext){delete P.lapNext;try{P.lap=lapOf();}catch(x){}}   // the overlaps on the frame after the step (the step's own lays nothing out)
      if(P.ctl)SP.ctl.push(P);emit(P);}
    const kinds=diff(s0,s1);
    if(kinds.length&&!force){const e=Object.assign({path:'held',t:+now().toFixed(0),ms:ms,skip:!!skip,prog:g1[0]-g0[0],tex:g1[1]-g0[1],geo:g1[2]-g0[2],c:cc,lay:layMs()},label(s1,kinds));
      if(kinds.some(k=>k==='step'||k==='stage'||k==='mstep')){try{e.vis=visOf(s1);e.lapNext=1;}catch(x){e.vis={err:String(x)};}}
      if(s1.les||s1.task||s1.m||kinds.some(k=>/end|off/.test(k)))SP.pend=e;else emit(e);}
    else if(!force&&(s1.les||s1.task||s1.m)&&++SP.ctlN%50===0){SP.pend={ctl:1,path:'held',ms:ms,skip:!!skip,c:cc,lay:layMs()};}
    return r;};
  // real frames
  const R=SP.raf;let gp=null;
  function rf(t){requestAnimationFrame(rf);const K=window.__kgeu;const g=R.prev?t-R.prev:0;R.prev=t;
    if(SP.pin)try{SP.pin(K);}catch(e){}
    // c: the frame's tick (the calls made while it ran); ca: the rest since the last frame (after-frame tasks, timers)
    const s1=snap(K),g1=gpu(K),tot=cCopy(),cc={},ca={};
    // a build without the marker (before stepstall) runs all of these in its tick: counted in the frame
    const mk=!!(K&&K.inFrame);
    for(const k of ['ls','fetch','beacon','speak','cancel','voices']){cc[k]=mk?tot.F[k]||0:tot[k];ca[k]=tot[k]-cc[k];}
    for(const k of ['an','bcr','lay','spMs','lsMs'])cc[k]=tot[k];cc.lsKeys=mk?tot.F.keys||[]:tot.lsKeys;
    cReset();
    for(let i=R.open.length-1;i>=0;i--){const o=R.open[i];o.after.push(+g.toFixed(1));if(o.after.length>=2){R.open.splice(i,1);emit(o);}}
    const s0=SP.last;SP.last=s1;
    const fly=!!(K.running&&K.running()&&!(K.paused&&K.paused()));
    if(fly&&g>0){R.gaps.push(g);if(R.gaps.length>4000)R.gaps.shift();if(R.gaps.length%100===0)emit({rafgaps:R.gaps.slice(-100).map(x=>+x.toFixed(1))});}
    const kinds=s0?diff(s0,s1):[];
    if(kinds.length&&fly&&g>0){const st=K.stalls?K.stalls():null,lg=st&&st.log.length?st.log[st.log.length-1]:null;
      R.open.push(Object.assign({path:'raf',t:+t.toFixed(0),gap:+g.toFixed(1),after:[],prog:gp?g1[0]-gp[0]:0,tex:gp?g1[1]-gp[1]:0,geo:gp?g1[2]-gp[2]:0,c:cc,ca:ca,
        stall:lg&&Math.abs(lg.t*1000-t)<1500?lg:null},label(s1,kinds)));}
    gp=g1;}
  requestAnimationFrame(rf);
  return true;}
const iv=setInterval(()=>{if(hook())clearInterval(iv);},20);
SP.summary=()=>{const q=a=>{const s=a.slice().sort((x,y)=>x-y);return s.length?s[s.length>>1]:0;};
  return {ssr:SP.ssr,frames:SP.frames,events:SP.ev.length,ctl:SP.ctl.length,ctlMs:q(SP.ctl.map(c=>c.ms)),ctlRender:q(SP.ctl.filter(c=>c.render).map(c=>c.render.ms)),
    ctlLay:q(SP.ctl.map(c=>c.lay)),rafMedian:q(SP.raf.gaps),rafN:SP.raf.gaps.length};};
})()"""

# the summary at the end of a page (its controls), printed the same way
SUMMARY = "()=>{const s=window.__sp&&window.__sp.summary();if(s)console.log('[stepprobe] '+JSON.stringify(Object.assign({summary:1},s)));return s}"

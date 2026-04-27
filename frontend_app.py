# frontend_app.py  —  Lindstorm Warehouse Web UI  (port 5000)

import os, secrets, requests
from functools import wraps
from flask import (Flask, render_template_string, request,
                   redirect, url_for, session, abort, jsonify)

API  = os.environ.get("API_BASE_URL", "http://127.0.0.1:5001")
ML   = os.environ.get("ML_BASE_URL",  "http://127.0.0.1:5002")
PORT = int(os.environ.get("FRONTEND_PORT", 5000))

app = Flask(__name__)
app.secret_key = os.environ.get("FRONTEND_SECRET", "lindstorm-warehouse-secret-2026-xK9mP")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours

# ── csrf ─────────────────────────────────────────────────────
def mk_csrf():
    t = secrets.token_hex(16); session["csrf"] = t; return t

def ok_csrf():
    s = request.form.get("csrf_token",""); r = session.get("csrf","")
    return bool(s and r and secrets.compare_digest(s, r))

# ── guards ────────────────────────────────────────────────────
def login_req(fn):
    @wraps(fn)
    def w(*a,**k):
        if "user" not in session: return redirect(url_for("login_page"))
        return fn(*a,**k)
    return w

def sup_only(fn):
    @wraps(fn)
    def w(*a,**k):
        if session.get("user",{}).get("role") != "supervisor": abort(403)
        return fn(*a,**k)
    return w

# ── api helpers ───────────────────────────────────────────────
def hdrs():
    t = session.get("api_token")
    return {"Authorization":f"Bearer {t}"} if t else {}

def aget(p):   return requests.get(f"{API}{p}",  headers=hdrs(), timeout=10)
def apost(p,d=None): return requests.post(f"{API}{p}",json=d or {},headers=hdrs(),timeout=10)
def adel(p):   return requests.delete(f"{API}{p}",headers=hdrs(),timeout=10)
def mlget(p):
    try: return requests.get(f"{ML}{p}", timeout=5)
    except: return None
def pj(r):
    try: return r.json()
    except: return {}

# ── CSS ──────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--red:#C8102E;--rd:#9B0B22;--wh:#fff;--off:#F8F8F8;--g1:#F2F2F2;--g2:#E0E0E0;--g4:#9E9E9E;--g6:#555;--g9:#111;--green:#16A34A;--glt:#D1FAE5;--amber:#D97706;--alt:#FEF3C7;--blue:#1D4ED8;--blt:#EFF6FF;--r:10px;--rl:16px}
body{font-family:'Barlow',sans-serif;background:var(--off);color:var(--g9);min-height:100vh}
.nav{background:var(--red);color:#fff;padding:0 20px;height:56px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(200,16,46,.35);position:sticky;top:0;z-index:100}
.nb{display:flex;align-items:center;gap:10px;text-decoration:none;color:#fff}
.nlogo{width:34px;height:34px;background:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center}
.nlogo svg{width:20px;height:20px;fill:var(--red)}
.ntit{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:800}
.nsub{font-size:10px;opacity:.75;text-transform:uppercase;letter-spacing:.05em}
.nr{display:flex;align-items:center;gap:8px}
.pill{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:3px 11px;font-size:12px}
.nbtn{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:5px 12px;border-radius:6px;font-size:12px;cursor:pointer;font-family:'Barlow',sans-serif;text-decoration:none;display:inline-block}
.tabs{background:var(--rd);display:flex;padding:0 20px}
.tab{color:rgba(255,255,255,.65);padding:9px 16px;font-size:13px;font-weight:600;text-decoration:none;border-bottom:3px solid transparent}
.tab:hover,.tab.on{color:#fff}.tab.on{border-bottom-color:#fff}
.tab.mlt{background:rgba(255,255,255,.08)}
.page{max-width:1180px;margin:0 auto;padding:20px 14px 48px}
.card{background:#fff;border-radius:var(--rl);box-shadow:0 4px 16px rgba(0,0,0,.09);padding:22px;border:1px solid var(--g2)}
.ch{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;padding-bottom:12px;border-bottom:2px solid var(--g1)}
.ct{font-family:'Barlow Condensed',sans-serif;font-size:17px;font-weight:700;display:flex;align-items:center;gap:8px}
.ico{width:26px;height:26px;background:var(--red);border-radius:6px;display:inline-flex;align-items:center;justify-content:center;font-size:13px}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 16px;border:none;border-radius:var(--r);font-family:'Barlow',sans-serif;font-size:14px;font-weight:600;cursor:pointer;width:100%;margin-top:8px}
.br{background:var(--red);color:#fff}.br:hover{background:var(--rd)}
.bg{background:var(--green);color:#fff}
.bo{background:transparent;border:2px solid var(--red);color:var(--red)}.bo:hover{background:var(--red);color:#fff}
.bsm{padding:6px 10px;font-size:12px;width:auto;margin-top:0}
.fg{margin-top:12px}
.fl{display:block;font-size:12px;font-weight:600;color:var(--g6);margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em}
.fi{width:100%;padding:10px 12px;font-size:15px;font-family:'Barlow',sans-serif;border:2px solid var(--g2);border-radius:var(--r);background:#fff}
.fi:focus{outline:none;border-color:var(--red)}
.chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase}
.cpend{background:var(--alt);color:var(--amber)}.cdone{background:var(--glt);color:var(--green)}.cact{background:var(--blt);color:var(--blue)}.cwrong{background:#FEE2E2;color:#DC2626}
.flash{padding:11px 14px;border-radius:var(--r);margin-bottom:14px;font-weight:500;font-size:14px}
.fs{background:var(--glt);color:var(--green);border-left:4px solid var(--green)}
.fe{background:#FEE2E2;color:#DC2626;border-left:4px solid #DC2626}
.fi2{background:var(--blt);color:var(--blue);border-left:4px solid var(--blue)}
.g2c{display:grid;grid-template-columns:1.15fr 1fr;gap:18px}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}
.sb{background:#fff;border-radius:var(--r);padding:14px;text-align:center;border:1px solid var(--g2)}
.sn{font-family:'Barlow Condensed',sans-serif;font-size:34px;font-weight:800;color:var(--red)}
.sl{font-size:11px;color:var(--g4);text-transform:uppercase;font-weight:600;margin-top:2px}
.pt{background:var(--g2);border-radius:999px;height:7px;margin:3px 0}
.pf{background:var(--red);border-radius:999px;height:100%;transition:width .4s}
.dt{width:100%;border-collapse:collapse;font-size:12px}
.dt th{text-align:left;padding:7px 9px;background:var(--g1);color:var(--g6);font-weight:700;font-size:10px;text-transform:uppercase}
.dt td{padding:7px 9px;border-bottom:1px solid var(--g1);vertical-align:middle}
.dt tr:last-child td{border-bottom:none}
.orb{font-size:9px;background:#EEF2FF;color:#4338CA;padding:2px 5px;border-radius:4px;font-weight:700}
.ob{border-left:3px solid #C7D2FE}
.ban{border-radius:var(--rl);padding:18px;margin:14px 0}
.bang{background:var(--red);color:#fff}
.banp{background:var(--green);color:#fff}
.blbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;opacity:.8;margin-bottom:4px}
.bloc{font-family:'Barlow Condensed',sans-serif;font-size:52px;font-weight:900;line-height:1}
.bqty{font-family:'Barlow Condensed',sans-serif;font-size:88px;font-weight:900;line-height:1}
.bunt{font-size:20px;font-weight:600;opacity:.9;margin-top:2px}
.bhnt{font-size:13px;opacity:.75;margin-top:6px}
@keyframes wo{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.4);opacity:0}}
@keyframes bp{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
.va{text-align:center;padding:8px 0 18px}
.rw{position:relative;display:inline-flex;align-items:center;justify-content:center;width:150px;height:150px;margin:0 auto 18px}
.rwave{position:absolute;width:150px;height:150px;border-radius:50%;background:var(--red);opacity:0;pointer-events:none}
.rwave.go{animation:wo 1.4s ease-out infinite}
.rwave:nth-child(2).go{animation-delay:.35s}
.rwave:nth-child(3).go{animation-delay:.7s}
.mic{position:relative;z-index:2;width:112px;height:112px;border-radius:50%;background:var(--red);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:3px;box-shadow:0 6px 22px rgba(200,16,46,.4)}
.mic:hover{background:var(--rd)}
.mic.lis{background:#1D4ED8;box-shadow:0 6px 22px rgba(29,78,216,.5);animation:bp 1s ease-in-out infinite}
.mic.spk{background:var(--green);animation:bp 1.5s ease-in-out infinite}
.mici{font-size:34px;line-height:1}
.micl{font-size:10px;font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:.06em}
.vs{font-size:14px;font-weight:600;color:var(--g6);min-height:22px;margin-bottom:8px}
.hb,.eb{border-radius:var(--r);padding:10px 14px;margin:8px 0;font-size:13px;font-weight:600;display:none}
.hb{background:var(--blt);border:2px solid var(--blue);color:var(--blue)}
.eb{background:#FEE2E2;border:2px solid #DC2626;color:#DC2626}
.hb.sh,.eb.sh{display:block}
.sdot{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;background:var(--g2);color:var(--g4)}
.sdot.on{background:var(--red);color:#fff}.sdot.dn{background:var(--green);color:#fff}
.sln{width:36px;height:2px;background:var(--g2)}.sln.dn{background:var(--green)}
.kt{background:none;border:none;color:var(--g4);font-size:12px;cursor:pointer;text-decoration:underline;font-family:'Barlow',sans-serif;padding:0}
.ks{display:none;margin-top:10px}.ks.op{display:block}
.bci{width:100%;padding:14px 18px;font-size:28px;font-family:'Barlow Condensed',sans-serif;font-weight:700;letter-spacing:.1em;border:3px solid var(--g2);border-radius:var(--rl);text-align:center;background:#fff;margin-top:10px}
.bci:focus{outline:none;border-color:var(--red)}
.dscrn{text-align:center;padding:36px 18px}
@keyframes pdot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}
@media(max-width:860px){.g2c{grid-template-columns:1fr}.sg{grid-template-columns:repeat(2,1fr)}}
"""
CSS_ESCAPED = CSS.replace("{", "{{").replace("}", "}}")
# ── Voice JS ─────────────────────────────────────────────────
VOICE_JS_TPL = """
var WFD       = JINJA_WFD;
var LOC       = "JINJA_LOC";
var QTY       = JINJA_QTY;
var ORDER_DONE= JINJA_ORDER_DONE;
var spoken=false, isLis=false, isSpk=false, recObj=null, blocked=false;

function speak(txt, cb) {
  if (!window.speechSynthesis) { if(cb) cb(); return; }
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(txt);
  u.rate=0.85; u.pitch=1.0; u.volume=1.0;
  var vs=window.speechSynthesis.getVoices();
  for(var i=0;i<vs.length;i++){if(vs[i].lang&&vs[i].lang.indexOf('en')===0){u.voice=vs[i];break;}}
  setState('spk');
  u.onend=function(){setState('idle');if(cb)cb();};
  u.onerror=function(){setState('idle');if(cb)cb();};
  window.speechSynthesis.speak(u);
}

var W2D={'zero':'0','oh':'0','o':'0','one':'1','won':'1','wan':'1',
  'two':'2','to':'2','too':'2','tu':'2','three':'3','tree':'3','free':'3',
  'four':'4','for':'4','fore':'4','five':'5','fife':'5','fi':'5',
  'six':'6','seven':'7','sewen':'7','eight':'8','ate':'8','eit':'8','nine':'9'};
var DONE_WORDS=['done','finish','finished','complete','completed','don','dun','ready','ok','okay'];

function norm(text){
  text=text.toLowerCase().trim().replace(/[.,!?]/g,'');
  var words=text.split(/ +/);
  for(var i=0;i<DONE_WORDS.length;i++){if(words.indexOf(DONE_WORDS[i])>=0)return 'done';}
  var digits=[],ok=true;
  for(var j=0;j<words.length;j++){
    var w=words[j];
    if(W2D[w]!==undefined)digits.push(W2D[w]);
    else if(/^[0-9]+$/.test(w))digits.push(w);
    else{ok=false;break;}
  }
  if(ok&&digits.length>0)return digits.join('');
  var compact=text.replace(/[^0-9]/g,'');
  if(compact.length>0)return compact;
  return text;
}

function bestResult(alts){
  for(var i=0;i<alts.length;i++){
    var c=norm(alts[i].transcript);
    if(/^[0-9]+$/.test(c)||c==='done')return c;
  }
  return norm(alts[0].transcript);
}

function listen(){
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){showErr('Voice not supported. Use Chrome or type below.');return;}
  if(isLis||isSpk)return;
  isLis=true; setState('lis'); hideErr();
  recObj=new SR();
  recObj.lang='en-US'; recObj.interimResults=false; recObj.maxAlternatives=5;
  recObj.onresult=function(e){
    isLis=false; setState('idle');
    var best=bestResult(Array.from(e.results[0]));
    var heard=e.results[0][0].transcript;
    showHrd('Heard: "'+heard+'" -> '+best);
    if(WFD){
      if(best==='done'){
        setVS('Done! Submitting...');
        speak('Task complete. Loading next task.',function(){document.getElementById('doneF').submit();});
      } else {
        showErr('I heard "'+heard+'". Please say DONE when finished. Tap mic to try again.');
        speak('Please say done when finished picking.');
        /* NO auto-restart - worker must tap again */
      }
    } else {
      if(/^[0-9]+$/.test(best)){
        document.getElementById('codeIn').value=best;
        speak('Checking code '+best.split('').join(' ')+'.',function(){document.getElementById('codeF').submit();});
      } else {
        showErr('I heard "'+heard+'". Say only the numbers from the label. Tap mic to try again.');
        speak('Please say only the numbers on the shelf label. Tap to try again.');
        /* NO auto-restart - worker must tap again */
      }
    }
  };
  recObj.onerror=function(e){
    isLis=false; setState('idle');
    var msgs={'not-allowed':'Allow microphone access in browser settings.',
              'no-speech':'Nothing heard. Tap and speak clearly.',
              'audio-capture':'No microphone found.',
              'network':'Voice network error.',
              'aborted':'Stopped. Tap to try again.'};
    showErr(msgs[e.error]||'Voice error. Tap to try again.');
    /* NO auto-restart */
  };
  recObj.onend=function(){if(isLis){isLis=false;setState('idle');}};
  try{recObj.start();}
  catch(err){isLis=false;setState('idle');showErr('Could not start mic. Tap to try again.');}
}

window.addEventListener('load',function(){
  if(window.speechSynthesis)window.speechSynthesis.getVoices();
  setTimeout(function(){
    if(spoken||!LOC)return;
    spoken=true;
    var lt=LOC.split('').join(' ');
    if(ORDER_DONE){
      /* Previous order just finished — announce order complete THEN next location */
      if(!WFD){
        speak('Order complete. Well done. Now start the next order. Go to location '+lt+'. Tap the microphone and say the confirmation code from the shelf label.');
      } else {
        var unit=(QTY===1)?'product':'products';
        speak('Order complete. Well done. Next task. Pick '+QTY+' '+unit+' from location '+lt+'. Say done when finished.');
      }
    } else {
      if(!WFD){
        speak('Go to location '+lt+'. Tap the microphone and say the confirmation code from the shelf label.');
      } else {
        var unit=(QTY===1)?'product':'products';
        speak('Code correct. Pick '+QTY+' '+unit+' from '+lt+'. Tap the microphone and say done when finished.');
      }
    }
  },900);
});

function tapMic(){
  hideErr();
  if(isSpk){window.speechSynthesis.cancel();setState('idle');setTimeout(listen,400);}
  else if(!isLis){listen();}
}

function setState(s){
  isSpk=(s==='spk'); isLis=(s==='lis');
  var btn=document.getElementById('micB'),lbl=document.getElementById('micL');
  if(!btn)return;
  btn.classList.remove('lis','spk');
  if(s==='lis'){btn.classList.add('lis');if(lbl)lbl.textContent='LISTENING';setW(true);setVS('Listening... speak now');}
  else if(s==='spk'){btn.classList.add('spk');if(lbl)lbl.textContent='SPEAKING';setW(true);setVS('Speaking...');}
  else{if(lbl)lbl.textContent=WFD?'SAY DONE':'TAP & SPEAK';setW(false);setVS(WFD?'Tap mic and say done when finished':'Tap mic and say the confirmation code');}
}
function setW(on){['w1','w2','w3'].forEach(function(id){var e=document.getElementById(id);if(e){if(on)e.classList.add('go');else e.classList.remove('go');}});}
function setVS(t){var e=document.getElementById('vs');if(e)e.textContent=t;}
function showHrd(t){var e=document.getElementById('hb');if(e){e.textContent=t;e.classList.add('sh');setTimeout(function(){e.classList.remove('sh');},5000);}}
function showErr(t){var e=document.getElementById('eb');if(e){e.textContent=t;e.classList.add('sh');}}
function hideErr(){var e=document.getElementById('eb');if(e)e.classList.remove('sh');}
function togKB(){var s=document.getElementById('ks');if(s){s.classList.toggle('op');var i=document.getElementById('kbI');if(i&&s.classList.contains('op'))i.focus();}}
"""


# ── HTML Templates ────────────────────────────────────────────
# CSS is embedded directly so Jinja never processes CSS braces

def _build_style():
    return "<style>" + CSS + "</style>"

STYLE = _build_style()

LOGIN_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lindstorm Login</title>
<style>{{CSS}}
body{display:flex;align-items:center;justify-content:center;
     background:linear-gradient(135deg,#1a0008 0%,#3a0010 40%,#C8102E 100%);min-height:100vh}
.lb{width:100%;max-width:400px;padding:14px}
.lc{background:#fff;border-radius:20px;padding:34px 30px;box-shadow:0 20px 60px rgba(0,0,0,.35)}
.ll{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:26px}
.li{width:50px;height:50px;background:var(--red);border-radius:11px;display:flex;align-items:center;justify-content:center}
.li svg{width:30px;height:30px;fill:#fff}
.ln{font-family:'Barlow Condensed',sans-serif;font-size:26px;font-weight:800;color:var(--red)}
.lsb{font-size:11px;color:var(--g4);text-transform:uppercase;letter-spacing:.07em;text-align:center;margin:-16px 0 24px}
.dbox{background:var(--g1);border-radius:var(--r);padding:10px 13px;margin-top:18px;font-size:12px;color:var(--g6)}
.dbox div{margin-top:3px}
</style></head>
<body><div class="lb"><div class="lc">
<div class="ll">
  <div class="li"><svg viewBox="0 0 32 32"><path d="M4 8h6v16H4zm8-4h6v20h-6zm8 6h6v14h-6z"/></svg></div>
  <div class="ln">LINDSTORM</div>
</div>
<div class="lsb">Voice-First Warehouse System</div>
{% if err %}<div class="flash fe">{{ err }}</div>{% endif %}
<form method="post" action="/login">
  <input type="hidden" name="csrf_token" value="{{ tok }}">
  <div class="fg"><label class="fl">Username</label>
    <input class="fi" type="text" name="username" placeholder="Enter username" required autocomplete="username"></div>
  <div class="fg"><label class="fl">Password</label>
    <input class="fi" type="password" name="password" placeholder="Enter password" required autocomplete="current-password"></div>
  <button class="btn br" type="submit" style="margin-top:18px">Sign In</button>
</form>
<div class="dbox"><strong>Demo accounts:</strong>
  <div>Worker:&#8194;&#8194;&#8194; worker1 / worker123</div>
  <div>Worker:&#8194;&#8194;&#8194; worker2 / worker456</div>
  <div>Supervisor: supervisor1 / super123</div>
</div>
</div></div></body></html>"""


WORKER_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lindstorm Picking</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--red:#C8102E;--rd:#9B0B22;--wh:#fff;--off:#F8F8F8;--g1:#F2F2F2;--g2:#E0E0E0;--g4:#9E9E9E;--g6:#555;--g9:#111;--green:#16A34A;--glt:#D1FAE5;--amber:#D97706;--alt:#FEF3C7;--blue:#1D4ED8;--blt:#EFF6FF;--r:10px;--rl:16px}
body{font-family:'Barlow',sans-serif;background:var(--off);color:var(--g9);min-height:100vh}
.nav{background:var(--red);color:#fff;padding:0 20px;height:56px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(200,16,46,.35);position:sticky;top:0;z-index:100}
.nb{display:flex;align-items:center;gap:10px;text-decoration:none;color:#fff}
.nlogo{width:34px;height:34px;background:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center}
.nlogo svg{width:20px;height:20px;fill:var(--red)}
.ntit{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:800}
.nsub{font-size:10px;opacity:.75;text-transform:uppercase;letter-spacing:.05em}
.nr{display:flex;align-items:center;gap:8px}
.pill{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:3px 11px;font-size:12px}
.nbtn{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:5px 12px;border-radius:6px;font-size:12px;cursor:pointer;font-family:'Barlow',sans-serif;text-decoration:none;display:inline-block}
.tabs{background:var(--rd);display:flex;padding:0 20px}
.tab{color:rgba(255,255,255,.65);padding:9px 16px;font-size:13px;font-weight:600;text-decoration:none;border-bottom:3px solid transparent}
.tab:hover,.tab.on{color:#fff}.tab.on{border-bottom-color:#fff}
.tab.mlt{background:rgba(255,255,255,.08)}
.page{max-width:1180px;margin:0 auto;padding:20px 14px 48px}
.card{background:#fff;border-radius:var(--rl);box-shadow:0 4px 16px rgba(0,0,0,.09);padding:22px;border:1px solid var(--g2)}
.ch{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;padding-bottom:12px;border-bottom:2px solid var(--g1)}
.ct{font-family:'Barlow Condensed',sans-serif;font-size:17px;font-weight:700;display:flex;align-items:center;gap:8px}
.ico{width:26px;height:26px;background:var(--red);border-radius:6px;display:inline-flex;align-items:center;justify-content:center;font-size:13px}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 16px;border:none;border-radius:var(--r);font-family:'Barlow',sans-serif;font-size:14px;font-weight:600;cursor:pointer;width:100%;margin-top:8px}
.br{background:var(--red);color:#fff}.br:hover{background:var(--rd)}
.bg{background:var(--green);color:#fff}
.bo{background:transparent;border:2px solid var(--red);color:var(--red)}.bo:hover{background:var(--red);color:#fff}
.bsm{padding:6px 10px;font-size:12px;width:auto;margin-top:0}
.fg{margin-top:12px}
.fl{display:block;font-size:12px;font-weight:600;color:var(--g6);margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em}
.fi{width:100%;padding:10px 12px;font-size:15px;font-family:'Barlow',sans-serif;border:2px solid var(--g2);border-radius:var(--r);background:#fff}
.fi:focus{outline:none;border-color:var(--red)}
.chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase}
.cpend{background:var(--alt);color:var(--amber)}.cdone{background:var(--glt);color:var(--green)}.cact{background:var(--blt);color:var(--blue)}.cwrong{background:#FEE2E2;color:#DC2626}
.flash{padding:11px 14px;border-radius:var(--r);margin-bottom:14px;font-weight:500;font-size:14px}
.fs{background:var(--glt);color:var(--green);border-left:4px solid var(--green)}
.fe{background:#FEE2E2;color:#DC2626;border-left:4px solid #DC2626}
.fi2{background:var(--blt);color:var(--blue);border-left:4px solid var(--blue)}
.g2c{display:grid;grid-template-columns:1.15fr 1fr;gap:18px}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}
.sb{background:#fff;border-radius:var(--r);padding:14px;text-align:center;border:1px solid var(--g2)}
.sn{font-family:'Barlow Condensed',sans-serif;font-size:34px;font-weight:800;color:var(--red)}
.sl{font-size:11px;color:var(--g4);text-transform:uppercase;font-weight:600;margin-top:2px}
.pt{background:var(--g2);border-radius:999px;height:7px;margin:3px 0}
.pf{background:var(--red);border-radius:999px;height:100%;transition:width .4s}
.dt{width:100%;border-collapse:collapse;font-size:12px}
.dt th{text-align:left;padding:7px 9px;background:var(--g1);color:var(--g6);font-weight:700;font-size:10px;text-transform:uppercase}
.dt td{padding:7px 9px;border-bottom:1px solid var(--g1);vertical-align:middle}
.dt tr:last-child td{border-bottom:none}
.orb{font-size:9px;background:#EEF2FF;color:#4338CA;padding:2px 5px;border-radius:4px;font-weight:700}
.ob{border-left:3px solid #C7D2FE}
.ban{border-radius:var(--rl);padding:18px;margin:14px 0}
.bang{background:var(--red);color:#fff}
.banp{background:var(--green);color:#fff}
.blbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;opacity:.8;margin-bottom:4px}
.bloc{font-family:'Barlow Condensed',sans-serif;font-size:52px;font-weight:900;line-height:1}
.bqty{font-family:'Barlow Condensed',sans-serif;font-size:88px;font-weight:900;line-height:1}
.bunt{font-size:20px;font-weight:600;opacity:.9;margin-top:2px}
.bhnt{font-size:13px;opacity:.75;margin-top:6px}
@keyframes wo{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.4);opacity:0}}
@keyframes bp{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
.va{text-align:center;padding:8px 0 18px}
.rw{position:relative;display:inline-flex;align-items:center;justify-content:center;width:150px;height:150px;margin:0 auto 18px}
.rwave{position:absolute;width:150px;height:150px;border-radius:50%;background:var(--red);opacity:0;pointer-events:none}
.rwave.go{animation:wo 1.4s ease-out infinite}
.rwave:nth-child(2).go{animation-delay:.35s}
.rwave:nth-child(3).go{animation-delay:.7s}
.mic{position:relative;z-index:2;width:112px;height:112px;border-radius:50%;background:var(--red);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:3px;box-shadow:0 6px 22px rgba(200,16,46,.4)}
.mic:hover{background:var(--rd)}
.mic.lis{background:#1D4ED8;box-shadow:0 6px 22px rgba(29,78,216,.5);animation:bp 1s ease-in-out infinite}
.mic.spk{background:var(--green);animation:bp 1.5s ease-in-out infinite}
.mici{font-size:34px;line-height:1}
.micl{font-size:10px;font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:.06em}
.vs{font-size:14px;font-weight:600;color:var(--g6);min-height:22px;margin-bottom:8px}
.hb,.eb{border-radius:var(--r);padding:10px 14px;margin:8px 0;font-size:13px;font-weight:600;display:none}
.hb{background:var(--blt);border:2px solid var(--blue);color:var(--blue)}
.eb{background:#FEE2E2;border:2px solid #DC2626;color:#DC2626}
.hb.sh,.eb.sh{display:block}
.sdot{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;background:var(--g2);color:var(--g4)}
.sdot.on{background:var(--red);color:#fff}.sdot.dn{background:var(--green);color:#fff}
.sln{width:36px;height:2px;background:var(--g2)}.sln.dn{background:var(--green)}
.kt{background:none;border:none;color:var(--g4);font-size:12px;cursor:pointer;text-decoration:underline;font-family:'Barlow',sans-serif;padding:0}
.ks{display:none;margin-top:10px}.ks.op{display:block}
.bci{width:100%;padding:14px 18px;font-size:28px;font-family:'Barlow Condensed',sans-serif;font-weight:700;letter-spacing:.1em;border:3px solid var(--g2);border-radius:var(--rl);text-align:center;background:#fff;margin-top:10px}
.bci:focus{outline:none;border-color:var(--red)}
.dscrn{text-align:center;padding:36px 18px}
@keyframes pdot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}
@media(max-width:860px){.g2c{grid-template-columns:1fr}.sg{grid-template-columns:repeat(2,1fr)}}</style></head><body>
<nav class="nav">
  <a class="nb" href="/">
    <div class="nlogo"><svg viewBox="0 0 32 32"><path d="M4 8h6v16H4zm8-4h6v20h-6zm8 6h6v14h-6z"/></svg></div>
    <div><div class="ntit">LINDSTORM</div><div class="nsub">Voice Picking</div></div>
  </a>
  <div class="nr">
    <span class="pill">{{ user.full_name or user.username }}</span>
    <button class="nbtn" onclick="document.getElementById('hmod').style.display='flex'">? Help</button>
    <form method="post" action="/logout" style="margin:0">
      <input type="hidden" name="csrf_token" value="{{ tok }}">
      <button class="nbtn" type="submit">Logout</button>
    </form>
  </div>
</nav>
<!-- Help Modal — H10 heuristic fix -->
<div id="hmod" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:999;align-items:center;justify-content:center;">
  <div style="background:#fff;border-radius:16px;padding:26px;max-width:460px;width:92%;position:relative;">
    <button onclick="document.getElementById('hmod').style.display='none'"
      style="position:absolute;top:12px;right:12px;background:var(--g2);border:none;border-radius:50%;width:28px;height:28px;cursor:pointer;font-size:15px;">x</button>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:800;color:var(--red);margin-bottom:14px;">How to Use Voice Picking</div>
    <div style="font-size:13px;color:var(--g6);line-height:1.9;">
      <p style="margin-bottom:9px;"><strong style="color:var(--g9);">Step 1 - Go to location</strong><br>The app speaks the shelf location. Walk there.</p>
      <p style="margin-bottom:9px;"><strong style="color:var(--g9);">Step 2 - Say the code</strong><br>Tap the red mic button. Say the number on the shelf label. Example: say "eight five" for code 85.</p>
      <p style="margin-bottom:9px;"><strong style="color:var(--g9);">Step 3 - Pick and say done</strong><br>Pick the items. Tap mic and say "done".</p>
      <p style="margin-bottom:9px;"><strong style="color:var(--g9);">Voice not working?</strong><br>Tap "Type manually instead" to use keyboard.</p>
      <p><strong style="color:var(--g9);">Wrong code?</strong><br>App says wrong once then listens again automatically.</p>
    </div>
  </div>
</div>
<div class="page"><div class="g2c">
<!-- LEFT: picking area -->
<div>
  {% if flash %}<div class="flash {{ 'fs' if 'complete' in flash or 'correct' in flash else 'fe' if 'wrong' in flash.lower() or 'Wrong' in flash else 'fi2' }}">{{ flash }}</div>{% endif %}
  <div class="card">
    <div style="height:4px;background:var(--red);border-radius:4px;margin-bottom:16px;width:60px;"></div>
    
    {% if task %}
      {% if not wfd %}
      <div class="ban bang">
        {% if task.order_id %}<div style="font-size:10px;opacity:.75;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;">Order {{ task.order_id[-8:] }}</div>{% endif %}
        <div class="blbl">Go to location</div>
        <div class="bloc">{{ task.location }}</div>
        <div class="bhnt">Tap the mic and speak the confirmation code from the shelf label</div>
        {% if task.priority %}<div style="display:inline-block;background:rgba(255,255,255,.2);border-radius:999px;padding:2px 10px;font-size:11px;font-weight:700;margin-top:8px;">&#9733; Priority Task</div>{% endif %}
      </div>
      {% else %}
      <div class="ban banp">
        {% if task.order_id %}<div style="font-size:10px;opacity:.75;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;">Order {{ task.order_id[-8:] }}</div>{% endif %}
        <div class="blbl">Code correct - now pick</div>
        <div class="bqty">{{ task.products }}</div>
        <div class="bunt">product{{ 's' if task.products != 1 else '' }} from {{ task.location }}</div>
        <div class="bhnt">Tap mic and say "done" when finished</div>
      </div>
      {% endif %}
      <div class="va">
        <div class="rw">
          <div class="rwave" id="w1"></div>
          <div class="rwave" id="w2"></div>
          <div class="rwave" id="w3"></div>
          <button class="mic" id="micB" onclick="tapMic()">
            <div class="mici" id="micI">&#127908;</div>
            <div class="micl" id="micL">{{ 'SAY DONE' if wfd else 'TAP &amp; SPEAK' }}</div>
          </button>
        </div>
        <div class="vs" id="vs">{{ 'Tap and say done when finished picking' if wfd else 'Tap and say the confirmation code' }}</div>
      </div>
      <div class="hb" id="hb"></div>
      <div class="eb" id="eb"></div>
      <form method="post" action="/check" id="codeF" style="display:none;">
        <input type="hidden" name="csrf_token" value="{{ tok }}">
        <input type="hidden" name="confirm_code" id="codeIn">
      </form>
      <form method="post" action="/done" id="doneF" style="display:none;">
        <input type="hidden" name="csrf_token" value="{{ tok }}">
      </form>
      <div style="text-align:center;margin-top:16px;">
        <button class="kt" onclick="togKB()">Type manually instead</button>
      </div>
      <div class="ks" id="ks">
        {% if not wfd %}
        <form method="post" action="/check">
          <input type="hidden" name="csrf_token" value="{{ tok }}">
          <input class="bci" type="text" name="confirm_code" placeholder="Type code here" inputmode="numeric" autocomplete="off" id="kbI">
          <button class="btn br" type="submit" style="margin-top:10px;">Check Code</button>
        </form>
        {% else %}
        <form method="post" action="/done">
          <input type="hidden" name="csrf_token" value="{{ tok }}">
          <button class="btn bg" type="submit" style="font-size:17px;padding:14px;margin-top:10px;">Done - Picked All Products</button>
        </form>
        {% endif %}
      </div>
    {% else %}
    <!-- Waiting screen -->
    <div class="dscrn">
      {% if order_just_completed %}
      <div style="font-size:52px;margin-bottom:8px;">&#127881;</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:800;color:var(--green);">Order Complete!</div>
      <div style="color:var(--g6);margin-top:6px;font-size:14px;font-weight:600;">All locations in this order are done. Well done!</div>
      <div style="color:var(--g4);margin-top:4px;font-size:13px;">Waiting for the next order from supervisor...</div>
      {% else %}
      <div style="font-size:52px;margin-bottom:8px;">&#9203;</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:800;color:var(--amber);">Waiting for Orders</div>
      <div style="color:var(--g6);margin-top:6px;font-size:14px;">All tasks complete. Waiting for supervisor to create a new order.</div>
      {% endif %}
      <div style="margin-top:16px;display:inline-flex;align-items:center;gap:8px;background:var(--alt);border-radius:999px;padding:8px 20px;">
        <div style="width:9px;height:9px;border-radius:50%;background:var(--amber);animation:pdot 1.2s ease-in-out infinite;"></div>
        <span style="font-size:13px;font-weight:600;color:var(--amber);" id="pollTxt">Checking every 4 seconds...</span>
      </div>
      <div style="margin-top:20px;background:var(--g1);border-radius:var(--rl);padding:16px 20px;max-width:340px;margin-left:auto;margin-right:auto;text-align:left;">
        <div style="font-size:12px;font-weight:700;color:var(--g6);margin-bottom:8px;text-transform:uppercase;">While waiting:</div>
        <div style="font-size:13px;color:var(--g6);line-height:1.9;">
          Stay near the warehouse shelves<br>
          App will speak when new order arrives<br>
          You do not need to tap anything<br>
          Keep phone volume turned up
        </div>
      </div>
      <script>
      var ORDER_JUST_DONE = {{ 'true' if order_just_completed else 'false' }};
      /* ── voice helper ── */
      function sayMsg(msg, cb) {
        if (!window.speechSynthesis) { if(cb) cb(); return; }
        window.speechSynthesis.cancel();
        var u = new SpeechSynthesisUtterance(msg);
        u.rate = 0.85; u.pitch = 1.0; u.volume = 1.0;
        /* pick English voice */
        var vs = window.speechSynthesis.getVoices();
        for (var i=0; i<vs.length; i++) {
          if (vs[i].lang && vs[i].lang.indexOf('en') === 0) { u.voice = vs[i]; break; }
        }
        if (cb) u.onend = cb;
        window.speechSynthesis.speak(u);
      }

      /* ── speak order-complete message on page load ── */
      (function(){
        var announced = false;
        function announce() {
          if (announced) return;
          announced = true;
          var msg = ORDER_JUST_DONE
            ? 'Order complete. Well done. All locations in this order are picked. Please wait for the next order from supervisor.'
            : 'All tasks complete. Well done. Please wait for the supervisor to create a new order.';
          sayMsg(msg);
        }
        /* try immediately, and again after voices load */
        setTimeout(announce, 800);
        if (window.speechSynthesis) {
          window.speechSynthesis.onvoiceschanged = function() { setTimeout(announce, 300); };
        }
      })();

      /* ── poll for new tasks every 4 seconds ── */
      var pollActive = true;
      var pi = setInterval(function(){
        if (!pollActive) return;
        fetch('/api/poll-tasks')
          .then(function(r){ return r.json(); })
          .then(function(d){
            if (d.has_task && pollActive) {
              pollActive = false;
              clearInterval(pi);
              var el = document.getElementById('pollTxt');
              if (el) el.textContent = 'New order received! Loading...';
              var lt = d.location ? d.location.split('').join(' ') : '';
              var msg = 'Attention. New order received. Go to location ' + lt + '. Tap the microphone and speak the confirmation code from the shelf label.';
              sayMsg(msg, function(){ window.location.reload(); });
              /* fallback reload if speech fails */
              setTimeout(function(){ window.location.reload(); }, 8000);
            }
          })
          .catch(function(){ /* ignore network errors, keep polling */ });
      }, 4000);
      </script>
    </div>
    {% endif %}
  </div>
</div>
<!-- RIGHT: task list -->
<div>
  <div class="card">
    <div class="ch">
      <div class="ct"><span class="ico">&#128230;</span> My Tasks</div>
      <span style="font-size:12px;color:var(--g4);">{{ done_cnt }}/{{ total_cnt }} done</span>
    </div>
    {% if total_cnt > 0 %}
    <div style="margin-bottom:14px;">
      <div class="pt"><div class="pf" style="width:{{ pct }}%;"></div></div>
    </div>
    {% endif %}

    {% if all_tasks %}
      {% set ns = namespace(last_order='__NONE__') %}
      {% for t in all_tasks %}

        {% if t.order_id and t.order_id != ns.last_order %}
          {% set ns.last_order = t.order_id %}
          {% if not loop.first %}<div style="height:8px;"></div>{% endif %}
          {% set all_done = namespace(v=true) %}
          {% for ot in all_tasks %}{% if ot.order_id == t.order_id and ot.status != 'done' %}{% set all_done.v = false %}{% endif %}{% endfor %}
          <div style="display:flex;align-items:center;gap:6px;margin:6px 0 4px 0;">
            <div style="background:{% if all_done.v %}var(--green){% else %}#4338CA{% endif %};color:#fff;font-size:9px;font-weight:700;padding:2px 8px;border-radius:4px;white-space:nowrap;">
              ORDER {{ t.order_id[-6:] }}{% if all_done.v %} &#10003;{% endif %}
            </div>
            <div style="flex:1;height:1px;background:#E0E7FF;"></div>
          </div>
        {% elif not t.order_id %}
          {% set ns.last_order = '__NONE__' %}
        {% endif %}

        <div style="display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:7px;margin-bottom:3px;
          {% if t.order_id %}border-left:3px solid {% if t.status=='done' %}#86EFAC{% elif t.in_progress %}#93C5FD{% else %}#C7D2FE{% endif %};{% endif %}
          background:{{ 'var(--glt)' if t.status=='done' else 'var(--blt)' if t.in_progress else 'var(--g1)' }};">
          <span style="font-size:13px;font-weight:800;color:{{ 'var(--green)' if t.status=='done' else 'var(--blue)' if t.in_progress else 'var(--g4)' }};">
            {{ '✓' if t.status=='done' else '▶' if t.in_progress else '○' }}
          </span>
          <span style="font-weight:700;font-size:13px;color:{{ 'var(--green)' if t.status=='done' else 'var(--blue)' if t.in_progress else 'var(--g6)' }};">{{ t.location }}</span>
          <span style="font-size:11px;color:var(--g4);">{{ t.products }} pc{{ 's' if t.products!=1 else '' }}</span>
          <span style="margin-left:auto;font-size:10px;font-weight:700;padding:2px 7px;border-radius:999px;
            background:{{ 'var(--glt)' if t.status=='done' else 'var(--blt)' if t.in_progress else 'var(--g2)' }};
            color:{{ 'var(--green)' if t.status=='done' else 'var(--blue)' if t.in_progress else 'var(--g4)' }};">
            {{ 'DONE' if t.status=='done' else 'ACTIVE' if t.in_progress else 'PENDING' }}
          </span>
        </div>
      {% endfor %}
    {% else %}
      <p style="color:var(--g4);font-size:13px;padding:10px 0;">No tasks assigned yet.</p>
    {% endif %}
  </div>
</div>
</div></div>
<script>{{ js | safe }}</script>
</body></html>"""

SUP_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lindstorm Supervisor</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--red:#C8102E;--rd:#9B0B22;--wh:#fff;--off:#F8F8F8;--g1:#F2F2F2;--g2:#E0E0E0;--g4:#9E9E9E;--g6:#555;--g9:#111;--green:#16A34A;--glt:#D1FAE5;--amber:#D97706;--alt:#FEF3C7;--blue:#1D4ED8;--blt:#EFF6FF;--r:10px;--rl:16px}
body{font-family:'Barlow',sans-serif;background:var(--off);color:var(--g9);min-height:100vh}
.nav{background:var(--red);color:#fff;padding:0 20px;height:56px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(200,16,46,.35);position:sticky;top:0;z-index:100}
.nb{display:flex;align-items:center;gap:10px;text-decoration:none;color:#fff}
.nlogo{width:34px;height:34px;background:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center}
.nlogo svg{width:20px;height:20px;fill:var(--red)}
.ntit{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:800}
.nsub{font-size:10px;opacity:.75;text-transform:uppercase;letter-spacing:.05em}
.nr{display:flex;align-items:center;gap:8px}
.pill{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:3px 11px;font-size:12px}
.nbtn{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:5px 12px;border-radius:6px;font-size:12px;cursor:pointer;font-family:'Barlow',sans-serif;text-decoration:none;display:inline-block}
.tabs{background:var(--rd);display:flex;padding:0 20px}
.tab{color:rgba(255,255,255,.65);padding:9px 16px;font-size:13px;font-weight:600;text-decoration:none;border-bottom:3px solid transparent}
.tab:hover,.tab.on{color:#fff}.tab.on{border-bottom-color:#fff}
.tab.mlt{background:rgba(255,255,255,.08)}
.page{max-width:1180px;margin:0 auto;padding:20px 14px 48px}
.card{background:#fff;border-radius:var(--rl);box-shadow:0 4px 16px rgba(0,0,0,.09);padding:22px;border:1px solid var(--g2)}
.ch{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;padding-bottom:12px;border-bottom:2px solid var(--g1)}
.ct{font-family:'Barlow Condensed',sans-serif;font-size:17px;font-weight:700;display:flex;align-items:center;gap:8px}
.ico{width:26px;height:26px;background:var(--red);border-radius:6px;display:inline-flex;align-items:center;justify-content:center;font-size:13px}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 16px;border:none;border-radius:var(--r);font-family:'Barlow',sans-serif;font-size:14px;font-weight:600;cursor:pointer;width:100%;margin-top:8px}
.br{background:var(--red);color:#fff}.br:hover{background:var(--rd)}
.bg{background:var(--green);color:#fff}
.bo{background:transparent;border:2px solid var(--red);color:var(--red)}.bo:hover{background:var(--red);color:#fff}
.bsm{padding:6px 10px;font-size:12px;width:auto;margin-top:0}
.fg{margin-top:12px}
.fl{display:block;font-size:12px;font-weight:600;color:var(--g6);margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em}
.fi{width:100%;padding:10px 12px;font-size:15px;font-family:'Barlow',sans-serif;border:2px solid var(--g2);border-radius:var(--r);background:#fff}
.fi:focus{outline:none;border-color:var(--red)}
.chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase}
.cpend{background:var(--alt);color:var(--amber)}.cdone{background:var(--glt);color:var(--green)}.cact{background:var(--blt);color:var(--blue)}.cwrong{background:#FEE2E2;color:#DC2626}
.flash{padding:11px 14px;border-radius:var(--r);margin-bottom:14px;font-weight:500;font-size:14px}
.fs{background:var(--glt);color:var(--green);border-left:4px solid var(--green)}
.fe{background:#FEE2E2;color:#DC2626;border-left:4px solid #DC2626}
.fi2{background:var(--blt);color:var(--blue);border-left:4px solid var(--blue)}
.g2c{display:grid;grid-template-columns:1.15fr 1fr;gap:18px}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}
.sb{background:#fff;border-radius:var(--r);padding:14px;text-align:center;border:1px solid var(--g2)}
.sn{font-family:'Barlow Condensed',sans-serif;font-size:34px;font-weight:800;color:var(--red)}
.sl{font-size:11px;color:var(--g4);text-transform:uppercase;font-weight:600;margin-top:2px}
.pt{background:var(--g2);border-radius:999px;height:7px;margin:3px 0}
.pf{background:var(--red);border-radius:999px;height:100%;transition:width .4s}
.dt{width:100%;border-collapse:collapse;font-size:12px}
.dt th{text-align:left;padding:7px 9px;background:var(--g1);color:var(--g6);font-weight:700;font-size:10px;text-transform:uppercase}
.dt td{padding:7px 9px;border-bottom:1px solid var(--g1);vertical-align:middle}
.dt tr:last-child td{border-bottom:none}
.orb{font-size:9px;background:#EEF2FF;color:#4338CA;padding:2px 5px;border-radius:4px;font-weight:700}
.ob{border-left:3px solid #C7D2FE}
.ban{border-radius:var(--rl);padding:18px;margin:14px 0}
.bang{background:var(--red);color:#fff}
.banp{background:var(--green);color:#fff}
.blbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;opacity:.8;margin-bottom:4px}
.bloc{font-family:'Barlow Condensed',sans-serif;font-size:52px;font-weight:900;line-height:1}
.bqty{font-family:'Barlow Condensed',sans-serif;font-size:88px;font-weight:900;line-height:1}
.bunt{font-size:20px;font-weight:600;opacity:.9;margin-top:2px}
.bhnt{font-size:13px;opacity:.75;margin-top:6px}
@keyframes wo{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.4);opacity:0}}
@keyframes bp{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
.va{text-align:center;padding:8px 0 18px}
.rw{position:relative;display:inline-flex;align-items:center;justify-content:center;width:150px;height:150px;margin:0 auto 18px}
.rwave{position:absolute;width:150px;height:150px;border-radius:50%;background:var(--red);opacity:0;pointer-events:none}
.rwave.go{animation:wo 1.4s ease-out infinite}
.rwave:nth-child(2).go{animation-delay:.35s}
.rwave:nth-child(3).go{animation-delay:.7s}
.mic{position:relative;z-index:2;width:112px;height:112px;border-radius:50%;background:var(--red);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:3px;box-shadow:0 6px 22px rgba(200,16,46,.4)}
.mic:hover{background:var(--rd)}
.mic.lis{background:#1D4ED8;box-shadow:0 6px 22px rgba(29,78,216,.5);animation:bp 1s ease-in-out infinite}
.mic.spk{background:var(--green);animation:bp 1.5s ease-in-out infinite}
.mici{font-size:34px;line-height:1}
.micl{font-size:10px;font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:.06em}
.vs{font-size:14px;font-weight:600;color:var(--g6);min-height:22px;margin-bottom:8px}
.hb,.eb{border-radius:var(--r);padding:10px 14px;margin:8px 0;font-size:13px;font-weight:600;display:none}
.hb{background:var(--blt);border:2px solid var(--blue);color:var(--blue)}
.eb{background:#FEE2E2;border:2px solid #DC2626;color:#DC2626}
.hb.sh,.eb.sh{display:block}
.sdot{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;background:var(--g2);color:var(--g4)}
.sdot.on{background:var(--red);color:#fff}.sdot.dn{background:var(--green);color:#fff}
.sln{width:36px;height:2px;background:var(--g2)}.sln.dn{background:var(--green)}
.kt{background:none;border:none;color:var(--g4);font-size:12px;cursor:pointer;text-decoration:underline;font-family:'Barlow',sans-serif;padding:0}
.ks{display:none;margin-top:10px}.ks.op{display:block}
.bci{width:100%;padding:14px 18px;font-size:28px;font-family:'Barlow Condensed',sans-serif;font-weight:700;letter-spacing:.1em;border:3px solid var(--g2);border-radius:var(--rl);text-align:center;background:#fff;margin-top:10px}
.bci:focus{outline:none;border-color:var(--red)}
.dscrn{text-align:center;padding:36px 18px}
@keyframes pdot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}
@media(max-width:860px){.g2c{grid-template-columns:1fr}.sg{grid-template-columns:repeat(2,1fr)}}</style></head><body>
<nav class="nav">
  <a class="nb" href="/supervisor">
    <div class="nlogo"><svg viewBox="0 0 32 32"><path d="M4 8h6v16H4zm8-4h6v20h-6zm8 6h6v14h-6z"/></svg></div>
    <div><div class="ntit">LINDSTORM</div><div class="nsub">Supervisor</div></div>
  </a>
  <div class="nr">
    <span class="pill">{{ user.full_name or user.username }}</span>
    <a class="nbtn" href="/supervisor?tab=ml">&#129302; ML</a>
    <form method="post" action="/logout" style="margin:0;">
      <input type="hidden" name="csrf_token" value="{{ tok }}">
      <button class="nbtn" type="submit">Logout</button>
    </form>
  </div>
</nav>
<div class="tabs">
  <a class="tab {{ 'on' if tab=='tasks' else '' }}" href="/supervisor?tab=tasks">Tasks</a>
  <a class="tab {{ 'on' if tab=='workers' else '' }}" href="/supervisor?tab=workers">Workers</a>
  <a class="tab {{ 'on' if tab=='logs' else '' }}" href="/supervisor?tab=logs">Audit Log</a>
  <a class="tab mlt {{ 'on' if tab=='ml' else '' }}" href="/supervisor?tab=ml">&#129302; ML Insights</a>
</div>
<div class="page">
{% if flash %}<div class="flash {{ 'fs' if 'created' in flash or 'reset' in flash else 'fe' if 'error' in flash.lower() or 'Failed' in flash else 'fi2' }}">{{ flash }}</div>{% endif %}

{% if tab=='tasks' %}
<div class="sg">
  <div class="sb"><div class="sn">{{ stats.total }}</div><div class="sl">Total</div></div>
  <div class="sb"><div class="sn" style="color:var(--amber);">{{ stats.pending }}</div><div class="sl">Pending</div></div>
  <div class="sb"><div class="sn" style="color:var(--blue);">{{ stats.in_progress }}</div><div class="sl">Active</div></div>
  <div class="sb"><div class="sn" style="color:var(--green);">{{ stats.done }}</div><div class="sl">Done</div></div>
</div>
{% if stats.total > 0 %}
<div style="margin-bottom:18px;">
  <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--g4);margin-bottom:5px;"><span>Progress</span><span>{{ stats.done }} / {{ stats.total }}</span></div>
  <div class="pt"><div class="pf" style="width:{{ (stats.done/stats.total*100)|int }}%;"></div></div>
</div>
{% endif %}
<div class="g2c">
  <div class="card">
    <div class="ch">
      <div class="ct"><span class="ico">&#128230;</span> All Tasks</div>
      <form method="post" action="/supervisor/reset" style="margin:0;">
        <input type="hidden" name="csrf_token" value="{{ tok }}">
        <button class="btn bo bsm" type="submit" onclick="return confirm('Reset ALL tasks to pending?')">Reset All</button>
      </form>
    </div>
    <table class="dt">
      <thead><tr><th>#</th><th>Order</th><th>Location</th><th>Code</th><th>Qty</th><th>Worker</th><th>Status</th><th></th></tr></thead>
      <tbody>{% for t in tasks %}<tr {{ 'class=ob' if t.order_id else '' }}>
        <td style="color:var(--g4);">{{ t.sequence_no }}</td>
        <td>{% if t.order_id %}<span class="orb">{{ t.order_id[-8:] }}</span>{% else %}<span style="color:var(--g4);">-</span>{% endif %}</td>
        <td><strong>{{ t.location }}</strong></td>
        <td><code>{{ t.confirm_code }}</code></td>
        <td>{{ t.products }}</td>
        <td style="font-size:11px;color:var(--g4);">{{ t.assigned_to or '-' }}</td>
        <td>{% if t.status=='done' %}<span class="chip cdone">done</span>{% elif t.in_progress %}<span class="chip cact">active</span>{% else %}<span class="chip cpend">pending</span>{% endif %}</td>
        <td>{% if t.status=='pending' and not t.in_progress %}
          <form method="post" action="/supervisor/delete-task/{{ t.id }}" style="margin:0;">
            <input type="hidden" name="csrf_token" value="{{ tok }}">
            <button type="submit" onclick="return confirm('Delete?')" style="background:#FEE2E2;color:#DC2626;border:none;border-radius:5px;padding:3px 7px;cursor:pointer;font-size:11px;">X</button>
          </form>{% endif %}</td>
      </tr>{% endfor %}</tbody>
    </table>
  </div>
  <div class="card">
    <div class="ch"><div class="ct"><span class="ico">+</span> Create Order</div></div>
    <div class="fg"><label class="fl">Priority</label>
      <select class="fi" id="oPri"><option value="0">Normal</option><option value="1">High Priority</option></select></div>
    <div class="fg"><label class="fl">Assign to Worker (optional)</label>
      <select class="fi" id="oWrk"><option value="">Any worker</option>
        {% for w in workers %}{% if w.role=='worker' %}<option value="{{ w.username }}">{{ w.full_name or w.username }}</option>{% endif %}{% endfor %}
      </select></div>
    <hr style="border:none;border-top:1px solid var(--g2);margin:14px 0;">
    <div style="font-size:11px;font-weight:700;color:var(--g6);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Locations in this order</div>
    <div style="display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:4px;margin-bottom:5px;">
      <div style="font-size:9px;color:var(--g4);text-transform:uppercase;">Location</div>
      <div style="font-size:9px;color:var(--g4);text-transform:uppercase;">Code</div>
      <div style="font-size:9px;color:var(--g4);text-transform:uppercase;">Qty</div>
      <div></div>
    </div>
    <div id="lrows">
      <div class="lrow" style="display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:5px;margin-bottom:7px;align-items:center;">
        <input class="fi" type="text" placeholder="R01-10" style="padding:8px 9px;font-size:13px;text-transform:uppercase;">
        <input class="fi" type="text" placeholder="Code" inputmode="numeric" style="padding:8px 9px;font-size:13px;">
        <input class="fi" type="number" placeholder="Qty" min="1" style="padding:8px 9px;font-size:13px;">
        <button type="button" onclick="rmRow(this)" style="background:#FEE2E2;color:#DC2626;border:none;border-radius:6px;padding:8px 9px;cursor:pointer;font-size:15px;font-weight:700;">-</button>
      </div>
    </div>
    <button type="button" onclick="addRow()" style="width:100%;padding:8px;border:2px dashed var(--g2);background:none;border-radius:var(--r);font-size:12px;color:var(--g4);cursor:pointer;margin-bottom:10px;font-family:'Barlow',sans-serif;">+ Add another location</button>
    <form method="post" action="/supervisor/create-task" id="oForm">
      <input type="hidden" name="csrf_token" value="{{ tok }}">
      <input type="hidden" name="locations_json" id="lj">
      <input type="hidden" name="priority" id="ph">
      <input type="hidden" name="assigned_to" id="ah">
    </form>
    <button class="btn br" type="button" onclick="submitOrder()">Create All Tasks</button>
    <script>
    function addRow(){
      var c=document.getElementById('lrows'),d=document.createElement('div');
      d.className='lrow';
      d.style.cssText='display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:5px;margin-bottom:7px;align-items:center;';
      d.innerHTML='<input class="fi" type="text" placeholder="R01-10" style="padding:8px 9px;font-size:13px;text-transform:uppercase;"><input class="fi" type="text" placeholder="Code" inputmode="numeric" style="padding:8px 9px;font-size:13px;"><input class="fi" type="number" placeholder="Qty" min="1" style="padding:8px 9px;font-size:13px;"><button type="button" onclick="rmRow(this)" style="background:#FEE2E2;color:#DC2626;border:none;border-radius:6px;padding:8px 9px;cursor:pointer;font-size:15px;font-weight:700;">-</button>';
      c.appendChild(d);
    }
    function rmRow(b){var rows=document.querySelectorAll('.lrow');if(rows.length>1)b.parentElement.remove();}
    function submitOrder(){
      var rows=document.querySelectorAll('.lrow'),entries=[],valid=true;
      rows.forEach(function(row){
        var inp=row.querySelectorAll('input');
        var loc=inp[0].value.trim().toUpperCase(),code=inp[1].value.trim(),qty=parseInt(inp[2].value);
        if(!loc||!code||!qty||qty<1){valid=false;return;}
        entries.push({location:loc,confirm_code:code,products:qty});
      });
      if(!valid){alert('Please fill all location, code and quantity fields.');return;}
      if(!entries.length){alert('Add at least one location.');return;}
      document.getElementById('lj').value=JSON.stringify(entries);
      document.getElementById('ph').value=document.getElementById('oPri').value;
      document.getElementById('ah').value=document.getElementById('oWrk').value;
      document.getElementById('oForm').submit();
    }
    </script>
  </div>
</div>

{% elif tab=='workers' %}
<div class="g2c">
  <div class="card">
    <div class="ch"><div class="ct"><span class="ico">&#128202;</span> Today's Performance</div></div>
    {% if wstats %}
    <table class="dt"><thead><tr><th>Worker</th><th>Done</th><th>Errors</th><th>Avg Time</th></tr></thead><tbody>
    {% for s in wstats %}<tr>
      <td><strong>{{ s.full_name or s.username }}</strong></td>
      <td><strong style="color:var(--green);">{{ s.tasks_completed }}</strong></td>
      <td style="color:{{ 'var(--red)' if s.wrong_codes>2 else 'var(--g6)' }};">{{ s.wrong_codes }}</td>
      <td style="font-size:11px;color:var(--g4);">{% if s.tasks_completed>0 %}{{ (s.total_seconds//s.tasks_completed) }}s{% else %}-{% endif %}</td>
    </tr>{% endfor %}</tbody></table>
    {% else %}<p style="color:var(--g4);font-size:13px;padding:16px 0;">No activity today.</p>{% endif %}
  </div>
  <div class="card">
    <div class="ch"><div class="ct"><span class="ico">&#128100;</span> Add Worker</div></div>
    <form method="post" action="/supervisor/create-worker">
      <input type="hidden" name="csrf_token" value="{{ tok }}">
      <div class="fg"><label class="fl">Full Name</label><input class="fi" type="text" name="full_name" placeholder="John Smith"></div>
      <div class="fg"><label class="fl">Username</label><input class="fi" type="text" name="username" required></div>
      <div class="fg"><label class="fl">Password</label><input class="fi" type="password" name="password" required></div>
      <div class="fg"><label class="fl">Role</label>
        <select class="fi" name="role"><option value="worker">Worker</option><option value="supervisor">Supervisor</option></select></div>
      <button class="btn br" type="submit">Create Account</button>
    </form>
  </div>
</div>
<div class="card" style="margin-top:16px;">
  <div class="ch"><div class="ct"><span class="ico">&#128101;</span> All Users</div></div>
  <table class="dt"><thead><tr><th>Name</th><th>Username</th><th>Role</th></tr></thead><tbody>
  {% for w in workers %}<tr><td>{{ w.full_name or '-' }}</td><td><code>{{ w.username }}</code></td>
    <td><span class="chip {{ 'cact' if w.role=='supervisor' else 'cpend' }}">{{ w.role }}</span></td></tr>{% endfor %}
  </tbody></table>
</div>

{% elif tab=='logs' %}
<div class="card">
  <div class="ch"><div class="ct"><span class="ico">&#128203;</span> Audit Log</div></div>
  <table class="dt"><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Location</th><th>Code</th><th>Result</th></tr></thead><tbody>
  {% for e in logs %}<tr>
    <td style="font-size:10px;color:var(--g4);white-space:nowrap;">{{ e.timestamp }}</td>
    <td>{{ e.username or '-' }}</td><td>{{ e.action }}</td><td>{{ e.location or '-' }}</td>
    <td><code>{{ e.entered_code or '-' }}</code></td>
    <td>{% if e.result in ['correct','completed','success'] %}<span class="chip cdone">{{ e.result }}</span>{% elif e.result=='wrong' %}<span class="chip cwrong">{{ e.result }}</span>{% else %}<span style="font-size:11px;color:var(--g4);">{{ e.result or '-' }}</span>{% endif %}</td>
  </tr>{% endfor %}</tbody></table>
</div>

{% elif tab=='ml' %}
<div style="background:linear-gradient(135deg,#1D4ED8,#7C3AED);border-radius:var(--rl);padding:16px 22px;color:#fff;margin-bottom:18px;">
  <div style="font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:800;margin-bottom:4px;">&#129302; Machine Learning Insights</div>
  <div style="font-size:12px;opacity:.85;">Model 1: Demand Forecast (Linear Regression) &middot; Model 2: Worker Performance (Weighted Scoring)</div>
</div>
<div class="g2c">
  <div class="card">
    <div class="ch"><div class="ct"><span class="ico" style="background:#1D4ED8;">&#128202;</span> Demand Forecast - Tomorrow</div></div>
    <p style="font-size:11px;color:var(--g4);margin-bottom:12px;">Linear Regression on 7 days of pick history. Predicts tomorrow's pick count per location.</p>
    {% if ml_demand %}
    <table class="dt"><thead><tr><th>Location</th><th>Predicted</th><th>Trend</th><th>Avg/day</th></tr></thead><tbody>
    {% for item in ml_demand %}<tr>
      <td><strong>{{ item.location }}</strong></td>
      <td><strong style="color:var(--blue);font-size:14px;">{{ item.predicted }}</strong></td>
      <td>{% if item.trend=='rising' %}<span style="color:var(--red);font-weight:600;">&#8599; Rising</span>{% elif item.trend=='falling' %}<span style="color:var(--green);font-weight:600;">&#8600; Falling</span>{% else %}<span style="color:var(--g4);">&#8594; Stable</span>{% endif %}</td>
      <td style="color:var(--g4);">{{ item.recent_avg }}</td>
    </tr>{% endfor %}</tbody></table>
    <div style="background:var(--blt);border-radius:var(--r);padding:9px 12px;margin-top:12px;font-size:11px;color:var(--blue);"><strong>Tip:</strong> Rising locations need restocking before tomorrow.</div>
    {% else %}<p style="color:var(--g4);font-size:12px;">No pick history yet. Complete tasks to generate predictions.</p>{% endif %}
  </div>
  <div class="card">
    <div class="ch"><div class="ct"><span class="ico" style="background:#7C3AED;">&#128119;</span> Worker Performance Score</div></div>
    <p style="font-size:11px;color:var(--g4);margin-bottom:12px;">Score 0-100: Wrong Code Rate (50pts) + Pick Speed (50pts). Updates from today's data.</p>
    {% if ml_workers %}
    <table class="dt"><thead><tr><th>Worker</th><th>Score</th><th>Status</th><th>Wrong%</th></tr></thead><tbody>
    {% for w in ml_workers %}<tr>
      <td><strong>{{ w.full_name }}</strong></td>
      <td><div style="display:flex;align-items:center;gap:7px;"><div style="background:var(--g2);border-radius:999px;height:5px;width:55px;overflow:hidden;"><div style="height:100%;border-radius:999px;width:{{ w.score }}%;background:{{ 'var(--green)' if w.risk_col=='green' else 'var(--amber)' if w.risk_col=='amber' else 'var(--red)' }};"></div></div><strong>{{ w.score }}</strong></div></td>
      <td><span class="chip {{ 'cdone' if w.risk_col=='green' else 'cpend' if w.risk_col=='amber' else 'cwrong' }}">{{ w.risk }}</span></td>
      <td style="color:{{ 'var(--red)' if w.wrong_rate_pct>20 else 'var(--g4)' }};">{{ w.wrong_rate_pct }}%</td>
    </tr>{% endfor %}</tbody></table>
    {% else %}<p style="color:var(--g4);font-size:12px;">No worker data for today yet.</p>{% endif %}
  </div>
</div>

{% endif %}
</div></body></html>"""
# ── route helpers ─────────────────────────────────────────────

def render_login(error=None):
    html = LOGIN_HTML.replace("{{CSS}}", CSS)
    return render_template_string(
        html.replace("{%","{% ").replace("%}","-%}").replace("{{","{{ ").replace("}}","}}"),
        err=error, tok=mk_csrf())

def flash_class(msg):
    if not msg: return "fi2"
    m = msg.lower()
    if any(x in m for x in ["creat","reset","complet","correct","done"]): return "fs"
    if any(x in m for x in ["error","fail","wrong","invalid"]): return "fe"
    return "fi2"


# ── Login / Logout ────────────────────────────────────────────

@app.get("/login")
def login_page():
    if "user" in session: return redirect(url_for("home"))
    return render_template_string(
        LOGIN_HTML.replace("{{CSS}}", CSS),
        err=None, tok=mk_csrf())

@app.post("/login")
def login_post():
    # No CSRF check on login — user has no session yet when logging in
    r = apost("/api/login", {
        "username": request.form.get("username","").strip(),
        "password": request.form.get("password","")
    })
    d = pj(r)
    if d.get("ok"):
        session["user"]      = d["user"]
        session["api_token"] = d["token"]
        session.permanent    = True
        # generate CSRF token now that session exists
        mk_csrf()
        if d["user"]["role"] == "supervisor":
            return redirect(url_for("supervisor_dashboard"))
        return redirect(url_for("home"))
    return render_template_string(
        LOGIN_HTML.replace("{{CSS}}", CSS),
        err=d.get("error","Login failed. Check username and password."),
        tok=mk_csrf())

@app.post("/logout")
@login_req
def logout():
    if ok_csrf():
        try: apost("/api/logout")
        except Exception: pass
    session.clear()
    return redirect(url_for("login_page"))

@app.get("/")
def root():
    if "user" not in session: return redirect(url_for("login_page"))
    u = session["user"]
    if u["role"] == "supervisor": return redirect(url_for("supervisor_dashboard"))
    return redirect(url_for("home"))


# ── Worker routes ─────────────────────────────────────────────

@app.get("/worker")
@login_req
def home():
    user = session["user"]
    if user["role"] == "supervisor": return redirect(url_for("supervisor_dashboard"))

    flash = session.pop("flash_message", None)

    # fetch current task
    tr   = pj(aget("/api/task/current"))
    task = tr.get("task")
    wfd  = tr.get("waiting_for_done", False)

    # fetch task list & logs
    from db import list_all_tasks
    all_tasks_raw = [t for t in list_all_tasks()
                     if t["assigned_to"] == user["username"] or t["assigned_to"] is None]

    # Sort: order_id groups together, within each order by row then col
    # Tasks with no order_id go last
    all_tasks = sorted(all_tasks_raw, key=lambda t: (
        0 if t.get("order_id") else 1,          # orders first
        t.get("order_id") or "zzz",              # group by order
        t.get("row_num", 0),                     # then row
        t.get("col_num", 0)                      # then shelf
    ))

    done_cnt  = sum(1 for t in all_tasks if t["status"] == "done")
    total_cnt = len(all_tasks)
    pct       = int(done_cnt / total_cnt * 100) if total_cnt else 0
    logs      = []

    order_just_completed = session.pop("order_just_completed", False)

    # build voice JS
    js = VOICE_JS_TPL
    js = js.replace("JINJA_WFD",       "true" if wfd else "false")
    js = js.replace("JINJA_LOC",       task["location"] if task else "")
    js = js.replace("JINJA_QTY",       str(task["products"]) if task and wfd else "0")
    js = js.replace("JINJA_ORDER_DONE","true" if order_just_completed else "false")

    html = WORKER_HTML
    return render_template_string(html,
        user=user, task=task, wfd=wfd, flash=flash,
        all_tasks=all_tasks, done_cnt=done_cnt, total_cnt=total_cnt,
        pct=pct, logs=[], js=js, tok=mk_csrf(),
        order_just_completed=order_just_completed)

@app.post("/check")
@login_req
def check_code():
    if not ok_csrf(): abort(400)
    code = request.form.get("confirm_code","").strip()
    r    = pj(apost("/api/task/check-code", {"code": code}))
    session["flash_message"] = r.get("message","")
    return redirect(url_for("home"))

@app.post("/done")
@login_req
def mark_done():
    if not ok_csrf(): abort(400)
    r = pj(apost("/api/task/done"))

    if r.get("order_complete"):
        # Whole order finished — set special flag so voice announces it
        session["order_just_completed"] = True
        session["flash_message"] = f"Order complete! All locations in this order are done."
    else:
        session["flash_message"] = r.get("message","")
    return redirect(url_for("home"))

@app.get("/api/poll-tasks")
@login_req
def poll_tasks():
    """
    Checks if there are pending tasks available for this worker.
    IMPORTANT: does NOT lock any task — just peeks at what is available.
    Called every 4 seconds from the waiting screen.
    """
    from db import get_conn
    user = session["user"]
    username = user["username"]
    with get_conn() as c:
        # Look for any pending task assigned to this worker or unassigned
        row = c.execute("""
            SELECT id, location, order_id FROM tasks
            WHERE status='pending' AND in_progress=0
              AND (assigned_to=? OR assigned_to IS NULL)
            ORDER BY priority DESC, row_num ASC, col_num ASC
            LIMIT 1
        """, (username,)).fetchone()
    if row:
        return jsonify({"has_task": True, "location": row["location"]})
    return jsonify({"has_task": False, "location": None})


# ── Supervisor routes ─────────────────────────────────────────

@app.get("/supervisor")
@login_req
@sup_only
def supervisor_dashboard():
    user  = session["user"]
    tab   = request.args.get("tab","tasks")
    flash = session.pop("flash_message", None)

    from db import (list_all_tasks, get_task_summary, get_recent_logs,
                    get_todays_worker_stats, list_all_users)

    tasks   = list_all_tasks()
    stats   = get_task_summary()
    logs    = get_recent_logs(100)
    wstats  = get_todays_worker_stats()
    workers = list_all_users()

    ml_demand  = []
    ml_workers = []
    if tab == "ml":
        r = mlget("/ml/demand-forecast")
        if r and r.ok:
            ml_demand = r.json().get("predictions",[])
        r = mlget("/ml/worker-performance")
        if r and r.ok:
            ml_workers = r.json().get("scores",[])

    html = SUP_HTML
    return render_template_string(html,
        user=user, tab=tab, flash=flash,
        tasks=tasks, stats=stats, logs=logs,
        wstats=wstats, workers=workers,
        ml_demand=ml_demand, ml_workers=ml_workers,
        tok=mk_csrf())

@app.post("/supervisor/reset")
@login_req
@sup_only
def reset_tasks():
    if not ok_csrf(): abort(400)
    from db import reset_all_tasks, log_action as db_log
    user = session["user"]
    reset_all_tasks()
    db_log(user["username"], user["role"], "reset_all", result="success")
    session["flash_message"] = "All tasks reset to pending."
    return redirect(url_for("supervisor_dashboard", tab="tasks"))

@app.post("/supervisor/create-task")
@login_req
@sup_only
def create_task():
    if not ok_csrf(): abort(400)
    import json as J
    priority    = int(request.form.get("priority","0"))
    assigned_to = request.form.get("assigned_to") or None
    order_id    = "ORD-" + __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime("%Y%m%d") + "-" + secrets.token_hex(2).upper()
    lj          = request.form.get("locations_json","").strip()
    if not lj:
        session["flash_message"] = "No locations provided."
        return redirect(url_for("supervisor_dashboard", tab="tasks"))
    try:
        entries = J.loads(lj)
    except Exception:
        session["flash_message"] = "Error reading order data."
        return redirect(url_for("supervisor_dashboard", tab="tasks"))
    # Create tasks directly in the database (avoids inter-process auth issues)
    from db import create_new_task, log_action as db_log
    user = session["user"]
    created, errors = 0, []
    for e in entries:
        loc  = (e.get("location") or "").strip().upper()
        code = (e.get("confirm_code") or "").strip()
        qty  = e.get("products")
        if not loc or not code or not qty:
            errors.append(f"Skipped incomplete row")
            continue
        try:
            create_new_task(loc, code, int(qty),
                            priority=priority,
                            assigned_to=assigned_to,
                            order_id=order_id)
            db_log(user["username"], user["role"], "create_task",
                   location=loc, result="created",
                   details=f"order={order_id}")
            created += 1
        except Exception as ex:
            errors.append(f"Failed {loc}: {str(ex)}")
    if errors:
        session["flash_message"] = f"Created {created} task(s). Issues: {'; '.join(errors)}"
    else:
        session["flash_message"] = f"Order {order_id[-8:]} created — {created} location(s) added."
    return redirect(url_for("supervisor_dashboard", tab="tasks"))

@app.post("/supervisor/delete-task/<int:tid>")
@login_req
@sup_only
def delete_task_route(tid):
    if not ok_csrf(): abort(400)
    from db import delete_task, log_action as db_log
    user = session["user"]
    delete_task(tid)
    db_log(user["username"], user["role"], "delete_task",
           task_id=tid, result="deleted")
    session["flash_message"] = "Task deleted."
    return redirect(url_for("supervisor_dashboard", tab="tasks"))

@app.post("/supervisor/create-worker")
@login_req
@sup_only
def create_worker():
    if not ok_csrf(): abort(400)
    from db import create_new_user, log_action as db_log
    user     = session["user"]
    username = request.form.get("username","").strip()
    password = request.form.get("password","")
    role     = request.form.get("role","worker")
    fullname = request.form.get("full_name","").strip()
    if not username or not password:
        session["flash_message"] = "Username and password are required."
        return redirect(url_for("supervisor_dashboard", tab="workers"))
    try:
        create_new_user(username, password, role, fullname)
        db_log(user["username"], user["role"], "create_user",
               result="created", details=username)
        session["flash_message"] = f"Account created for {fullname or username}."
    except Exception as ex:
        session["flash_message"] = f"Error: {str(ex)}"
    return redirect(url_for("supervisor_dashboard", tab="workers"))


if __name__ == "__main__":
    print(f"Frontend starting on port {PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False)

import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from weather_news import make_agent

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Weather News Agent</title>
<style>
:root{--bg:#f1f5f9;--card:#fff;--ink:#0f172a;--mute:#64748b;--line:#e2e8f0;--accent:#0ea5e9;--accent-ink:#fff;--code:#f8fafc;--grad:linear-gradient(135deg,#e0f2fe,#f1f5f9)}
@media(prefers-color-scheme:dark){:root{--bg:#0b1220;--card:#131c2e;--ink:#e2e8f0;--mute:#94a3b8;--line:#243049;--accent:#38bdf8;--accent-ink:#06121f;--code:#0e1626;--grad:linear-gradient(135deg,#10243d,#0b1220)}}
*{box-sizing:border-box}body{margin:0;background:var(--grad) fixed;color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh}
main{max-width:620px;margin:0 auto;padding:48px 16px 64px}
header{text-align:center;margin-bottom:28px}.logo{font-size:44px;line-height:1}
h1{margin:8px 0 4px;font-size:28px;letter-spacing:-.02em}header p{margin:0;color:var(--mute)}
form{display:flex;gap:8px;background:var(--card);padding:8px;border-radius:14px;border:1px solid var(--line);box-shadow:0 4px 20px #0001}
input{flex:1;min-width:0;border:0;background:none;color:inherit;font:inherit;padding:10px 12px;outline:none}
button{border:0;border-radius:10px;background:var(--accent);color:var(--accent-ink);font:inherit;font-weight:600;padding:10px 22px;cursor:pointer}
button:disabled{opacity:.55;cursor:wait}
.card{margin-top:18px;background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 4px 20px #0001;overflow:hidden;animation:in .25s ease}
@keyframes in{from{opacity:0;transform:translateY(6px)}}
.head{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid var(--line)}
.head b{font-size:18px}.tag{font-size:12px;color:var(--mute)}
.row{display:flex;gap:14px;padding:16px 20px;border-bottom:1px solid var(--line)}.row:last-child{border:0}
.ico{font-size:24px;width:32px;text-align:center}.k{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:700}
.v{margin-top:2px}
.trace{padding:14px 20px}.trace h3{margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--mute)}
code{display:block;background:var(--code);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font:13px ui-monospace,monospace;overflow-x:auto}
details{margin-top:10px}summary{cursor:pointer;color:var(--mute);font-size:14px}
pre{margin:8px 0 0;white-space:pre-wrap;font:13px/1.5 ui-monospace,monospace;color:var(--mute)}
.load{padding:28px;text-align:center;color:var(--mute)}.spin{display:inline-block;width:18px;height:18px;border:3px solid var(--line);border-top-color:var(--accent);border-radius:50%;animation:s .8s linear infinite;vertical-align:-4px;margin-right:8px}
@keyframes s{to{transform:rotate(360deg)}}
</style>
<main>
<header><div class=logo>&#127782;&#65039;</div><h1>Weather News Agent</h1><p>Today's weather headlines in three short lines</p></header>
<form id=f><input id=c placeholder="Enter a city, e.g. Chennai" required autofocus><button id=b>Ask</button></form>
<div id=out></div>
</main>
<script>
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const ICONS=['&#9729;&#65039;','&#127777;&#65039;','&#128161;'],NAMES=['Conditions','Temperature','Tip'];
function lines(t){return t.split('\\n').map(l=>l.replace(/^\\s*(?:[-*•]|\\d+[.)])\\s*/,'').trim()).filter(Boolean).slice(0,3).map((l,i)=>{
 const m=l.match(/^([A-Za-z ]{3,15}):\\s*(.*)$/);return {i,k:m?m[1]:NAMES[i]||'Note',v:m?m[2]:l}})}
f.onsubmit=async e=>{e.preventDefault();b.disabled=true;
 out.innerHTML='<div class="card load"><span class=spin></span>Searching the web&hellip;</div>';
 try{const r=await(await fetch('/ask',{method:'POST',body:JSON.stringify({city:c.value})})).json();
  out.innerHTML=`<div class=card><div class=head><b>${esc(c.value.trim())}</b><span class=tag>3-line reply</span></div>`+
   lines(r.reply).map(x=>`<div class=row><div class=ico>${ICONS[x.i]}</div><div><div class=k>${esc(x.k)}</div><div class=v>${esc(x.v)}</div></div></div>`).join('')+`</div>`}
 catch(x){out.innerHTML=`<div class="card load">Something went wrong: ${esc(x)}</div>`}
 b.disabled=false};
</script>
"""


async def ask(city):
    steps, reply = [], ""
    async for m in make_agent().run_stream(task=city):
        kind = type(m).__name__
        if kind == "ToolCallRequestEvent":
            steps.append({"kind": "Tool call", "text": "\n".join(f"{c.name}({c.arguments})" for c in m.content)})
        elif kind == "ToolCallExecutionEvent":
            steps.append({"kind": "Tool result", "text": "\n".join(r.content for r in m.content)})
        elif kind == "TextMessage" and m.source != "user":
            reply = m.content
    return {"steps": steps, "reply": reply}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send(200, "text/html", PAGE)

    def do_POST(self):
        city = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["city"].strip()
        try:
            self._send(200, "application/json", json.dumps(asyncio.run(ask(city))))
        except Exception as e:  # surface agent/search failures in the UI
            self._send(500, "application/json", json.dumps({"steps": [], "reply": f"Error: {e}"}))

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())


print("http://localhost:8000")
HTTPServer(("127.0.0.1", 8000), H).serve_forever()

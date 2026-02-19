#!/usr/bin/env python3
"""
SAUOS Web 可视化交互界面
"""

import os
import sys
import json
import time
import base64
import threading
import io
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, jsonify, request
from sauos import Automation, Screen
from sauos.ai.llm import OllamaClient, Message

# ==================== 配置 ====================
OLLAMA_URL = "http://10.10.0.20:11434"
TEXT_MODEL = "qwen3:8b"
VISION_MODEL = "moondream:1.8b"
HOST = "0.0.0.0"
PORT = 5678

# ==================== 全局实例 ====================
app = Flask(__name__)
auto = Automation()
screen = Screen()
text_llm = OllamaClient(base_url=OLLAMA_URL, model=TEXT_MODEL)
vision_llm = OllamaClient(base_url=OLLAMA_URL, model=VISION_MODEL)

# 任务状态
task_state = {
    "running": False,
    "task": "",
    "steps": [],
    "current_step": 0,
    "done": False,
    "error": None,
}
task_lock = threading.Lock()

SYSTEM_PROMPT = """你是SAUOS电脑自动化助手。根据屏幕描述和用户任务，返回下一步操作。
严格返回JSON格式，不要其他内容：
{"action":"click","x":100,"y":200,"reason":"点击按钮"}
{"action":"type","text":"hello","reason":"输入文本"}
{"action":"hotkey","keys":["command","space"],"reason":"打开Spotlight"}
{"action":"scroll","direction":"down","reason":"向下滚动"}
{"action":"wait","duration":2,"reason":"等待加载"}
{"action":"done","reason":"任务完成"}
macOS系统用command代替ctrl。每次只返回一个JSON。
/no_think"""


# ==================== 工具函数 ====================

def capture_base64():
    """截图并返回base64"""
    img = screen.capture_primary()
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), img


def analyze_with_vision(img):
    """视觉分析"""
    messages = [Message("user", "Describe this screenshot in detail in Chinese. Focus on visible UI elements, buttons, text fields, and their positions.")]
    response = vision_llm.chat_with_vision(messages, [img])
    return response.content


def plan_action(task, screen_desc, history=""):
    """规划操作"""
    prompt = f"屏幕状态：{screen_desc}\n\n任务：{task}"
    if history:
        prompt += f"\n\n已执行：{history}"
    prompt += "\n\n返回下一步JSON："
    messages = [Message("system", SYSTEM_PROMPT), Message("user", prompt)]
    response = text_llm.chat(messages, temperature=0.3)
    return response.content


def execute_action(action_json):
    """执行操作"""
    content = action_json.strip()
    if "```" in content:
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end == 0:
        return False, "无法解析"

    action = json.loads(content[start:end])
    act = action.get("action", "")
    reason = action.get("reason", "")

    if act == "done":
        return True, f"完成: {reason}"
    elif act == "click":
        x, y = action.get("x", 0), action.get("y", 0)
        auto.click((x, y))
        return False, f"点击 ({x},{y}) - {reason}"
    elif act == "type":
        auto.keyboard.write(action.get("text", ""))
        return False, f"输入 '{action.get('text','')}' - {reason}"
    elif act == "hotkey":
        keys = action.get("keys", [])
        auto.hotkey(*keys)
        return False, f"快捷键 {'+'.join(keys)} - {reason}"
    elif act == "scroll":
        d = action.get("direction", "down")
        (auto.scroll_up if d == "up" else auto.scroll_down)(5)
        return False, f"滚动{d} - {reason}"
    elif act == "wait":
        time.sleep(action.get("duration", 1))
        return False, f"等待 - {reason}"
    return False, f"未知: {act}"


def run_task_thread(task_desc):
    """后台执行任务"""
    global task_state
    with task_lock:
        task_state = {"running": True, "task": task_desc, "steps": [], "current_step": 0, "done": False, "error": None}

    history = []
    for step in range(30):
        if not task_state["running"]:
            break
        try:
            img_b64, img = capture_base64()
            desc = analyze_with_vision(img)
            action_json = plan_action(task_desc, desc, "\n".join(history[-5:]))
            done, msg = execute_action(action_json)

            step_info = {
                "step": step + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "screen_desc": desc[:120],
                "action_raw": action_json.strip()[:200],
                "result": msg,
                "screenshot": img_b64,
                "done": done,
            }
            with task_lock:
                task_state["steps"].append(step_info)
                task_state["current_step"] = step + 1
            history.append(f"Step{step+1}: {msg}")

            if done:
                with task_lock:
                    task_state["done"] = True
                    task_state["running"] = False
                break
            time.sleep(1.0)
        except Exception as e:
            with task_lock:
                task_state["steps"].append({"step": step+1, "time": datetime.now().strftime("%H:%M:%S"), "result": f"错误: {e}", "done": False, "screenshot": ""})
                task_state["error"] = str(e)
                task_state["running"] = False
            break

    with task_lock:
        task_state["running"] = False


# ==================== API 路由 ====================

@app.route("/api/screenshot")
def api_screenshot():
    img_b64, _ = capture_base64()
    return jsonify({"image": img_b64})


@app.route("/api/mouse")
def api_mouse():
    x, y = auto.mouse.position
    return jsonify({"x": x, "y": y})


@app.route("/api/window")
def api_window():
    w = auto.get_active_window()
    if w:
        return jsonify({"app": w.app_name, "title": w.title, "x": w.x, "y": w.y, "width": w.width, "height": w.height})
    return jsonify({"app": "", "title": ""})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    _, img = capture_base64()
    desc = analyze_with_vision(img)
    return jsonify({"description": desc})


@app.route("/api/click", methods=["POST"])
def api_click():
    data = request.json
    x, y = data.get("x", 0), data.get("y", 0)
    auto.click((x, y))
    return jsonify({"ok": True, "x": x, "y": y})


@app.route("/api/type", methods=["POST"])
def api_type():
    data = request.json
    auto.keyboard.write(data.get("text", ""))
    return jsonify({"ok": True})


@app.route("/api/hotkey", methods=["POST"])
def api_hotkey():
    data = request.json
    keys = data.get("keys", [])
    auto.hotkey(*keys)
    return jsonify({"ok": True})


@app.route("/api/task/start", methods=["POST"])
def api_task_start():
    if task_state["running"]:
        return jsonify({"ok": False, "error": "任务正在执行中"})
    data = request.json
    task_desc = data.get("task", "")
    if not task_desc:
        return jsonify({"ok": False, "error": "任务描述不能为空"})
    t = threading.Thread(target=run_task_thread, args=(task_desc,), daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/task/stop", methods=["POST"])
def api_task_stop():
    with task_lock:
        task_state["running"] = False
    return jsonify({"ok": True})


@app.route("/api/task/status")
def api_task_status():
    with task_lock:
        # 返回不含截图的轻量状态
        steps_lite = []
        for s in task_state["steps"]:
            steps_lite.append({k: v for k, v in s.items() if k != "screenshot"})
        return jsonify({
            "running": task_state["running"],
            "task": task_state["task"],
            "current_step": task_state["current_step"],
            "done": task_state["done"],
            "error": task_state["error"],
            "steps": steps_lite,
        })


@app.route("/api/task/step_screenshot/<int:step>")
def api_step_screenshot(step):
    with task_lock:
        for s in task_state["steps"]:
            if s.get("step") == step and s.get("screenshot"):
                return jsonify({"image": s["screenshot"]})
    return jsonify({"image": ""})


# ==================== 前端页面 ====================

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SAUOS - AI 电脑自动化</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0f1117;--card:#1a1d27;--border:#2a2d3a;--primary:#6366f1;--primary-hover:#818cf8;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--text:#e2e8f0;--text2:#94a3b8;--text3:#64748b}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.header{background:linear-gradient(135deg,#1e1b4b,#312e81);padding:16px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}
.header h1{font-size:20px;font-weight:700;letter-spacing:1px}
.header h1 span{color:var(--primary-hover)}
.header .status{display:flex;align-items:center;gap:12px;font-size:13px;color:var(--text2)}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.dot.on{background:var(--green);box-shadow:0 0 8px var(--green)}
.dot.off{background:var(--red)}
.main{display:grid;grid-template-columns:1fr 380px;height:calc(100vh - 57px)}
.left{padding:16px;display:flex;flex-direction:column;gap:12px;overflow:auto}
.right{border-left:1px solid var(--border);display:flex;flex-direction:column}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.card-head{padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600;color:var(--text2);display:flex;align-items:center;justify-content:space-between}
.card-body{padding:12px 14px}
.screen-box{flex:1;min-height:0}
.screen-box .card{height:100%;display:flex;flex-direction:column}
.screen-box .card-body{flex:1;display:flex;align-items:center;justify-content:center;padding:8px;position:relative}
.screen-box img{max-width:100%;max-height:100%;border-radius:6px;cursor:crosshair}
.screen-info{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.7);padding:4px 10px;border-radius:6px;font-size:11px;color:var(--text2)}
.task-input{display:flex;gap:8px}
.task-input input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-size:14px;outline:none;transition:border .2s}
.task-input input:focus{border-color:var(--primary)}
.btn{padding:10px 20px;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{background:var(--primary-hover)}
.btn-danger{background:var(--red);color:#fff}
.btn-sm{padding:6px 14px;font-size:12px}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn-ghost:hover{border-color:var(--primary);color:var(--primary-hover)}
.steps{flex:1;overflow-y:auto;padding:12px}
.step{padding:10px 12px;border-left:2px solid var(--border);margin-left:8px;margin-bottom:4px;font-size:13px;position:relative;cursor:pointer;transition:background .15s}
.step:hover{background:rgba(99,102,241,.08)}
.step::before{content:'';position:absolute;left:-6px;top:12px;width:10px;height:10px;border-radius:50%;background:var(--border)}
.step.done::before{background:var(--green)}
.step.running::before{background:var(--yellow);animation:pulse 1s infinite}
.step.error::before{background:var(--red)}
.step .step-head{display:flex;justify-content:space-between;margin-bottom:4px}
.step .step-num{color:var(--primary-hover);font-weight:600}
.step .step-time{color:var(--text3);font-size:11px}
.step .step-msg{color:var(--text2);font-size:12px;word-break:break-all}
.panel-head{padding:12px 16px;border-bottom:1px solid var(--border);font-size:14px;font-weight:600}
.tools{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px}
.tool-btn{display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px;background:var(--bg);border:1px solid var(--border);border-radius:8px;cursor:pointer;transition:all .15s;font-size:12px;color:var(--text2)}
.tool-btn:hover{border-color:var(--primary);color:var(--primary-hover);transform:translateY(-1px)}
.tool-btn .icon{font-size:22px}
.analysis{padding:12px;font-size:12px;color:var(--text2);line-height:1.6;max-height:200px;overflow-y:auto;border-top:1px solid var(--border)}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;align-items:center;justify-content:center}
.modal-overlay.show{display:flex}
.modal{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;max-width:90vw;max-height:90vh}
.modal img{max-width:100%;max-height:80vh;border-radius:8px}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.loading{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--primary);border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>

<div class="header">
  <h1><span>SAUOS</span> AI 电脑自动化</h1>
  <div class="status">
    <span><span class="dot on" id="dotOllama"></span> Ollama</span>
    <span id="modelInfo">qwen3:8b + moondream:1.8b</span>
  </div>
</div>

<div class="main">
  <div class="left">
    <!-- 任务输入 -->
    <div class="card">
      <div class="card-body">
        <div class="task-input">
          <input id="taskInput" placeholder="输入任务描述，如：打开Safari搜索Python教程" onkeydown="if(event.key==='Enter')startTask()">
          <button class="btn btn-primary" id="btnStart" onclick="startTask()">执行</button>
          <button class="btn btn-danger" id="btnStop" onclick="stopTask()" style="display:none">停止</button>
        </div>
      </div>
    </div>

    <!-- 屏幕预览 -->
    <div class="screen-box">
      <div class="card">
        <div class="card-head">
          <span>屏幕预览</span>
          <div style="display:flex;gap:6px">
            <button class="btn btn-sm btn-ghost" onclick="refreshScreen()">刷新</button>
            <button class="btn btn-sm btn-ghost" onclick="analyzeScreen()">AI分析</button>
          </div>
        </div>
        <div class="card-body">
          <img id="screenImg" src="" alt="屏幕截图" onclick="handleScreenClick(event)">
          <div class="screen-info" id="screenInfo">点击截图可触发点击操作</div>
        </div>
        <div class="analysis" id="analysisBox" style="display:none"></div>
      </div>
    </div>
  </div>

  <div class="right">
    <div class="panel-head" style="display:flex;justify-content:space-between;align-items:center">
      <span>控制面板</span>
      <span id="taskStatus" style="font-size:12px;color:var(--text3)">空闲</span>
    </div>

    <!-- 快捷工具 -->
    <div class="tools">
      <div class="tool-btn" onclick="quickAction('spotlight')"><span class="icon">🔍</span>Spotlight</div>
      <div class="tool-btn" onclick="quickAction('screenshot')"><span class="icon">📸</span>截图</div>
      <div class="tool-btn" onclick="quickAction('copy')"><span class="icon">📋</span>复制</div>
      <div class="tool-btn" onclick="quickAction('paste')"><span class="icon">📄</span>粘贴</div>
      <div class="tool-btn" onclick="quickAction('undo')"><span class="icon">↩️</span>撤销</div>
      <div class="tool-btn" onclick="quickAction('save')"><span class="icon">💾</span>保存</div>
      <div class="tool-btn" onclick="quickAction('scroll_up')"><span class="icon">⬆️</span>上滚</div>
      <div class="tool-btn" onclick="quickAction('scroll_down')"><span class="icon">⬇️</span>下滚</div>
    </div>

    <!-- 执行步骤 -->
    <div class="panel-head">执行日志</div>
    <div class="steps" id="stepsBox">
      <div style="text-align:center;color:var(--text3);padding:40px 0;font-size:13px">输入任务开始自动化</div>
    </div>
  </div>
</div>

<!-- 截图大图弹窗 -->
<div class="modal-overlay" id="modal" onclick="this.classList.remove('show')">
  <div class="modal" onclick="event.stopPropagation()">
    <img id="modalImg" src="">
  </div>
</div>

<script>
let polling = null;
let screenW = 1440, screenH = 900;

// 初始化
window.onload = () => { refreshScreen(); };

async function refreshScreen() {
  try {
    const r = await fetch('/api/screenshot');
    const d = await r.json();
    document.getElementById('screenImg').src = 'data:image/png;base64,' + d.image;
  } catch(e) { console.error(e); }
}

async function analyzeScreen() {
  const box = document.getElementById('analysisBox');
  box.style.display = 'block';
  box.innerHTML = '<div class="loading"></div> AI 分析中...';
  try {
    const r = await fetch('/api/analyze', {method:'POST'});
    const d = await r.json();
    box.textContent = d.description;
  } catch(e) { box.textContent = '分析失败: ' + e; }
}

function handleScreenClick(e) {
  const img = e.target;
  const rect = img.getBoundingClientRect();
  const scaleX = img.naturalWidth / rect.width;
  const scaleY = img.naturalHeight / rect.height;
  const x = Math.round((e.clientX - rect.left) * scaleX);
  const y = Math.round((e.clientY - rect.top) * scaleY);
  document.getElementById('screenInfo').textContent = `点击: (${x}, ${y})`;
  fetch('/api/click', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({x,y})});
  setTimeout(refreshScreen, 500);
}

async function startTask() {
  const input = document.getElementById('taskInput');
  const task = input.value.trim();
  if (!task) return;

  const r = await fetch('/api/task/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task})});
  const d = await r.json();
  if (!d.ok) { alert(d.error); return; }

  document.getElementById('btnStart').style.display = 'none';
  document.getElementById('btnStop').style.display = '';
  document.getElementById('taskStatus').textContent = '执行中...';
  document.getElementById('stepsBox').innerHTML = '';

  polling = setInterval(pollStatus, 1500);
}

async function stopTask() {
  await fetch('/api/task/stop', {method:'POST'});
  clearInterval(polling);
  document.getElementById('btnStart').style.display = '';
  document.getElementById('btnStop').style.display = 'none';
  document.getElementById('taskStatus').textContent = '已停止';
  refreshScreen();
}

async function pollStatus() {
  try {
    const r = await fetch('/api/task/status');
    const d = await r.json();

    const box = document.getElementById('stepsBox');
    box.innerHTML = '';
    d.steps.forEach(s => {
      const cls = s.done ? 'done' : (d.running && s.step === d.current_step ? 'running' : '');
      const div = document.createElement('div');
      div.className = 'step ' + cls;
      div.innerHTML = `<div class="step-head"><span class="step-num">Step ${s.step}</span><span class="step-time">${s.time||''}</span></div><div class="step-msg">${s.result||''}</div>`;
      div.onclick = () => showStepScreenshot(s.step);
      box.appendChild(div);
    });
    box.scrollTop = box.scrollHeight;

    if (!d.running) {
      clearInterval(polling);
      document.getElementById('btnStart').style.display = '';
      document.getElementById('btnStop').style.display = 'none';
      document.getElementById('taskStatus').textContent = d.done ? '已完成' : (d.error ? '出错' : '已停止');
      refreshScreen();
    }
  } catch(e) { console.error(e); }
}

async function showStepScreenshot(step) {
  const r = await fetch('/api/task/step_screenshot/' + step);
  const d = await r.json();
  if (d.image) {
    document.getElementById('modalImg').src = 'data:image/png;base64,' + d.image;
    document.getElementById('modal').classList.add('show');
  }
}

async function quickAction(action) {
  const map = {
    spotlight: {url:'/api/hotkey', body:{keys:['command','space']}},
    screenshot: {url:'/api/screenshot', body:null},
    copy: {url:'/api/hotkey', body:{keys:['command','c']}},
    paste: {url:'/api/hotkey', body:{keys:['command','v']}},
    undo: {url:'/api/hotkey', body:{keys:['command','z']}},
    save: {url:'/api/hotkey', body:{keys:['command','s']}},
    scroll_up: {url:'/api/hotkey', body:{keys:['pageup']}},
    scroll_down: {url:'/api/hotkey', body:{keys:['pagedown']}},
  };
  const a = map[action];
  if (!a) return;
  if (a.body) {
    await fetch(a.url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(a.body)});
  } else {
    await fetch(a.url);
  }
  setTimeout(refreshScreen, 300);
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


# ==================== 启动 ====================

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════╗
║         SAUOS - AI 电脑自动化 Web 界面           ║
║                                                  ║
║  打开浏览器访问: http://localhost:{PORT}             ║
║                                                  ║
║  Ollama: {OLLAMA_URL:<39s} ║
║  文本模型: {TEXT_MODEL:<37s} ║
║  视觉模型: {VISION_MODEL:<37s} ║
╚══════════════════════════════════════════════════╝
""")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)

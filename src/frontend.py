"""
Interactive CUSB Chatbot Frontend - Enhanced UI
"""

CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CUSB AI Assistant</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  
  :root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --bg: #f8fafc;
    --chat-bg: #ffffff;
    --user-bg: #2563eb;
    --user-text: #ffffff;
    --bot-bg: #f1f5f9;
    --bot-text: #1e293b;
    --border: #e2e8f0;
    --text: #1e293b;
    --subtext: #64748b;
  }

  [data-theme="dark"] {
    --bg: #0f172a;
    --chat-bg: #1e293b;
    --user-bg: #3b82f6;
    --bot-bg: #334155;
    --bot-text: #f1f5f9;
    --border: #475569;
    --text: #f1f5f9;
    --subtext: #94a3b8;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    transition: background 0.3s, color 0.3s;
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  .header {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    color: white;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  }

  .header-icon {
    font-size: 28px;
    animation: bounce 2s infinite;
  }

  @keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
  }

  .header-title h1 { font-size: 18px; font-weight: 600; }
  .header-title p { font-size: 12px; opacity: 0.9; }

  .theme-toggle {
    margin-left: auto;
    background: rgba(255,255,255,0.2);
    border: none;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    color: white;
    font-size: 20px;
    transition: all 0.3s;
  }

  .theme-toggle:hover { background: rgba(255,255,255,0.3); transform: scale(1.05); }

  #chatContainer {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
  }

  .welcome {
    text-align: center;
    padding: 40px 20px;
    animation: fadeIn 0.5s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .welcome-icon { font-size: 60px; margin-bottom: 16px; }

  .suggestions {
    display: flex; flex-wrap: wrap; gap: 8px;
    justify-content: center; margin-top: 20px;
  }

  .suggestion-btn {
    background: var(--chat-bg);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 13px;
    color: var(--text);
    cursor: pointer;
    transition: all 0.3s;
  }

  .suggestion-btn:hover {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }

  .message {
    display: flex;
    gap: 10px;
    max-width: 85%;
    animation: slideIn 0.3s ease;
  }

  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .message.user { align-self: flex-end; flex-direction: row-reverse; animation: slideInRight 0.3s ease; }
  .message.user @keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }
  .message.bot { align-self: flex-start; }

  .msg-avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; flex-shrink: 0;
  }
  .message.user .msg-avatar { background: var(--user-bg); color: white; }
  .message.bot .msg-avatar { background: var(--border); color: var(--subtext); }

  .msg-bubble {
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.6;
    word-wrap: break-word;
  }
  .message.user .msg-bubble {
    background: var(--user-bg);
    color: var(--user-text);
    border-bottom-right-radius: 4px;
  }
  .message.bot .msg-bubble {
    background: var(--bot-bg);
    color: var(--bot-text);
    border-bottom-left-radius: 4px;
  }

  .typing {
    display: flex; gap: 4px; padding: 4px 0;
  }
  .typing span {
    width: 8px; height: 8px;
    background: var(--subtext);
    border-radius: 50%;
    animation: bounce 1.4s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }

  .input-area {
    padding: 16px 20px;
    background: var(--chat-bg);
    border-top: 1px solid var(--border);
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
  }

  .input-wrapper {
    display: flex;
    gap: 10px;
  }

  #queryInput {
    flex: 1;
    padding: 12px 16px;
    border: 2px solid var(--border);
    border-radius: 12px;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
    outline: none;
    transition: border-color 0.3s, box-shadow 0.3s;
  }

  #queryInput:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  #sendBtn {
    width: 48px; height: 48px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.3s;
  }

  #sendBtn:hover:not(:disabled) {
    background: var(--primary-dark);
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
  }

  #sendBtn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }

  .footer {
    text-align: center;
    padding: 8px;
    font-size: 11px;
    color: var(--subtext);
  }

  #status {
    text-align: center;
    padding: 8px;
    font-size: 12px;
    color: var(--subtext);
  }

  #chatContainer::-webkit-scrollbar { width: 6px; }
  #chatContainer::-webkit-scrollbar-track { background: transparent; }
  #chatContainer::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  #chatContainer::-webkit-scrollbar-thumb:hover { background: var(--subtext); }

  @media (max-width: 640px) {
    .message { max-width: 90%; }
    .suggestions { gap: 6px; }
    .suggestion-btn { font-size: 12px; padding: 6px 12px; }
  }
</style>
</head>
<body>

<div class="header">
  <div class="header-icon">🎓</div>
  <div class="header-title">
    <h1>CUSB AI Assistant</h1>
    <p>Central University of South Bihar</p>
  </div>
  <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">🌙</button>
</div>

<div id="chatContainer">
  <div class="welcome">
    <div class="welcome-icon">🎓</div>
    <h2>Welcome to CUSB AI Assistant</h2>
    <p style="color: var(--subtext); margin: 10px 0;">Ask me anything about CUSB courses, fees, admissions & more!</p>
    <div class="suggestions">
      <button class="suggestion-btn" onclick="ask('CUSB kya hai?')">CUSB kya hai?</button>
      <button class="suggestion-btn" onclick="ask('Hostel fee kitni hai?')">Hostel fee</button>
      <button class="suggestion-btn" onclick="ask('M.Sc Statistics ki fees?')">M.Sc Statistics fees</button>
      <button class="suggestion-btn" onclick="ask('Admission process?')">Admission process</button>
      <button class="suggestion-btn" onclick="ask('How many students in CUSB?')">Total students</button>
      <button class="suggestion-btn" onclick="ask('NAAC grade?')">NAAC grade</button>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="input-wrapper">
    <input type="text" id="queryInput" placeholder="Type your question here..." onkeypress="if(event.key==='Enter') sendQuery()">
    <button id="sendBtn" onclick="sendQuery()">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
      </svg>
    </button>
  </div>
</div>

<div id="status"></div>
<div class="footer">Powered by RAG + LLM | CUSB Knowledge Base v2.0</div>

<script>
const API_URL = '/api/query';
let isProcessing = false;

const themeToggle = document.getElementById('themeToggle');
let isDark = false;

themeToggle.addEventListener('click', () => {
  isDark = !isDark;
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  themeToggle.textContent = isDark ? '☀️' : '🌙';
});

function loadHistory() {
  const history = localStorage.getItem('cusb_chat_history');
  if (history) {
    const messages = JSON.parse(history);
    messages.forEach(msg => {
      const welcome = document.getElementById('welcome');
      if (welcome) welcome.style.display = 'none';
      addMessage(msg.role, msg.text);
    });
  }
}

function saveHistory(role, text) {
  let history = JSON.parse(localStorage.getItem('cusb_chat_history') || '[]');
  history.push({ role, text, time: Date.now() });
  if (history.length > 50) history = history.slice(-50);
  localStorage.setItem('cusb_chat_history', JSON.stringify(history));
}

function ask(q) {
  document.getElementById('queryInput').value = q;
  sendQuery();
}

function addMessage(role, text) {
  const container = document.getElementById('chatContainer');
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.style.display = 'none';
  
  const msg = document.createElement('div');
  msg.className = 'message ' + role;
  
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = role === 'user' ? 'U' : 'AI';
  
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = text;
  
  msg.appendChild(avatar);
  msg.appendChild(bubble);
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function addTyping() {
  const container = document.getElementById('chatContainer');
  const msg = document.createElement('div');
  msg.className = 'message bot';
  msg.id = 'typingMsg';
  
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = 'AI';
  
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
  
  msg.appendChild(avatar);
  msg.appendChild(bubble);
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingMsg');
  if (el) el.remove();
}

function showStatus(msg) {
  document.getElementById('status').textContent = msg;
}

async function sendQuery() {
  const input = document.getElementById('queryInput');
  const question = input.value.trim();
  
  if (!question || isProcessing) return;
  
  isProcessing = true;
  document.getElementById('sendBtn').disabled = true;
  
  showStatus('🤔 Thinking...');
  addMessage('user', question);
  saveHistory('user', question);
  input.value = '';
  
  addTyping();
  
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question})
    });
    
    showStatus('✓ Response received');
    
    if (!res.ok) throw new Error('HTTP ' + res.status);
    
    const data = await res.json();
    removeTyping();
    addMessage('bot', data.answer || 'No answer');
    saveHistory('bot', data.answer);
    showStatus('');
    
  } catch (err) {
    console.error(err);
    removeTyping();
    addMessage('bot', 'Error: ' + err.message);
    showStatus('❌ Error occurred');
  }
  
  isProcessing = false;
  document.getElementById('sendBtn').disabled = false;
  input.focus();
}

loadHistory();
document.getElementById('queryInput').focus();
console.log('CUSB Interactive Chatbot loaded!');
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("Interactive chatbot ready")
    print(f"Size: {len(CHAT_HTML)} chars")

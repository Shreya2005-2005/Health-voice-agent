/* ── State ──────────────────────────────────────────────────────── */
let sessionId   = null;
let userName    = '';
let isRecording = false;
let isBusy      = false;

// Web Audio capture state
let audioCtx      = null;
let mediaStream   = null;
let scriptNode    = null;
let pcmChunks     = [];
let nativeSR      = 44100;

const TARGET_SR = 16000;   // Whisper expects 16 kHz

/* ── Session Start ──────────────────────────────────────────────── */
async function startSession() {
  const nameInput = document.getElementById('name-input');
  const name = nameInput.value.trim() || 'Friend';
  setStatus('thinking', 'Starting…');

  try {
    const fd = new FormData();
    fd.append('name', name);
    const res = await fetch('/api/session/start', { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    sessionId = data.session_id;
    userName  = data.user;

    document.getElementById('user-name-label').textContent = userName;
    document.getElementById('setup-screen').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');

    addMessage('bot', data.message);
    setStatus('ready', 'Ready');
    speak(data.message);
  } catch (e) {
    alert('Could not connect to the server.\nMake sure app.py is running.\n\n' + e);
    setStatus('ready', 'Ready');
  }
}

document.getElementById('name-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') startSession();
});

/* ── Recording (Web Audio → PCM → WAV) ─────────────────────────── */
async function toggleRecording() {
  if (isBusy) return;
  if (isRecording) { stopRecording(); return; }
  await startRecording();
}

async function startRecording() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
  } catch {
    alert('Microphone access denied. Please allow microphone access and try again.');
    return;
  }

  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  nativeSR  = audioCtx.sampleRate;
  pcmChunks = [];

  const source = audioCtx.createMediaStreamSource(mediaStream);

  // ScriptProcessor works in all browsers (deprecated but functional)
  scriptNode = audioCtx.createScriptProcessor(4096, 1, 1);
  scriptNode.onaudioprocess = (e) => {
    const data = e.inputBuffer.getChannelData(0);
    pcmChunks.push(new Float32Array(data));
  };

  source.connect(scriptNode);
  scriptNode.connect(audioCtx.destination);  // must connect to dest to fire

  isRecording = true;
  document.getElementById('mic-btn').classList.add('recording');
  document.getElementById('mic-icon').classList.add('hidden');
  document.getElementById('stop-icon').classList.remove('hidden');
  document.getElementById('recording-wave').classList.remove('hidden');
  setStatus('listening', 'Listening…');
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  // Tear down audio graph
  if (scriptNode)   { scriptNode.disconnect(); scriptNode = null; }
  if (mediaStream)  { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }
  if (audioCtx)     { audioCtx.close(); audioCtx = null; }

  document.getElementById('mic-btn').classList.remove('recording');
  document.getElementById('mic-icon').classList.remove('hidden');
  document.getElementById('stop-icon').classList.add('hidden');
  document.getElementById('recording-wave').classList.add('hidden');

  // Build WAV from captured PCM
  const wavBlob = buildWavBlob(pcmChunks, nativeSR, TARGET_SR);
  pcmChunks = [];
  sendAudio(wavBlob);
}

/* ── WAV helpers ────────────────────────────────────────────────── */
function buildWavBlob(chunks, fromSR, toSR) {
  // Merge Float32 chunks
  const totalLen = chunks.reduce((n, c) => n + c.length, 0);
  const merged   = new Float32Array(totalLen);
  let offset = 0;
  for (const c of chunks) { merged.set(c, offset); offset += c.length; }

  // Simple nearest-neighbour downsample
  const ratio    = fromSR / toSR;
  const outLen   = Math.floor(merged.length / ratio);
  const resampled = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    resampled[i] = merged[Math.floor(i * ratio)];
  }

  // Encode as 16-bit PCM WAV
  const buf  = new ArrayBuffer(44 + outLen * 2);
  const view = new DataView(buf);

  const wr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
  wr(0, 'RIFF');
  view.setUint32(4,  36 + outLen * 2, true);
  wr(8, 'WAVE');
  wr(12, 'fmt ');
  view.setUint32(16, 16,      true);   // chunk size
  view.setUint16(20, 1,       true);   // PCM
  view.setUint16(22, 1,       true);   // mono
  view.setUint32(24, toSR,    true);   // sample rate
  view.setUint32(28, toSR*2,  true);   // byte rate
  view.setUint16(32, 2,       true);   // block align
  view.setUint16(34, 16,      true);   // bits per sample
  wr(36, 'data');
  view.setUint32(40, outLen * 2, true);

  let off = 44;
  for (let i = 0; i < outLen; i++) {
    const s = Math.max(-1, Math.min(1, resampled[i]));
    view.setInt16(off, s < 0 ? s * 32768 : s * 32767, true);
    off += 2;
  }

  return new Blob([buf], { type: 'audio/wav' });
}

/* ── Send Audio ─────────────────────────────────────────────────── */
async function sendAudio(blob) {
  if (!sessionId) return;
  if (blob.size < 200) {
    addMessage('bot', 'The recording was too short. Please try again.');
    return;
  }

  isBusy = true;
  setStatus('thinking', 'Transcribing…');
  showTyping(true);

  try {
    const fd = new FormData();
    fd.append('session_id', sessionId);
    fd.append('audio', blob, 'audio.wav');

    const res = await fetch('/api/chat/audio', { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    if (data.transcription) addMessage('user', data.transcription);
    handleResponse(data);
  } catch (e) {
    showTyping(false);
    addMessage('bot', '⚠️ Error processing audio. Please try the text box instead.', false, true);
    setStatus('ready', 'Ready');
    console.error(e);
  } finally {
    isBusy = false;
  }
}

/* ── Send Text ──────────────────────────────────────────────────── */
async function sendText() {
  const input = document.getElementById('text-input');
  const text  = input.value.trim();
  if (!text || !sessionId || isBusy) return;

  input.value = '';
  isBusy = true;
  addMessage('user', text);
  setStatus('thinking', 'Thinking…');
  showTyping(true);

  try {
    const fd = new FormData();
    fd.append('session_id', sessionId);
    fd.append('text', text);

    const res = await fetch('/api/chat/text', { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    handleResponse(data);
  } catch (e) {
    showTyping(false);
    addMessage('bot', '⚠️ Error sending message. Please try again.', false, true);
    setStatus('ready', 'Ready');
    console.error(e);
  } finally {
    isBusy = false;
  }
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
}

/* ── Strip markdown so responses render as clean plain text ─────── */
function stripMarkdown(text) {
  return text
    .replace(/#{1,6}\s*/g, '')           // headings
    .replace(/\*\*(.+?)\*\*/g, '$1')     // bold
    .replace(/\*(.+?)\*/g, '$1')         // italic
    .replace(/`(.+?)`/g, '$1')           // inline code
    .replace(/^[\s]*[-*•]\s+/gm, '• ')  // bullet points → simple bullet
    .replace(/^\s*\d+\.\s+/gm, '')       // numbered lists
    .replace(/\n{3,}/g, '\n\n')          // excessive blank lines
    .trim();
}

/* ── Handle Response ────────────────────────────────────────────── */
function handleResponse(data) {
  showTyping(false);
  const clean = stripMarkdown(data.message);
  const emergency = /emergency|call emergency|hospital immediately/i.test(clean);
  addMessage('bot', clean, emergency);
  speak(clean);

  if (data.is_done) {
    setStatus('done', 'Session done');
    setTimeout(() => {
      addMessage('bot', '💬 Start a new conversation anytime using the + button above.');
    }, 600);
  } else {
    setStatus('ready', 'Ready');
  }
}

/* ── New Conversation ───────────────────────────────────────────── */
async function newConversation() {
  if (isBusy || !sessionId) return;
  isBusy = true;
  showTyping(true);
  setStatus('thinking', 'Restarting…');

  try {
    const fd = new FormData();
    fd.append('session_id', sessionId);
    const res  = await fetch('/api/session/restart', { method: 'POST', body: fd });
    const data = await res.json();
    showTyping(false);
    document.getElementById('messages').innerHTML = '';
    addMessage('bot', data.message);
    speak(data.message);
    setStatus('ready', 'Ready');
  } catch {
    showTyping(false);
    setStatus('ready', 'Ready');
  } finally {
    isBusy = false;
  }
}

/* ── UI Helpers ─────────────────────────────────────────────────── */
function addMessage(role, text, emergency = false) {
  const messages = document.getElementById('messages');

  const wrapper = document.createElement('div');
  wrapper.className = `msg ${role}`;

  const avatar  = document.createElement('div');
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === 'bot' ? '🩺' : '🙂';

  const content = document.createElement('div');

  const bubble  = document.createElement('div');
  bubble.className = `bubble ${role}${emergency ? ' emergency' : ''}`;
  bubble.textContent = text;

  const time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  content.appendChild(bubble);
  content.appendChild(time);
  wrapper.appendChild(avatar);
  wrapper.appendChild(content);
  messages.appendChild(wrapper);

  const chatArea = document.getElementById('chat-area');
  chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping(show) {
  document.getElementById('typing-indicator').classList.toggle('hidden', !show);
  if (show) {
    const chatArea = document.getElementById('chat-area');
    chatArea.scrollTop = chatArea.scrollHeight;
  }
}

function setStatus(type, label) {
  document.getElementById('status-pill').className = `status-pill status-${type}`;
  document.getElementById('status-text').textContent = label;
}

/* ── Text-to-Speech (browser) ───────────────────────────────────── */
let preferredVoice = null;

function loadVoices() {
  const voices = speechSynthesis.getVoices();
  if (!voices.length) return;
  preferredVoice =
    voices.find(v => /zira|microsoft zira/i.test(v.name)) ||
    voices.find(v => /female/i.test(v.name) && /en/i.test(v.lang)) ||
    voices.find(v => /en[-_]US/i.test(v.lang)) ||
    voices[0];
}
speechSynthesis.onvoiceschanged = loadVoices;
loadVoices();

function speak(text) {
  if (document.getElementById('mute-toggle').checked || !text) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate   = 0.92;
  u.pitch  = 1.0;
  u.volume = 1.0;
  if (preferredVoice) u.voice = preferredVoice;
  u.onstart = () => setStatus('speaking', 'Speaking…');
  u.onend   = () => setStatus('ready',    'Ready');
  u.onerror = () => setStatus('ready',    'Ready');
  speechSynthesis.speak(u);
}

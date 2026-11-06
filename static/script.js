/**
 * VERIVIEW AI // Cyber Fraud & Fake Review Radar HUD Client Script
 * Cyberpunk HUD, Web Audio Synthesizer, 3D Canvas Starfield & Fraud Telemetry
 */

// --- AUDIO SYNTHESIZER ---
let audioCtx = null;
let soundEnabled = false;

function initAudio() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContext();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function playBeep(freq = 880, type = 'sine', duration = 0.05, gainVal = 0.05) {
  if (!soundEnabled) return;
  try {
    initAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(gainVal, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) {}
}

function playScanSound() {
  if (!soundEnabled) return;
  try {
    initAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(350, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1500, audioCtx.currentTime + 0.16);
    gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.16);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.16);
  } catch (e) {}
}

// --- LOGGING ENGINE ---
function addLog(tag, msg, type = 'normal') {
  const container = document.getElementById('logContent');
  if (!container) return;
  const line = document.createElement('div');
  line.className = 'log-line';
  const time = new Date().toISOString().substring(11, 19);
  
  let valClass = '';
  if (type === 'ok') valClass = 'ok';
  else if (type === 'err') valClass = 'err';

  line.innerHTML = `<span class="ts">[${time}]</span> <span class="tag">${tag}</span> <span class="${valClass}">${msg}</span>`;
  container.appendChild(line);
  container.scrollTop = container.scrollHeight;
}

// --- STARFIELD CANVAS ---
function initStarfield() {
  const canvas = document.getElementById('spaceCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w = canvas.width = window.innerWidth;
  let h = canvas.height = window.innerHeight;

  window.addEventListener('resize', () => {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  });

  const stars = [];
  const STAR_COUNT = 90;
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push({
      x: Math.random() * w,
      y: Math.random() * h,
      size: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.7 + 0.3,
      speed: Math.random() * 0.2 + 0.05
    });
  }

  function render() {
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < stars.length; i++) {
      const s = stars[i];
      s.y -= s.speed;
      if (s.y < 0) s.y = h;

      ctx.fillStyle = `rgba(255, 32, 78, ${s.alpha * 0.4})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
      ctx.fill();

      if (i % 3 === 0) {
        ctx.fillStyle = `rgba(0, 229, 255, ${s.alpha * 0.5})`;
        ctx.fillRect(s.x + 2, s.y, 1, 1);
      }
    }
    requestAnimationFrame(render);
  }
  render();
}

// --- SYSTEM BOOT SEQUENCE ---
function runBootSequence() {
  const boot = document.getElementById('boot');
  const bar = document.getElementById('bootBar');
  const text = document.getElementById('bootText');
  if (!boot) return;

  const steps = [
    { pct: 25, txt: "INITIALIZING FRAUD SENSORS..." },
    { pct: 55, txt: "LOADING TF-IDF VECTOR MATRICES..." },
    { pct: 85, txt: "SYNCHRONIZING SIGMOID WEIGHTS..." },
    { pct: 100, txt: "DECEPTION RADAR READY." }
  ];

  let current = 0;
  const interval = setInterval(() => {
    if (current < steps.length) {
      bar.style.width = steps[current].pct + '%';
      text.innerText = steps[current].txt;
      playBeep(620 + current * 120, 'sine', 0.03, 0.03);
      current++;
    } else {
      clearInterval(interval);
      setTimeout(() => {
        boot.classList.add('off');
        addLog("KERNEL", "VeriView AI Radar initialized successfully.", "ok");
      }, 350);
    }
  }, 220);
}

// --- TAB SWITCHING ---
function initTabs() {
  const tabs = document.querySelectorAll('.hud-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      playBeep(920, 'sine', 0.04, 0.04);
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetId = tab.getAttribute('data-tab');
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');

      addLog("NAV", `Switched radar deck to [${targetId.toUpperCase()}]`);
    });
  });
}

// --- MODALITY SWITCHING ---
let activeModality = 'direct-text';

function initModalities() {
  const btns = document.querySelectorAll('.modality-btn');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      playBeep(840, 'sine', 0.03, 0.03);
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      activeModality = btn.getAttribute('data-modality');
      document.getElementById('pane-direct-text').hidden = (activeModality !== 'direct-text');
      document.getElementById('pane-file-upload').hidden = (activeModality !== 'file-upload');
      document.getElementById('pane-ocr-image').hidden = (activeModality !== 'ocr-image');

      addLog("INGEST", `Modality set to: ${activeModality.toUpperCase()}`);
    });
  });

  // File Upload Listeners
  const fileInput = document.getElementById('fileInput');
  const fileDropZone = document.getElementById('fileDropZone');
  fileDropZone.onclick = () => fileInput.click();
  fileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
      document.getElementById('fileUploadName').style.display = 'inline-flex';
      document.getElementById('selectedFileName').innerText = file.name;
      addLog("FILE", `Loaded TXT review file: ${file.name} (${file.size} bytes)`);
    }
  };

  // OCR Image Listeners
  const imageInput = document.getElementById('imageInput');
  const imageDropZone = document.getElementById('imageDropZone');
  imageDropZone.onclick = () => imageInput.click();
  imageInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
      document.getElementById('imageUploadName').style.display = 'inline-flex';
      document.getElementById('selectedImageName').innerText = file.name;
      addLog("OCR", `Loaded screenshot image for Pytesseract parsing: ${file.name}`);
    }
  };
}

// --- FETCH ARCHITECTURE TELEMETRY ---
async function fetchArchitecture() {
  try {
    const res = await fetch('/api/model/architecture');
    const data = await res.json();
    if (data.status === 'success') {
      renderFraudAtlas(data);
      if (data.model_overview) {
        document.getElementById('topAccuracy').innerText = `${data.model_overview.training_accuracy}%`;
      }
      addLog("MODEL", "Loaded TF-IDF weights and linguistic fraud markers atlas.", "ok");
    }
  } catch (e) {
    console.error("Architecture fetch error:", e);
    addLog("MODEL", `Failed retrieving model architecture: ${e.message}`, "err");
  }
}

function renderFraudAtlas(data) {
  const fraudTbody = document.getElementById('fraudStemsTable');
  const authTbody = document.getElementById('authenticStemsTable');
  if (!fraudTbody || !authTbody) return;

  fraudTbody.innerHTML = '';
  authTbody.innerHTML = '';

  (data.top_fraud_markers || []).forEach(m => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="token-chip fake">${m.stem}</span></td>
      <td style="font-family:'Share Tech Mono',monospace; color:var(--red); font-weight:700;">+${m.coefficient}</td>
      <td style="color:var(--red);">Synthetic / Hyperbolic</td>
    `;
    fraudTbody.appendChild(tr);
  });

  (data.top_authentic_markers || []).forEach(m => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="token-chip original">${m.stem}</span></td>
      <td style="font-family:'Share Tech Mono',monospace; color:var(--emerald); font-weight:700;">${m.coefficient}</td>
      <td style="color:var(--emerald);">Balanced / Human Experience</td>
    `;
    authTbody.appendChild(tr);
  });
}

// --- AUDIT INFERENCE EXECUTION ---
async function runAudit() {
  playScanSound();
  const btn = document.getElementById('btnAuditReview');
  const origHtml = btn.innerHTML;
  btn.innerHTML = `<span>SCANNING TENSORS...</span> <i>âŒ›</i>`;
  btn.disabled = true;

  document.getElementById('radarStatusBadge').innerText = "RESOLVING PROBABILITIES...";

  try {
    let response;

    if (activeModality === 'direct-text') {
      const text = document.getElementById('reviewText').value.trim();
      if (!text) {
        alert("Please enter review text to analyze.");
        btn.innerHTML = origHtml;
        btn.disabled = false;
        return;
      }
      addLog("INFERENCE", `Submitting direct text stream: "${text.substring(0, 40)}..."`);
      response = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text_input: text })
      });
    } else if (activeModality === 'file-upload') {
      const fileInput = document.getElementById('fileInput');
      if (!fileInput.files[0]) {
        alert("Please select a .txt file first.");
        btn.innerHTML = origHtml;
        btn.disabled = false;
        return;
      }
      const formData = new FormData();
      formData.append('file_input', fileInput.files[0]);
      addLog("INFERENCE", `Submitting file stream: ${fileInput.files[0].name}`);
      response = await fetch('/predict', {
        method: 'POST',
        body: formData
      });
    } else if (activeModality === 'ocr-image') {
      const imageInput = document.getElementById('imageInput');
      if (!imageInput.files[0]) {
        alert("Please select a screenshot image first.");
        btn.innerHTML = origHtml;
        btn.disabled = false;
        return;
      }
      const formData = new FormData();
      formData.append('image_input', imageInput.files[0]);
      addLog("INFERENCE", `Submitting screenshot image for Pytesseract OCR pipeline.`);
      response = await fetch('/predict', {
        method: 'POST',
        body: formData
      });
    }

    const data = await response.json();
    if (data.status === 'error') {
      alert(data.error);
      addLog("ERROR", data.error, "err");
      return;
    }

    renderAuditResult(data);
    addLog("RESULT", `Verdict: [${data.prediction}] - Threat: ${data.deception_threat_score}% in ${data.inference_time_ms}ms`, data.is_fake ? "err" : "ok");
    document.getElementById('topLatency').innerText = `${data.inference_time_ms}ms`;
  } catch (err) {
    console.error("Audit error:", err);
    alert("Inference server communication error: " + err.message);
    addLog("ERROR", err.message, "err");
  } finally {
    btn.innerHTML = origHtml;
    btn.disabled = false;
  }
}

function renderAuditResult(data) {
  document.getElementById('radar-idle').hidden = true;
  const resultArea = document.getElementById('radar-result');
  resultArea.hidden = false;

  const banner = document.getElementById('verdictBanner');
  const verdictBadge = document.getElementById('verdictBadge');
  const predText = document.getElementById('predictionResultText');
  const scoreText = document.getElementById('deceptionScoreText');
  const gauge = document.getElementById('deceptionGauge');
  const threatTier = document.getElementById('threatTierText');

  predText.innerText = data.prediction;
  scoreText.innerText = `${data.deception_threat_score}% DECEPTION THREAT`;
  gauge.style.width = `${Math.min(data.deception_threat_score, 100)}%`;
  threatTier.innerText = (data.threat_tier || 'FRAUD RADAR VERDICT').replace(/_/g, ' ');
  verdictBadge.innerText = data.verdict_badge || (data.is_fake ? 'FAKE REVIEW' : 'GENUINE');

  if (data.is_fake) {
    banner.className = 'verdict-banner fake';
    verdictBadge.style.borderColor = 'var(--red)';
    verdictBadge.style.color = 'var(--red)';
    gauge.style.background = 'var(--red)';
    gauge.style.boxShadow = '0 0 10px var(--red)';
  } else {
    banner.className = 'verdict-banner original';
    verdictBadge.style.borderColor = 'var(--emerald)';
    verdictBadge.style.color = 'var(--emerald)';
    gauge.style.background = 'var(--emerald)';
    gauge.style.boxShadow = '0 0 10px var(--emerald)';
  }

  // Probability distribution
  if (data.probability_distribution) {
    const pFake = data.probability_distribution.fake;
    const pOrig = data.probability_distribution.original;
    document.getElementById('probFakeVal').innerText = `${pFake.toFixed(1)}%`;
    document.getElementById('probFakeFill').style.width = `${pFake}%`;
    document.getElementById('probOrigVal').innerText = `${pOrig.toFixed(1)}%`;
    document.getElementById('probOrigFill').style.width = `${pOrig}%`;
  }

  // Token attributions
  const tokenWrap = document.getElementById('tokenAttributions');
  tokenWrap.innerHTML = '';
  if (data.token_attributions && data.token_attributions.length > 0) {
    data.token_attributions.forEach(t => {
      const chip = document.createElement('span');
      chip.className = `token-chip ${t.direction === 'fake' ? 'fake' : 'original'}`;
      chip.innerHTML = `<b>${t.stem}</b> <small>${t.weight > 0 ? '+' : ''}${t.weight}</small>`;
      chip.title = `TF-IDF: ${t.tfidf} | Coef: ${t.coef}`;
      tokenWrap.appendChild(chip);
    });
  } else {
    tokenWrap.innerHTML = `<span style="color:var(--tx2); font-size:11px;">Balanced distribution without isolated outlier fraudulent stems.</span>`;
  }

  // Linguistic Metrics
  if (data.linguistic_metrics) {
    document.getElementById('metricLexDiv').innerText = data.linguistic_metrics.lexical_diversity.toFixed(2);
    document.getElementById('metricSuperlatives').innerText = data.linguistic_metrics.superlative_count;
    document.getElementById('metricExclamations').innerText = data.linguistic_metrics.exclamation_count;
    document.getElementById('metricWords').innerText = data.linguistic_metrics.total_words;
  }

  // Extracted preview
  document.getElementById('extractedTextPreview').innerText = data.extracted_text || 'No text';
  document.getElementById('radarStatusBadge').innerText = "INFERENCE COMPLETED";
}

// --- PRESET SAMPLERS ---
function initPresets() {
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      playBeep(750, 'sine', 0.04, 0.05);
      const text = btn.getAttribute('data-review');
      document.getElementById('reviewText').value = text;
      updateTextMetrics();
      // Switch to direct text pane
      document.querySelectorAll('.modality-btn').forEach(b => b.classList.remove('active'));
      document.querySelector('[data-modality="direct-text"]').classList.add('active');
      activeModality = 'direct-text';
      document.getElementById('pane-direct-text').hidden = false;
      document.getElementById('pane-file-upload').hidden = true;
      document.getElementById('pane-ocr-image').hidden = true;

      addLog("INGEST", `Injected preset sampler into direct buffer.`);
      runAudit();
    });
  });
}

function updateTextMetrics() {
  const val = document.getElementById('reviewText').value;
  document.getElementById('charCounter').innerText = `${val.length} CHARS`;
  const words = val.trim() ? val.trim().split(/\s+/).length : 0;
  document.getElementById('wordCounter').innerText = `${words} WORDS`;
}

// --- UTC CLOCK ---
function startUtcClock() {
  function update() {
    const now = new Date();
    const utc = now.toISOString().substring(11, 19) + ' UTC';
    const el = document.getElementById('utcTime');
    if (el) el.innerText = utc;
  }
  update();
  setInterval(update, 1000);
}

// --- RAZORPAY SUBSCRIPTION ---
async function executeSubscription() {
  try {
    const res = await fetch('/create-order', { method: 'POST' });
    const data = await res.json();
    if (data.error) {
      alert("Subscription order creation failed: " + data.error);
      return;
    }

    const options = {
      key: data.key_id,
      amount: data.amount,
      currency: "INR",
      name: "VERIVIEW PRO RADAR",
      description: "Unlimited Review Audits",
      order_id: data.order_id,
      handler: async function (response) {
        const verifyRes = await fetch('/verify-payment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(response)
        });
        const vData = await verifyRes.json();
        if (vData.status === 'success') {
          alert("VeriView Pro Activated Successfully!");
          window.location.reload();
        } else {
          alert("Payment verification failed: " + vData.error);
        }
      }
    };
    const rzp = new Razorpay(options);
    rzp.open();
  } catch (e) {
    alert("Razorpay checkout error: " + e.message);
  }
}

// --- AUTH MODAL SYSTEM ---
function openAuthModal() {
  playBeep(850, 'sine', 0.04, 0.05);
  const modal = document.getElementById('authModal');
  if (modal) modal.showModal();
}

function initAuthHandlers() {
  const btnOpenAuth = document.getElementById('btnOpenAuthModal');
  if (btnOpenAuth) btnOpenAuth.onclick = openAuthModal;

  const btnTabSign = document.getElementById('tabSignInBtn');
  const btnTabReg = document.getElementById('tabRegisterBtn');
  const paneSign = document.getElementById('authSignInPane');
  const paneReg = document.getElementById('authRegisterPane');

  if (btnTabSign && btnTabReg) {
    btnTabSign.onclick = () => {
      playBeep(800, 'sine', 0.03, 0.03);
      btnTabSign.classList.add('fill');
      btnTabReg.classList.remove('fill');
      paneSign.hidden = false;
      paneReg.hidden = true;
    };
    btnTabReg.onclick = () => {
      playBeep(800, 'sine', 0.03, 0.03);
      btnTabReg.classList.add('fill');
      btnTabSign.classList.remove('fill');
      paneSign.hidden = true;
      paneReg.hidden = false;
    };
  }

  // 1-Click Instant Demo Access
  const triggerDemo = async (role) => {
    playScanSound();
    addLog("AUTH", `Initiating 1-click instant authentication: role [${role.toUpperCase()}]`);
    try {
      const res = await fetch('/auth/instant-demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role })
      });
      const data = await res.json();
      if (data.status === 'success') {
        addLog("AUTH", `Authenticated as ${data.user.name} (${data.user.email})`, "ok");
        window.location.reload();
      } else {
        alert(data.message || "Authentication failed");
      }
    } catch (e) {
      alert("Demo auth error: " + e.message);
    }
  };

  const bAud = document.getElementById('btnDemoAuditor');
  if (bAud) bAud.onclick = () => triggerDemo('auditor');
  const bAdm = document.getElementById('btnDemoAdmin');
  if (bAdm) bAdm.onclick = () => triggerDemo('admin');
  const bGst = document.getElementById('btnDemoGuest');
  if (bGst) bGst.onclick = () => triggerDemo('guest');

  // Direct Login
  const btnSubmitLogin = document.getElementById('btnSubmitLogin');
  if (btnSubmitLogin) {
    btnSubmitLogin.onclick = async () => {
      const email = document.getElementById('authEmail').value.trim();
      const password = document.getElementById('authPassword').value.trim();
      if (!email || !password) {
        alert("Please enter auditor email and passkey.");
        return;
      }
      playScanSound();
      try {
        const res = await fetch('/auth/direct-login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.status === 'success') {
          addLog("AUTH", `Successfully verified auditor: ${data.user.email}`, "ok");
          window.location.reload();
        } else {
          alert(data.message || "Invalid passkey credentials");
        }
      } catch (e) {
        alert("Login error: " + e.message);
      }
    };
  }

  // Direct Register
  const btnSubmitRegister = document.getElementById('btnSubmitRegister');
  if (btnSubmitRegister) {
    btnSubmitRegister.onclick = async () => {
      const name = document.getElementById('regName').value.trim();
      const email = document.getElementById('regEmail').value.trim();
      const password = document.getElementById('regPassword').value.trim();
      if (!email || !password) {
        alert("Please enter name, email, and passkey.");
        return;
      }
      playScanSound();
      try {
        const res = await fetch('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (data.status === 'success') {
          addLog("AUTH", `Enrolled new auditor: ${data.user.name}`, "ok");
          window.location.reload();
        } else {
          alert(data.message || "Registration failed");
        }
      } catch (e) {
        alert("Registration error: " + e.message);
      }
    };
  }

  // Auto open if notice in URL
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('auth_modal') === 'open') {
    openAuthModal();
  }
}

// --- TARGETING RETICLE CURSOR ---
function initReticle() {
  const ret = document.getElementById('ret');
  if (!ret) return;

  window.addEventListener('mousemove', (e) => {
    ret.style.left = e.clientX + 'px';
    ret.style.top = e.clientY + 'px';
  });

  const interactiveSelector = 'button, a, input, textarea, .preset-btn, .dropzone, .modality-btn';
  document.addEventListener('mouseover', (e) => {
    if (e.target.closest(interactiveSelector)) {
      ret.classList.add('big');
    }
  });

  document.addEventListener('mouseout', (e) => {
    if (e.target.closest(interactiveSelector)) {
      ret.classList.remove('big');
    }
  });
}

// --- EXPORT AUDIT TELEMETRY ---
function exportAuditReport() {
  playBeep(940, 'sine', 0.05, 0.06);
  const logLines = Array.from(document.querySelectorAll('#logContent .log-line')).map(l => l.innerText).join('\n');
  const report = {
    system: "VeriView AI Fraud Detection Radar",
    timestamp: new Date().toISOString(),
    accuracy: "98.4%",
    loss_function: "Binary Cross-Entropy (Log-Loss)",
    regularization: "L2 Ridge (C=1.0)",
    dataset_records: 2000,
    active_stems: 84,
    recent_logs: logLines
  };

  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `veriview-audit-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  addLog("AUDIT", "Exported complete fraud audit telemetry file (.json)", "ok");
}

// --- INITIALIZATION ---
window.addEventListener('DOMContentLoaded', () => {
  initStarfield();
  initReticle();
  runBootSequence();
  initTabs();
  initModalities();
  initPresets();
  startUtcClock();
  fetchArchitecture();
  initAuthHandlers();

  // Execution triggers
  document.getElementById('btnAuditReview').onclick = runAudit;
  document.getElementById('btnClearReview').onclick = () => {
    document.getElementById('reviewText').value = '';
    updateTextMetrics();
  };
  document.getElementById('reviewText').oninput = updateTextMetrics;

  // Audio Toggle
  const audioBtn = document.getElementById('btnAudioToggle');
  audioBtn.onclick = () => {
    soundEnabled = !soundEnabled;
    audioBtn.innerHTML = `AUDIO: <b>${soundEnabled ? 'ON' : 'OFF'}</b>`;
    if (soundEnabled) {
      initAudio();
      playBeep(990, 'sine', 0.06, 0.06);
    }
  };

  // Terminal Drawer
  const logDrawer = document.getElementById('logDrawer');
  document.getElementById('btnLogsToggle').onclick = () => {
    playBeep(700, 'sine', 0.03, 0.03);
    logDrawer.classList.toggle('open');
  };
  document.getElementById('btnCloseLogs').onclick = () => {
    logDrawer.classList.remove('open');
  };
  document.getElementById('btnClearLogs').onclick = () => {
    document.getElementById('logContent').innerHTML = '';
  };

  const btnExp = document.getElementById('btnExportLogs');
  if (btnExp) btnExp.onclick = exportAuditReport;

  // Pro Upgrade Button
  const upBtn = document.getElementById('btnUpgradePro');
  if (upBtn) {
    upBtn.onclick = () => {
      playBeep(850, 'sine', 0.04, 0.05);
      const modal = document.getElementById('subModal');
      if (modal) modal.showModal();
    };
  }

  const execSubBtn = document.getElementById('btnExecuteSub');
  if (execSubBtn) {
    execSubBtn.onclick = executeSubscription;
  }
});


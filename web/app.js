/* ==========================================================================
   SurakshaAI — Web App Logic & API Integration
   ========================================================================== */

const API_BASE = '/api/v1';

// ── State ──────────────────────────────────────────────────────────────────
let currentMode = 'text';       // text | image
let selectedImageFile = null;

// Sample Presets
const SAMPLES = {
  anydesk:    "Hello sir I am from HDFC Bank support. Install AnyDesk and share the code to update KYC.",
  otp:        "Your refund is pending. Tell us the OTP just received and your money will be credited in 2 minutes.",
  upi:        "Your UPI refund of Rs.2,999 is waiting. Open collect request and enter PIN to receive money.",
  loan:       "Instant loan approved for Rs.50,000. No CIBIL check. Pay Rs.999 processing fee first at http://upi-cashback.xyz",
  safe_sms:   "SBI: Rs.1,250 debited from A/c XX1234 on 12-Aug. Avl Bal: Rs.24,500. If not done by you, call official customer care.",
  safe_alert: "Security alert: a login was made to your account. If this was not you, call the official bank helpline."
};

// ── DOMContentLoaded ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
  checkApiHealth();
  loadSample('anydesk');
  updateLangUI(getLang());

  // Close lang dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#lang-switcher')) {
      const dd = document.getElementById('lang-dropdown');
      if (dd) dd.classList.add('hidden');
    }
  });
});

// ── API Health ─────────────────────────────────────────────────────────────
async function checkApiHealth() {
  const badge = document.getElementById('api-status-badge');
  const text  = document.getElementById('api-status-text');
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      text.textContent = t('api_status_ok');
      badge.style.borderColor = 'rgba(16,185,129,0.3)';
      badge.style.color = '#34D399';
    } else throw new Error();
  } catch {
    text.textContent = t('api_status_err');
    badge.style.borderColor = 'rgba(245,158,11,0.4)';
    badge.style.color = '#FBBF24';
  }
}

// ── Main Nav Tabs ─────────────────────────────────────────────────────────
function switchMainTab(tab) {
  ['studio', 'history', 'analytics', 'assistant'].forEach(id => {
    const btn = document.getElementById(`tab-btn-${id}`);
    const cnt = document.getElementById(`tab-content-${id}`);
    if (btn) btn.classList.toggle('active', id === tab);
    if (cnt) cnt.classList.toggle('hidden', id !== tab);
  });
  if (tab === 'history')   loadHistory();
  if (tab === 'analytics') loadAnalytics();
}

// ── Input Mode: Text vs Image ─────────────────────────────────────────────
function switchInputMode(mode) {
  currentMode = mode;

  const textBtn  = document.getElementById('mode-btn-text');
  const imageBtn = document.getElementById('mode-btn-image');
  const textGrp  = document.getElementById('input-group-text');
  const imgGrp   = document.getElementById('input-group-image');
  const presets  = document.getElementById('preset-section');
  const btnLabel = document.getElementById('btn-analyze-text');

  if (mode === 'image') {
    textBtn.classList.remove('active');
    imageBtn.classList.add('active');
    textGrp.classList.add('hidden');
    imgGrp.classList.remove('hidden');
    presets.classList.add('hidden');
    btnLabel.textContent = t('btn_analyze_image');
  } else {
    imageBtn.classList.remove('active');
    textBtn.classList.add('active');
    imgGrp.classList.add('hidden');
    textGrp.classList.remove('hidden');
    presets.classList.remove('hidden');
    btnLabel.textContent = t('btn_analyze');
    document.getElementById('input-text-content').placeholder = t('placeholder_sms');
  }
}

// ── Sample Presets ────────────────────────────────────────────────────────
function loadSample(key) {
  if (currentMode === 'image') switchInputMode('text');
  const ta = document.getElementById('input-text-content');
  if (ta && SAMPLES[key]) ta.value = SAMPLES[key];
}

// ── Image Upload ──────────────────────────────────────────────────────────
function onDragOver(e)  { e.preventDefault(); document.getElementById('upload-zone').classList.add('drag-over'); }
function onDragLeave()  { document.getElementById('upload-zone').classList.remove('drag-over'); }
function onDrop(e) {
  e.preventDefault(); onDragLeave();
  const file = e.dataTransfer.files[0];
  if (file) handleImageFile(file);
}
function onFileSelect(e) {
  const file = e.target.files[0];
  if (file) handleImageFile(file);
}
function handleImageFile(file) {
  if (!file.type.startsWith('image/')) { showToast('Please upload a valid image file (PNG, JPG, WebP)', 'error'); return; }
  if (file.size > 10 * 1024 * 1024)    { showToast('File too large. Maximum size is 10MB.', 'error'); return; }

  selectedImageFile = file;
  const reader = new FileReader();
  reader.onload = (ev) => {
    document.getElementById('image-preview').src = ev.target.result;
    document.getElementById('preview-filename').textContent = file.name;
    document.getElementById('image-preview-container').classList.remove('hidden');
    document.getElementById('upload-zone').style.display = 'none';
  };
  reader.readAsDataURL(file);
}
function clearImageUpload() {
  selectedImageFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('image-preview').src = '';
  document.getElementById('image-preview-container').classList.add('hidden');
  document.getElementById('upload-zone').style.display = '';
}

// ── Main Analyze Dispatcher ───────────────────────────────────────────────
async function runAnalysis() {
  if (currentMode === 'image') await analyzeImage();
  else                          await analyzeText();
}

// ── Analyze Text ──────────────────────────────────────────────────────────
async function analyzeText() {
  const text = document.getElementById('input-text-content').value.trim();
  if (!text) { showToast('Please paste a message to analyze.', 'warning'); return; }

  const btn   = document.getElementById('btn-analyze');
  const label = document.getElementById('btn-analyze-text');
  btn.disabled = true;
  label.textContent = t('analyzing');

  try {
    const res = await fetch(`${API_BASE}/analyze/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        channel: 'sms',
        language: 'auto',
        preferred_language: getLang()
      })
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    renderResults(await res.json());
  } catch (err) {
    showToast(`Analysis failed: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    label.textContent = t('btn_analyze');
  }
}

// ── Analyze Image (OCR) ───────────────────────────────────────────────────
async function analyzeImage() {
  if (!selectedImageFile) { showToast('Please upload a screenshot first.', 'warning'); return; }

  const btn   = document.getElementById('btn-analyze');
  const label = document.getElementById('btn-analyze-text');
  btn.disabled = true;
  label.textContent = t('analyzing');

  try {
    const formData = new FormData();
    formData.append('file', selectedImageFile);
    formData.append('language', getLang());

    const res = await fetch(`${API_BASE}/analyze/image`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Server error ${res.status}` }));
      throw new Error(err.detail || `Server error ${res.status}`);
    }
    renderResults(await res.json());
  } catch (err) {
    showToast(`Image analysis failed: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    label.textContent = t('btn_analyze_image');
  }
}

// ── Render Results ────────────────────────────────────────────────────────
function renderResults(data) {
  document.getElementById('results-panel').classList.remove('hidden');

  // Score Gauge
  const score100 = Math.round((data.risk_score || 0) * 100);
  document.getElementById('meter-number').textContent = score100;

  const circle = document.getElementById('meter-circle');
  circle.style.borderColor = getRiskColor(data.risk_level);
  circle.style.boxShadow   = `0 0 25px ${getRiskGlow(data.risk_level)}`;

  const badge = document.getElementById('risk-badge');
  badge.textContent = getRiskLabel(data.risk_level);
  badge.className   = `risk-level-badge ${data.risk_level || 'low_risk'}`;

  // Rule Flags
  const flags     = data.rule_flags || [];
  const container = document.getElementById('flag-tags-container');
  container.innerHTML = flags.length
    ? flags.map(f => `<span class="flag-tag">${f}</span>`).join('')
    : `<span class="flag-tag safe-tag">no_fraud_rules_triggered</span>`;

  // Evidence
  const ev = data.llm_response?.evidence || data.rule_evidence || [];
  document.getElementById('evidence-list').innerHTML = ev.length
    ? ev.map(e => `<li>${e}</li>`).join('')
    : '<li>No suspicious indicators detected.</li>';

  // Immediate Actions
  const ac = data.llm_response?.immediate_actions || [];
  document.getElementById('action-list').innerHTML = ac.length
    ? ac.map(a => `<li>${a}</li>`).join('')
    : '<li>Verify details through official channels only.</li>';

  // OCR Card
  const ocrCard = document.getElementById('ocr-card');
  if (data.ocr_extracted_text) {
    ocrCard.classList.remove('hidden');
    document.getElementById('ocr-text-display').textContent = data.ocr_extracted_text;
  } else {
    ocrCard.classList.add('hidden');
  }

  // AI Summary
  document.getElementById('ai-summary-text').textContent =
    data.llm_response?.risk_summary || 'Analysis complete.';

  // DO NOT list
  const dn = data.llm_response?.do_not || [];
  document.getElementById('ai-donot-list').innerHTML = dn.length
    ? dn.map(d => `<li>${d}</li>`).join('')
    : '<li>Do not share personal details with unknown callers.</li>';

  // Safe Alternatives
  const sa = data.llm_response?.safe_alternatives || [];
  document.getElementById('ai-alternatives-list').innerHTML = sa.length
    ? sa.map(a => `<li>${a}</li>`).join('')
    : '<li>Verify through your official bank application.</li>';

  document.getElementById('results-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function getRiskColor(level) {
  return { critical:'#DC143C', very_high_risk:'#EF4444', high_risk:'#F97316',
           caution:'#F59E0B', low_risk:'#10B981', safe:'#10B981' }[level] || '#10B981';
}
function getRiskGlow(level) {
  return { critical:'rgba(220,20,60,0.4)', very_high_risk:'rgba(239,68,68,0.35)',
           high_risk:'rgba(249,115,22,0.35)', caution:'rgba(245,158,11,0.3)',
           low_risk:'rgba(16,185,129,0.25)', safe:'rgba(16,185,129,0.25)' }[level] || 'rgba(16,185,129,0.25)';
}
function getRiskLabel(level) {
  const map = { critical:t('risk_critical'), very_high_risk:t('risk_very_high'),
                high_risk:t('risk_high'), caution:t('risk_medium'),
                low_risk:t('risk_low'), safe:t('risk_safe') };
  return map[level] || (level || 'SAFE').toUpperCase().replace(/_/g,' ');
}

// ── History ───────────────────────────────────────────────────────────────
async function loadHistory() {
  const tbody = document.getElementById('history-table-body');
  try {
    const res  = await fetch(`${API_BASE}/history?limit=50`);
    const data = await res.json();
    const items = data.items || data;
    if (!items || items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">${t('history_empty')}</td></tr>`;
      return;
    }
    tbody.innerHTML = items.map(item => {
      const score = Math.round((item.risk_score || 0) * 100);
      const color = getRiskColor(item.risk_level);
      const flags = (item.rule_flags || []).slice(0, 3).join(', ') || '—';
      const ts    = item.analyzed_at ? new Date(item.analyzed_at).toLocaleString('en-IN') : '—';
      const text  = (item.original_text || item.url || '').slice(0, 60) + '…';
      return `<tr>
        <td style="color:var(--text-muted);font-size:0.8rem;">${ts}</td>
        <td>${item.channel || '—'}</td>
        <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${text}</td>
        <td style="font-weight:700;color:${color};">${score}/100</td>
        <td><span style="color:${color};font-weight:600;">${(item.risk_level||'').replace(/_/g,' ').toUpperCase()}</span></td>
        <td style="font-size:0.78rem;color:var(--text-muted);">${flags}</td>
      </tr>`;
    }).join('');
  } catch {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#F87171;">Failed to load history.</td></tr>`;
  }
}

async function clearHistory() {
  if (!confirm('Clear all history display? (This does not delete server records)')) return;
  document.getElementById('history-table-body').innerHTML =
    `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">${t('history_empty')}</td></tr>`;
}

// ── Analytics ─────────────────────────────────────────────────────────────
async function loadAnalytics() {
  try {
    const res  = await fetch(`${API_BASE}/analytics/summary`);
    const data = await res.json();
    document.getElementById('stat-total').textContent = data.total_analyses || 0;
    document.getElementById('stat-fraud').textContent = data.fraud_count    || 0;
    document.getElementById('stat-safe').textContent  = data.safe_count     || 0;
    const list = document.getElementById('top-patterns-list');
    const patterns = data.top_patterns || [];
    list.innerHTML = patterns.length
      ? patterns.map(p => `<li>${p.pattern_name} — <strong style="color:#F59E0B;">${p.count} detections</strong></li>`).join('')
      : '<li>No pattern data available yet.</li>';
  } catch {
    document.getElementById('stat-total').textContent = '—';
  }
}

// ── Language Switcher ─────────────────────────────────────────────────────
function toggleLangDropdown() {
  document.getElementById('lang-dropdown').classList.toggle('hidden');
}

function selectLang(lang) {
  setLanguage(lang);
  updateLangUI(lang);
  document.getElementById('lang-dropdown').classList.add('hidden');
  checkApiHealth();
}

function updateLangUI(lang) {
  const dict = window.I18N[lang] || window.I18N['en'];
  const flagEl  = document.getElementById('lang-flag');
  const labelEl = document.getElementById('lang-label');
  if (flagEl)  flagEl.textContent  = dict.lang_flag || '🇮🇳';
  if (labelEl) labelEl.textContent = lang.toUpperCase();

  document.querySelectorAll('.lang-option').forEach(btn => {
    const m = btn.getAttribute('onclick').match(/'(\w+)'/);
    if (m) btn.classList.toggle('active', m[1] === lang);
  });
}

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const existing = document.getElementById('toast-notification');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.id = 'toast-notification';
  const c = { success:['rgba(16,185,129,0.15)','rgba(16,185,129,0.4)','#34D399'],
              error:  ['rgba(239,68,68,0.15)','rgba(239,68,68,0.4)','#F87171'],
              warning:['rgba(245,158,11,0.15)','rgba(245,158,11,0.4)','#FDE047'],
              info:   ['rgba(14,165,233,0.15)','rgba(14,165,233,0.4)','#38BDF8'] }[type] || ['rgba(14,165,233,0.15)','rgba(14,165,233,0.4)','#38BDF8'];
  toast.style.cssText = `position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);
    background:${c[0]};border:1px solid ${c[1]};color:${c[2]};
    padding:0.75rem 1.5rem;border-radius:12px;font-size:0.9rem;font-weight:600;
    z-index:9999;backdrop-filter:blur(12px);box-shadow:0 8px 32px rgba(0,0,0,0.4);
    max-width:90vw;text-align:center;`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ── AI Safety Assistant ───────────────────────────────────────────────────
function askQuickQuestion(qText) {
  const input = document.getElementById('assistant-query-input');
  if (input) {
    input.value = qText;
    askAssistant();
  }
}

async function askAssistant() {
  const input = document.getElementById('assistant-query-input');
  const question = input ? input.value.trim() : '';
  if (!question) {
    showToast('Please enter a question to ask the AI Safety Assistant.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-ask-assistant');
  const btnText = document.getElementById('btn-ask-text');
  if (btn) btn.disabled = true;
  if (btnText) btnText.textContent = t('analyzing');

  try {
    const res = await fetch(`${API_BASE}/assistant/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        language: getLang()
      })
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    document.getElementById('assistant-q-display').textContent = data.question || question;
    document.getElementById('assistant-a-display').textContent = data.answer || 'No advisory generated.';

    const badge = document.getElementById('assistant-source-badge');
    if (badge) {
      badge.textContent = data.source === 'mistral_ai' ? 'Mistral AI Live' : 'Verified Advice';
    }

    const panel = document.getElementById('assistant-response-panel');
    if (panel) panel.classList.remove('hidden');
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    showToast(`Assistant error: ${err.message}`, 'error');
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = t('btn_ask');
  }
}


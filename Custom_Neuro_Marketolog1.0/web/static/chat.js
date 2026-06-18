/* ── Neuro Marketolog Chat JS ─────────────────────────────────────────── */

const PAID_SPLIT = '[PAID_START]';
const REPORT_MARKER = 'МАРКЕТИНГОВЫЙ_АНАЛИЗ_ЗАВЕРШЁН';

// ── Copy protection ──────────────────────────────────────────────────────
document.addEventListener('copy', e => { e.preventDefault(); e.clipboardData.setData('text/plain', ''); });
document.addEventListener('cut', e => e.preventDefault());
document.addEventListener('contextmenu', e => e.preventDefault());
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && ['c', 'x', 'a', 'p'].includes(e.key.toLowerCase())) e.preventDefault();
});

// ── Marked config ────────────────────────────────────────────────────────
marked.setOptions({ breaks: true, gfm: true });

// ── State ────────────────────────────────────────────────────────────────
let chatStarted = false;
let isFinished = false;
let isUnlocked = localStorage.getItem('nm_unlocked') === '1';

// ── DOM refs ─────────────────────────────────────────────────────────────
const messagesEl = document.getElementById('messages');
const userInput  = document.getElementById('userInput');
const sendBtn    = document.getElementById('sendBtn');
const statusDot  = document.getElementById('statusDot');
const undoBtn    = document.getElementById('undoBtn');
const resetBtn   = document.getElementById('resetBtn');
const startBtn   = document.getElementById('startBtn');
const chatSection = document.getElementById('chatSection');
const unlockModal = document.getElementById('unlockModal');
const modalClose  = document.getElementById('modalClose');
const tokenInput  = document.getElementById('tokenInput');
const tokenSubmit = document.getElementById('tokenSubmit');
const tokenError  = document.getElementById('tokenError');

// ── Init ─────────────────────────────────────────────────────────────────
if (window.CHAT_ONLY) {
  startChat();
}

if (startBtn) {
  startBtn.addEventListener('click', () => {
    chatSection.scrollIntoView({ behavior: 'smooth' });
    setTimeout(startChat, 400);
  });
}

resetBtn.addEventListener('click', async () => {
  if (!confirm('Начать диагностику заново?')) return;
  await fetch('/api/reset', { method: 'POST' });
  messagesEl.innerHTML = '';
  isFinished = false;
  chatStarted = false;
  undoBtn.style.display = 'none';
  enableInput();
  startChat();
});

undoBtn.addEventListener('click', async () => {
  const res = await fetch('/api/undo', { method: 'POST' });
  if (!res.ok) return;
  const data = await res.json();
  const msgs = messagesEl.querySelectorAll('.msg--ai');
  if (msgs.length > 0) msgs[msgs.length - 1].remove();
  const userMsgs = messagesEl.querySelectorAll('.msg--user');
  if (userMsgs.length > 0) userMsgs[userMsgs.length - 1].remove();
  renderAI(data.reply);
  enableInput();
});

// ── Modal ─────────────────────────────────────────────────────────────────
modalClose.addEventListener('click', () => unlockModal.style.display = 'none');
unlockModal.addEventListener('click', e => { if (e.target === unlockModal) unlockModal.style.display = 'none'; });

tokenSubmit.addEventListener('click', tryUnlock);
tokenInput.addEventListener('keydown', e => { if (e.key === 'Enter') tryUnlock(); });

async function tryUnlock() {
  const token = tokenInput.value.trim();
  if (!token) return;
  tokenSubmit.disabled = true;
  tokenSubmit.textContent = 'Проверяю...';
  tokenError.style.display = 'none';

  try {
    const res = await fetch('/api/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    if (res.ok) {
      localStorage.setItem('nm_unlocked', '1');
      isUnlocked = true;
      unlockModal.style.display = 'none';
      applyUnlock();
    } else {
      tokenError.style.display = 'block';
    }
  } catch {
    tokenError.style.display = 'block';
  } finally {
    tokenSubmit.disabled = false;
    tokenSubmit.textContent = 'Активировать';
  }
}

// ── Chat start ────────────────────────────────────────────────────────────
async function startChat() {
  if (chatStarted) return;
  chatStarted = true;
  setStatus('Подключаюсь...');
  disableInput();

  try {
    const params = new URLSearchParams(window.location.search);
    const qs = ['utm_source', 'utm_medium', 'utm_campaign']
      .filter(k => params.get(k))
      .map(k => `${k}=${encodeURIComponent(params.get(k))}`)
      .join('&');

    const res = await fetch(`/api/start${qs ? '?' + qs : ''}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      renderAI(err.detail || 'Не удалось подключиться. Попробуйте позже.');
      return;
    }
    const data = await res.json();
    renderAI(data.reply);
    if (!data.finished) enableInput();
    else handleFinish(data.contact_link);
  } catch {
    renderAI('Ошибка подключения. Проверьте интернет и обновите страницу.');
  }
}

// ── Send message ──────────────────────────────────────────────────────────
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || !sendBtn.disabled === false) return;

  renderUser(text);
  userInput.value = '';
  userInput.style.height = 'auto';
  disableInput();
  setStatus('Думает...');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      renderAI(err.detail || 'Ошибка. Попробуйте ещё раз.');
      enableInput();
      return;
    }

    const data = await res.json();

    if (data.finished) {
      renderReport(data.reply);
      handleFinish(data.contact_link);
    } else {
      renderAI(data.reply);
      enableInput();
      undoBtn.style.display = 'inline-flex';
    }
  } catch {
    renderAI('Ошибка соединения. Попробуйте ещё раз.');
    enableInput();
  }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
userInput.addEventListener('input', () => {
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 160) + 'px';
});

// ── Render helpers ────────────────────────────────────────────────────────
function renderUser(text) {
  const div = document.createElement('div');
  div.className = 'msg msg--user';
  div.textContent = text;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function renderAI(text) {
  const div = document.createElement('div');
  div.className = 'msg msg--ai';
  div.innerHTML = marked.parse(text);
  messagesEl.appendChild(div);
  scrollToBottom();
  setStatus('Онлайн');
}

function renderReport(rawText) {
  // Strip the completion marker
  const cleaned = rawText.replace(REPORT_MARKER, '').trim();

  const paidIdx = cleaned.indexOf(PAID_SPLIT);

  const freeText = paidIdx !== -1 ? cleaned.slice(0, paidIdx).trim() : cleaned;
  const paidText = paidIdx !== -1 ? cleaned.slice(paidIdx + PAID_SPLIT.length).trim() : '';

  const wrap = document.createElement('div');
  wrap.className = 'msg msg--ai msg--report';

  // Free sections
  const freeDiv = document.createElement('div');
  freeDiv.className = 'report-free';
  freeDiv.innerHTML = marked.parse(freeText);
  wrap.appendChild(freeDiv);

  if (paidText) {
    // Paid sections
    const paidWrap = document.createElement('div');
    paidWrap.className = 'report-paid' + (isUnlocked ? ' report-paid--unlocked' : '');
    paidWrap.id = 'paidSection';

    const paidContent = document.createElement('div');
    paidContent.className = 'report-paid__content';
    paidContent.innerHTML = marked.parse(paidText);
    paidWrap.appendChild(paidContent);

    if (!isUnlocked) {
      const overlay = document.createElement('div');
      overlay.className = 'report-paid__overlay';
      overlay.id = 'paidOverlay';
      overlay.innerHTML = `
        <div class="paid-gate">
          <div class="paid-gate__icon">🔒</div>
          <h3 class="paid-gate__title">Полная версия анализа</h3>
          <p class="paid-gate__desc">Включает: детальный план на 12 месяцев, финансовую модель, дорожную карту и скрипты офферов.</p>
          <div class="paid-gate__actions">
            <a href="${window.CONTACT_LINK}" target="_blank" class="btn-primary">Получить полный доступ →</a>
            <button class="btn-unlock" id="enterTokenBtn">Ввести токен</button>
          </div>
        </div>
      `;
      paidWrap.appendChild(overlay);
    }

    wrap.appendChild(paidWrap);
  }

  messagesEl.appendChild(wrap);
  scrollToBottom();
  setStatus('Анализ завершён');

  // Wire up token button
  const tokenBtn = document.getElementById('enterTokenBtn');
  if (tokenBtn) tokenBtn.addEventListener('click', () => unlockModal.style.display = 'flex');
}

function handleFinish(contactLink) {
  isFinished = true;
  disableInput();
  undoBtn.style.display = 'none';
  userInput.placeholder = 'Диагностика завершена';

  // CTA block
  const cta = document.createElement('div');
  cta.className = 'cta-block';
  cta.innerHTML = `
    <div class="cta-block__inner">
      <h3 class="cta-block__title">Хотите обсудить анализ лично?</h3>
      <p class="cta-block__desc">Александр разберёт ваш отчёт, ответит на вопросы и предложит конкретные шаги для вашего бизнеса.</p>
      <a href="${contactLink || window.CONTACT_LINK}" target="_blank" class="btn-primary">Написать в Telegram →</a>
    </div>
  `;
  messagesEl.appendChild(cta);
  scrollToBottom();
}

// ── Unlock ────────────────────────────────────────────────────────────────
function applyUnlock() {
  const paidSection = document.getElementById('paidSection');
  const overlay = document.getElementById('paidOverlay');
  if (paidSection) {
    paidSection.classList.add('report-paid--unlocked');
    if (overlay) overlay.remove();
  }
  // Show PDF print button
  const printBtn = document.createElement('button');
  printBtn.className = 'btn-print';
  printBtn.textContent = '🖨 Распечатать / Сохранить PDF';
  printBtn.addEventListener('click', () => window.print());
  const report = document.querySelector('.msg--report');
  if (report) report.appendChild(printBtn);
}

// ── Utilities ─────────────────────────────────────────────────────────────
function enableInput() {
  userInput.disabled = false;
  sendBtn.disabled = false;
  userInput.focus();
  setStatus('Онлайн');
}

function disableInput() {
  userInput.disabled = true;
  sendBtn.disabled = true;
}

function setStatus(text) {
  if (statusDot) statusDot.textContent = text;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

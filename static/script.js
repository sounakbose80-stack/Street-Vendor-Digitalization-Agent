/* ============================================================
   Street Vendor Digitalization Agent — Frontend Script
   ============================================================ */

'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentLanguage = 'english';
let isLoading = false;
let lastProfileText = '';

// ---------------------------------------------------------------------------
// Language Management
// ---------------------------------------------------------------------------
function setLanguage(lang) {
  currentLanguage = lang;
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  // Update textarea placeholder based on language
  const textarea = document.getElementById('chatInput');
  if (!textarea) return;

  const placeholders = {
    english: 'Type your question... e.g. I sell vegetables near Dadar station',
    hindi:   'अपना सवाल लिखें... जैसे मैं पुणे में फल बेचता हूँ',
    marathi: 'तुमचा प्रश्न लिहा... उदा. मी पुण्यात फळे विकतो',
  };
  textarea.placeholder = placeholders[lang] || placeholders.english;
}

// ---------------------------------------------------------------------------
// Tab Switching
// ---------------------------------------------------------------------------
function switchTab(tab) {
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `tab-${tab}`);
  });
  document.querySelectorAll('.tab-btn').forEach(btn => {
    const isActive = btn.dataset.tab === tab;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-selected', isActive);
  });
}

// ---------------------------------------------------------------------------
// Chat — Core
// ---------------------------------------------------------------------------
function scrollToBottom() {
  const win = document.getElementById('chatWindow');
  if (win) win.scrollTop = win.scrollHeight;
}

function appendMessage(role, text) {
  const win = document.getElementById('chatWindow');
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'bot' ? '🤖' : '👤';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  div.appendChild(avatar);
  div.appendChild(bubble);
  win.appendChild(div);
  scrollToBottom();
  return bubble;
}

function showLoadingBubble() {
  const win = document.getElementById('chatWindow');
  const div = document.createElement('div');
  div.className = 'chat-message bot';
  div.id = 'loadingMsg';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🤖';

  const loading = document.createElement('div');
  loading.className = 'loading-bubble bubble';
  loading.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';

  div.appendChild(avatar);
  div.appendChild(loading);
  win.appendChild(div);
  scrollToBottom();
}

function removeLoadingBubble() {
  const el = document.getElementById('loadingMsg');
  if (el) el.remove();
}

function setInputDisabled(disabled) {
  const input = document.getElementById('chatInput');
  const btn = document.getElementById('sendBtn');
  if (input) input.disabled = disabled;
  if (btn) btn.disabled = disabled;
  isLoading = disabled;
}

// ---------------------------------------------------------------------------
// Chat — Send Message
// ---------------------------------------------------------------------------
async function sendMessage() {
  if (isLoading) return;

  const input = document.getElementById('chatInput');
  const message = (input.value || '').trim();
  if (!message) return;

  input.value = '';
  input.style.height = 'auto';
  appendMessage('user', message);

  setInputDisabled(true);
  showLoadingBubble();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language: currentLanguage }),
    });

    removeLoadingBubble();

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      appendMessage('bot', `⚠️ Sorry, something went wrong: ${err.error || response.statusText}. Please try again.`);
      return;
    }

    const data = await response.json();
    appendMessage('bot', data.reply || 'No response received.');
  } catch (err) {
    removeLoadingBubble();
    appendMessage('bot', '⚠️ Network error. Please check your connection and try again.');
    console.error('Chat error:', err);
  } finally {
    setInputDisabled(false);
    document.getElementById('chatInput')?.focus();
  }
}

// ---------------------------------------------------------------------------
// Chat — Quick Message Helper
// ---------------------------------------------------------------------------
function sendQuickMessage(text) {
  const input = document.getElementById('chatInput');
  if (input) input.value = text;
  sendMessage();
}

// ---------------------------------------------------------------------------
// Chat — Enter to send (Shift+Enter for newline)
// ---------------------------------------------------------------------------
function handleChatKey(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// ---------------------------------------------------------------------------
// Profile Generation
// ---------------------------------------------------------------------------
async function generateProfile(event) {
  event.preventDefault();
  if (isLoading) return;

  const businessName = document.getElementById('businessName').value.trim();
  const ownerName    = document.getElementById('ownerName').value.trim();
  const location     = document.getElementById('location').value.trim();
  const itemType     = document.getElementById('itemType').value.trim();
  const upiId        = document.getElementById('upiId').value.trim();

  if (!businessName || !location || !itemType) return;

  const btn = document.getElementById('generateBtn');
  const btnText = document.getElementById('generateBtnText');
  const spinner = document.getElementById('generateSpinner');
  const output = document.getElementById('profileOutput');

  // Show loading state
  btn.disabled = true;
  btnText.textContent = 'Generating…';
  spinner.classList.remove('hidden');
  output.classList.add('hidden');
  isLoading = true;

  try {
    const response = await fetch('/api/generate-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        business_name: businessName,
        owner_name:    ownerName,
        location,
        item_type:     itemType,
        upi_id:        upiId,
        language:      currentLanguage,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      showError(`Profile generation failed: ${err.error || response.statusText}`);
      return;
    }

    const data = await response.json();
    const profileText = data.profile || '';
    lastProfileText = profileText;

    const content = document.getElementById('profileContent');
    content.textContent = profileText;
    output.classList.remove('hidden');

    // Scroll to output
    output.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    showError('Network error while generating profile. Please try again.');
    console.error('Profile error:', err);
  } finally {
    btn.disabled = false;
    btnText.textContent = '✨ Generate My Digital Card';
    spinner.classList.add('hidden');
    isLoading = false;
  }
}

// ---------------------------------------------------------------------------
// Profile Actions
// ---------------------------------------------------------------------------
function copyProfile() {
  if (!lastProfileText) return;
  navigator.clipboard.writeText(lastProfileText).then(() => {
    const btn = document.querySelector('.copy-btn');
    if (btn) {
      const original = btn.textContent;
      btn.textContent = '✅ Copied!';
      setTimeout(() => { btn.textContent = original; }, 2000);
    }
  }).catch(() => {
    // Fallback for older browsers
    const el = document.createElement('textarea');
    el.value = lastProfileText;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
  });
}

function shareProfile() {
  if (!lastProfileText) return;
  const text = encodeURIComponent(lastProfileText.slice(0, 1000));
  window.open(`https://wa.me/?text=${text}`, '_blank', 'noopener');
}

function resetProfile() {
  document.getElementById('profileForm').reset();
  document.getElementById('profileOutput').classList.add('hidden');
  lastProfileText = '';
  document.getElementById('businessName').focus();
}

// ---------------------------------------------------------------------------
// Error Utility
// ---------------------------------------------------------------------------
function showError(message) {
  // Append an error message to the profile area
  const output = document.getElementById('profileOutput');
  const content = document.getElementById('profileContent');
  if (content) {
    content.textContent = `⚠️ ${message}`;
    output.classList.remove('hidden');
    output.style.borderColor = '#dc3545';
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setLanguage('english');

  // Auto-expand textarea on input
  const textarea = document.getElementById('chatInput');
  if (textarea) {
    textarea.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
    textarea.focus();
  }
});

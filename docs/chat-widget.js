/* ── Chat Widget — BRACE4PEACE RAG Analyst Chat ── */
(function () {
  'use strict';

  /* ── Config ── */
  const API_BASE = 'https://ksvendsen-brace4peace-chat.hf.space';
  const PIN_CODE = '2025';
  const LS_PIN   = 'b4p_pin_ok';
  const LS_KEY   = 'b4p_api_key';
  const LS_NAME  = 'b4p_analyst_name';
  const COUNTRIES = ['Kenya', 'Somalia', 'South Sudan'];

  /* ── State ── */
  let panelOpen = false;
  let activeCountry = null;
  let messages = [];
  let coldStartRetries = 0;

  /* ── Mount ── */
  const root = document.getElementById('chat-widget-container');
  if (!root) return;

  function render() {
    root.innerHTML = '';
    root.appendChild(buildToggle());
    root.appendChild(buildOverlay());
    root.appendChild(buildPanel());
  }

  /* ── Toggle button ── */
  function buildToggle() {
    const btn = el('button', { className: 'chat-toggle-btn', title: 'Open analyst chat' });
    btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/></svg>';
    btn.onclick = () => togglePanel(true);
    return btn;
  }

  /* ── Overlay ── */
  function buildOverlay() {
    const ov = el('div', { className: 'chat-overlay' + (panelOpen ? ' visible' : '') });
    ov.onclick = () => togglePanel(false);
    return ov;
  }

  /* ── Panel ── */
  function buildPanel() {
    const panel = el('div', { className: 'chat-panel' + (panelOpen ? ' open' : '') });

    /* Header */
    const header = el('div', { className: 'chat-header' });
    header.innerHTML = '<span class="chat-header-title">BRACE4PEACE Analyst</span>';
    const closeBtn = el('button', { className: 'chat-header-close', textContent: '\u00d7' });
    closeBtn.onclick = () => togglePanel(false);
    header.appendChild(closeBtn);
    panel.appendChild(header);

    /* Gate flow */
    if (!localStorage.getItem(LS_PIN)) {
      panel.appendChild(buildPinGate());
      return panel;
    }
    if (!localStorage.getItem(LS_KEY)) {
      panel.appendChild(buildApiGate());
      return panel;
    }
    if (!localStorage.getItem(LS_NAME)) {
      panel.appendChild(buildNameGate());
      return panel;
    }

    /* Filters */
    panel.appendChild(buildFilters());

    /* Messages */
    const msgArea = el('div', { className: 'chat-messages', id: 'chat-messages' });
    if (messages.length === 0) {
      const welcome = el('div', { className: 'chat-msg-assistant' });
      const bubble = el('div', { className: 'chat-bubble' });
      bubble.textContent = 'Hello ' + localStorage.getItem(LS_NAME) + '. Ask me about hate speech patterns, disinformation events, or early warnings across East Africa.';
      welcome.appendChild(bubble);
      msgArea.appendChild(welcome);
    } else {
      messages.forEach(function (m) { msgArea.appendChild(renderMessage(m)); });
    }
    panel.appendChild(msgArea);

    /* Input */
    panel.appendChild(buildInputArea());

    return panel;
  }

  /* ── PIN gate ── */
  function buildPinGate() {
    const gate = el('div', { className: 'chat-pin-gate' });
    gate.innerHTML =
      '<h3>Analyst Access</h3>' +
      '<p>Enter the team PIN to continue.</p>';
    const inp = el('input', { className: 'chat-pin-input', type: 'password', maxLength: 8, placeholder: '\u2022\u2022\u2022\u2022' });
    const errEl = el('div', { className: 'chat-pin-error' });
    const btn = el('button', { className: 'chat-pin-submit', textContent: 'Unlock' });
    btn.onclick = function () {
      if (inp.value === PIN_CODE) {
        localStorage.setItem(LS_PIN, '1');
        render();
      } else {
        errEl.textContent = 'Incorrect PIN. Try again.';
      }
    };
    inp.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    gate.appendChild(inp);
    gate.appendChild(errEl);
    gate.appendChild(btn);
    return gate;
  }

  /* ── API key gate ── */
  function buildApiGate() {
    const gate = el('div', { className: 'chat-api-gate' });
    gate.innerHTML =
      '<h3>API Key</h3>' +
      '<p>Paste your Hugging Face API token.</p>';
    const inp = el('input', { className: 'chat-api-input', type: 'password', placeholder: 'hf_...' });
    const btn = el('button', { className: 'chat-api-submit', textContent: 'Save' });
    btn.onclick = function () {
      var v = inp.value.trim();
      if (v) { localStorage.setItem(LS_KEY, v); render(); }
    };
    inp.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    gate.appendChild(inp);
    gate.appendChild(btn);
    return gate;
  }

  /* ── Name gate ── */
  function buildNameGate() {
    const gate = el('div', { className: 'chat-name-gate' });
    gate.innerHTML =
      '<h3>Your Name</h3>' +
      '<p>How should responses address you?</p>';
    const inp = el('input', { className: 'chat-name-input', type: 'text', placeholder: 'e.g. Amina' });
    const btn = el('button', { className: 'chat-name-submit', textContent: 'Continue' });
    btn.onclick = function () {
      var v = inp.value.trim();
      if (v) { localStorage.setItem(LS_NAME, v); render(); }
    };
    inp.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    gate.appendChild(inp);
    gate.appendChild(btn);
    return gate;
  }

  /* ── Filter chips ── */
  function buildFilters() {
    const wrap = el('div', { className: 'chat-filters' });
    COUNTRIES.forEach(function (c) {
      const chip = el('button', {
        className: 'chat-filter-chip' + (activeCountry === c ? ' active' : ''),
        textContent: c
      });
      chip.onclick = function () {
        activeCountry = activeCountry === c ? null : c;
        render();
        scrollMessages();
      };
      wrap.appendChild(chip);
    });
    return wrap;
  }

  /* ── Input area ── */
  function buildInputArea() {
    const area = el('div', { className: 'chat-input-area' });
    const ta = el('textarea', { className: 'chat-input', rows: 1, placeholder: 'Ask about hate speech or disinfo...' });
    ta.id = 'chat-input-field';
    ta.oninput = function () {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 100) + 'px';
    };
    ta.onkeydown = function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    };
    const btn = el('button', { className: 'chat-send-btn' });
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
    btn.onclick = sendMessage;
    area.appendChild(ta);
    area.appendChild(btn);
    return area;
  }

  /* ── Send message ── */
  function sendMessage() {
    var inp = document.getElementById('chat-input-field');
    if (!inp) return;
    var text = inp.value.trim();
    if (!text) return;

    messages.push({ role: 'user', content: text });
    render();
    scrollMessages();

    /* Show typing indicator */
    var msgArea = document.getElementById('chat-messages');
    if (msgArea) {
      var typing = el('div', { className: 'chat-typing', id: 'chat-typing' });
      typing.innerHTML = '<span></span><span></span><span></span>';
      msgArea.appendChild(typing);
      scrollMessages();
    }

    coldStartRetries = 0;
    callApi(text);
  }

  /* ── API call with cold-start retry ── */
  function callApi(query) {
    var headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + localStorage.getItem(LS_KEY)
    };
    var body = {
      query: query,
      session_id: sessionId
    };
    if (activeCountry) body.filters = { country: activeCountry };

    fetch(API_BASE + '/chat', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout ? AbortSignal.timeout(30000) : undefined
    })
      .then(function (res) {
        if (res.status === 503) throw { coldStart: true };
        if (!res.ok) throw new Error('API error ' + res.status);
        return res.json();
      })
      .then(function (data) {
        removeColdStart();
        removeTyping();
        messages.push({
          role: 'assistant',
          content: data.answer || data.response || 'No response.',
          confidence: data.confidence,
          sources: data.sources || data.citations || [],
          messageId: data.message_id || null
        });
        render();
        scrollMessages();
      })
      .catch(function (err) {
        if (err && err.coldStart && coldStartRetries < 3) {
          coldStartRetries++;
          showColdStart();
          setTimeout(function () { callApi(query); }, 5000);
        } else {
          removeTyping();
          removeColdStart();
          messages.push({
            role: 'assistant',
            content: 'Sorry, something went wrong. Please try again.',
            confidence: null,
            sources: []
          });
          render();
          scrollMessages();
        }
      });
  }

  /* ── Cold-start banner ── */
  function showColdStart() {
    var msgArea = document.getElementById('chat-messages');
    if (!msgArea || document.getElementById('chat-cold-start')) return;
    var banner = el('div', { className: 'chat-cold-start', id: 'chat-cold-start' });
    banner.innerHTML = '<span class="spinner"></span> Waking up the server... this can take a minute on first use.';
    var typing = document.getElementById('chat-typing');
    if (typing) msgArea.insertBefore(banner, typing);
    else msgArea.appendChild(banner);
    scrollMessages();
  }

  function removeColdStart() {
    var cs = document.getElementById('chat-cold-start');
    if (cs) cs.remove();
  }

  function removeTyping() {
    var t = document.getElementById('chat-typing');
    if (t) t.remove();
  }

  /* ── Render a message ── */
  function renderMessage(m) {
    if (m.role === 'user') {
      var wrap = el('div', { className: 'chat-msg-user' });
      var b = el('div', { className: 'chat-bubble' });
      b.textContent = m.content;
      wrap.appendChild(b);
      return wrap;
    }

    var wrap = el('div', { className: 'chat-msg-assistant' });
    var b = el('div', { className: 'chat-bubble' });
    b.innerHTML = renderMarkdownLinks(m.content);
    wrap.appendChild(b);

    /* Confidence badge */
    if (m.confidence) {
      var level = m.confidence.toLowerCase();
      var badge = el('div', { className: 'chat-confidence ' + level });
      badge.textContent = m.confidence.toUpperCase();
      wrap.appendChild(badge);
    }

    /* Source cards */
    if (m.sources && m.sources.length > 0) {
      var srcWrap = el('div', { className: 'chat-sources' });
      m.sources.forEach(function (s) {
        var card = el('div', { className: 'chat-source-card' });
        var title = s.title || s.doc_id || 'Source';
        var snippet = s.snippet || s.text || '';
        var url = s.url || s.link || '';
        card.innerHTML =
          '<div class="source-title">' + esc(title) + '</div>' +
          (snippet ? '<div class="source-snippet">' + esc(snippet.substring(0, 120)) + (snippet.length > 120 ? '...' : '') + '</div>' : '') +
          (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">Open source</a>' : '');
        srcWrap.appendChild(card);
      });
      wrap.appendChild(srcWrap);
    }

    /* Feedback */
    if (m.messageId) {
      var fb = el('div', { className: 'chat-feedback' });
      var thumbUp = el('button', { className: 'chat-feedback-btn', textContent: '\uD83D\uDC4D', title: 'Helpful' });
      var thumbDn = el('button', { className: 'chat-feedback-btn', textContent: '\uD83D\uDC4E', title: 'Not helpful' });
      thumbUp.onclick = function () { sendFeedback(m.messageId, 'up', thumbUp, thumbDn); };
      thumbDn.onclick = function () { sendFeedback(m.messageId, 'down', thumbDn, thumbUp); };
      fb.appendChild(thumbUp);
      fb.appendChild(thumbDn);
      wrap.appendChild(fb);
    }

    return wrap;
  }

  /* ── Feedback POST ── */
  function sendFeedback(messageId, direction, activeBtn, otherBtn) {
    activeBtn.classList.add('selected');
    otherBtn.classList.remove('selected');
    fetch(API_BASE + '/chat/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem(LS_KEY)
      },
      body: JSON.stringify({
        message_id: messageId,
        feedback: direction,
        analyst_name: localStorage.getItem(LS_NAME)
      })
    }).catch(function () { /* silent */ });
  }

  /* ── Markdown link rendering ── */
  function renderMarkdownLinks(text) {
    if (!text) return '';
    var escaped = esc(text);
    /* Convert [Text](URL) to links */
    escaped = escaped.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
    /* Convert bare URLs */
    escaped = escaped.replace(
      /(?<!")(https?:\/\/[^\s<"]+)/g,
      '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );
    /* Newlines to <br> */
    escaped = escaped.replace(/\n/g, '<br>');
    return escaped;
  }

  /* ── Toggle panel ── */
  function togglePanel(open) {
    panelOpen = open;
    render();
    if (open) {
      setTimeout(function () {
        var inp = document.getElementById('chat-input-field') ||
                  document.querySelector('.chat-pin-input') ||
                  document.querySelector('.chat-api-input') ||
                  document.querySelector('.chat-name-input');
        if (inp) inp.focus();
      }, 250);
    }
  }

  /* ── Scroll messages to bottom ── */
  function scrollMessages() {
    setTimeout(function () {
      var area = document.getElementById('chat-messages');
      if (area) area.scrollTop = area.scrollHeight;
    }, 50);
  }

  /* ── Helpers ── */
  function el(tag, props) {
    var e = document.createElement(tag);
    if (props) Object.keys(props).forEach(function (k) { e[k] = props[k]; });
    return e;
  }

  function esc(s) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  /* ── Init ── */
  render();

})();

/* ── Admin Page — BRACE4PEACE Verification & Annotation ── */
(function () {
  'use strict';

  /* ── Config ── */
  var API_BASE = 'https://ksvendsen-brace4peace-chat.hf.space';
  var PIN_CODE = '2025';
  var LS_PIN   = 'b4p_pin_ok';
  var LS_KEY   = 'b4p_api_key';
  var LS_NAME  = 'b4p_analyst_name';

  var COUNTRIES = ['Kenya', 'Somalia', 'South Sudan'];
  var SUBTYPES  = ['hate', 'abusive', 'offensive', 'normal'];

  /* ── State ── */
  var activeTab       = 'verify';
  var verifyData      = [];
  var reviewData      = [];
  var statsData       = null;
  var reviewCountry   = null;
  var reviewSubtype   = null;

  var root = document.getElementById('admin-app');

  /* ── Render ── */
  function render() {
    root.innerHTML = '';

    /* Auth gates */
    if (!localStorage.getItem(LS_PIN)) { root.appendChild(buildPinGate()); return; }
    if (!localStorage.getItem(LS_KEY)) { root.appendChild(buildApiGate()); return; }
    if (!localStorage.getItem(LS_NAME)) { root.appendChild(buildNameGate()); return; }

    root.appendChild(buildHeader());
    root.appendChild(buildTabs());

    var verifyPane = buildVerifyTab();
    var reviewPane = buildReviewTab();
    var statsPane  = buildStatsTab();

    verifyPane.className = 'admin-tab-content' + (activeTab === 'verify' ? ' active' : '');
    reviewPane.className = 'admin-tab-content' + (activeTab === 'review' ? ' active' : '');
    statsPane.className  = 'admin-tab-content' + (activeTab === 'stats' ? ' active' : '');

    root.appendChild(verifyPane);
    root.appendChild(reviewPane);
    root.appendChild(statsPane);
  }

  /* ── Auth gates ── */
  function buildPinGate() {
    var gate = el('div', 'admin-gate');
    gate.innerHTML = '<h2>Admin Access</h2><p>Enter the team PIN to continue.</p>';
    var inp = el('input', 'pin-input');
    inp.type = 'password'; inp.maxLength = 8; inp.placeholder = '\u2022\u2022\u2022\u2022';
    var err = el('div', 'admin-gate-error');
    var btn = el('button', 'admin-gate-btn');
    btn.textContent = 'Unlock';
    btn.onclick = function () {
      if (inp.value === PIN_CODE) { localStorage.setItem(LS_PIN, '1'); render(); }
      else { err.textContent = 'Incorrect PIN.'; }
    };
    inp.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    gate.appendChild(inp); gate.appendChild(err); gate.appendChild(btn);
    return gate;
  }

  function buildApiGate() {
    var gate = el('div', 'admin-gate');
    gate.innerHTML = '<h2>API Key</h2><p>Paste your Hugging Face API token.</p>';
    var inp = el('input', 'api-input');
    inp.type = 'password'; inp.placeholder = 'hf_...';
    var btn = el('button', 'admin-gate-btn');
    btn.textContent = 'Save';
    btn.onclick = function () {
      var v = inp.value.trim();
      if (v) { localStorage.setItem(LS_KEY, v); render(); }
    };
    inp.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    gate.appendChild(inp); gate.appendChild(btn);
    return gate;
  }

  function buildNameGate() {
    var gate = el('div', 'admin-gate');
    gate.innerHTML = '<h2>Your Name</h2><p>Used for audit trail on decisions.</p>';
    var inp = el('input', 'name-input');
    inp.type = 'text'; inp.placeholder = 'e.g. Amina';
    var btn = el('button', 'admin-gate-btn');
    btn.textContent = 'Continue';
    btn.onclick = function () {
      var v = inp.value.trim();
      if (v) { localStorage.setItem(LS_NAME, v); render(); loadInitialData(); }
    };
    inp.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    gate.appendChild(inp); gate.appendChild(btn);
    return gate;
  }

  /* ── Header ── */
  function buildHeader() {
    var hdr = el('div', 'admin-header');
    var left = el('div', 'admin-header-left');
    left.innerHTML = '<div class="admin-logo">MERL<span class="accent">x</span></div><span class="admin-subtitle">BRACE4PEACE Admin</span>';

    var right = el('div', '');
    right.style.display = 'flex';
    right.style.alignItems = 'center';
    right.style.gap = '8px';
    var user = el('span', 'admin-user');
    user.innerHTML = 'Signed in as <strong>' + esc(localStorage.getItem(LS_NAME)) + '</strong>';
    var logout = el('button', 'admin-logout');
    logout.textContent = 'Sign out';
    logout.onclick = function () {
      localStorage.removeItem(LS_PIN);
      localStorage.removeItem(LS_KEY);
      localStorage.removeItem(LS_NAME);
      render();
    };
    right.appendChild(user);
    right.appendChild(logout);
    hdr.appendChild(left);
    hdr.appendChild(right);
    return hdr;
  }

  /* ── Tabs ── */
  function buildTabs() {
    var tabs = el('div', 'admin-tabs');
    var items = [
      { id: 'verify', label: 'Verify Findings' },
      { id: 'review', label: 'Review Posts' },
      { id: 'stats',  label: 'Knowledge Base Stats' }
    ];
    items.forEach(function (t) {
      var btn = el('button', 'admin-tab' + (activeTab === t.id ? ' active' : ''));
      btn.textContent = t.label;
      btn.onclick = function () { activeTab = t.id; render(); };
      tabs.appendChild(btn);
    });
    return tabs;
  }

  /* ── Verify Findings tab ── */
  function buildVerifyTab() {
    var pane = el('div', '');

    if (verifyData.length === 0) {
      var empty = el('div', 'admin-empty');
      empty.innerHTML = 'No pending findings. <button class="admin-gate-btn" style="margin-left:12px;padding:6px 16px;font-size:12px" id="btn-refresh-verify">Refresh</button>';
      pane.appendChild(empty);
      setTimeout(function () {
        var b = document.getElementById('btn-refresh-verify');
        if (b) b.onclick = function () { fetchVerify(); };
      }, 0);
      return pane;
    }

    var wrap = el('div', 'admin-table-wrap');
    var table = el('table', 'admin-table');
    table.innerHTML =
      '<thead><tr>' +
      '<th>Date</th><th>Country</th><th>Finding</th><th>Confidence</th><th>Actions</th>' +
      '</tr></thead>';
    var tbody = el('tbody', '');

    verifyData.forEach(function (item, idx) {
      var tr = el('tr', '');
      tr.innerHTML =
        '<td>' + esc(item.date || '-') + '</td>' +
        '<td>' + esc(item.country || '-') + '</td>' +
        '<td class="text-col">' + esc(item.summary || item.finding || '-') + '</td>' +
        '<td><span class="conf-badge ' + (item.confidence || 'medium').toLowerCase() + '">' +
          (item.confidence || 'N/A').toUpperCase() + '</span></td>' +
        '<td><div class="action-group" id="verify-actions-' + idx + '"></div>' +
        '<input class="note-input" placeholder="Optional note..." id="verify-note-' + idx + '"></td>';
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    pane.appendChild(wrap);

    /* Bind action buttons after DOM attach */
    setTimeout(function () {
      verifyData.forEach(function (item, idx) {
        var container = document.getElementById('verify-actions-' + idx);
        if (!container) return;

        var btnV = el('button', 'btn-verify'); btnV.textContent = 'Verify';
        var btnF = el('button', 'btn-flag');   btnF.textContent = 'Flag';
        var btnR = el('button', 'btn-reject'); btnR.textContent = 'Reject';

        btnV.onclick = function () { decide(item, 'verified', idx); };
        btnF.onclick = function () { decide(item, 'flagged', idx); };
        btnR.onclick = function () { decide(item, 'rejected', idx); };

        container.appendChild(btnV);
        container.appendChild(btnF);
        container.appendChild(btnR);
      });
    }, 0);

    return pane;
  }

  function decide(item, decision, idx) {
    var noteEl = document.getElementById('verify-note-' + idx);
    var note = noteEl ? noteEl.value.trim() : '';
    apiFetch('/verification/decide', 'POST', {
      finding_id: item.id || item.finding_id,
      decision: decision,
      note: note,
      analyst_name: localStorage.getItem(LS_NAME)
    }).then(function () {
      verifyData.splice(idx, 1);
      render();
      showToast('Finding ' + decision);
    }).catch(function () { showToast('Error — try again'); });
  }

  /* ── Review Posts tab ── */
  function buildReviewTab() {
    var pane = el('div', '');

    /* Filters */
    var filters = el('div', 'admin-filters');
    COUNTRIES.forEach(function (c) {
      var chip = el('button', 'admin-filter-chip' + (reviewCountry === c ? ' active' : ''));
      chip.textContent = c;
      chip.onclick = function () {
        reviewCountry = reviewCountry === c ? null : c;
        fetchReview();
      };
      filters.appendChild(chip);
    });
    SUBTYPES.forEach(function (s) {
      var chip = el('button', 'admin-filter-chip' + (reviewSubtype === s ? ' active' : ''));
      chip.textContent = s;
      chip.onclick = function () {
        reviewSubtype = reviewSubtype === s ? null : s;
        fetchReview();
      };
      filters.appendChild(chip);
    });
    pane.appendChild(filters);

    if (reviewData.length === 0) {
      var empty = el('div', 'admin-empty');
      empty.innerHTML = 'No posts in review queue. <button class="admin-gate-btn" style="margin-left:12px;padding:6px 16px;font-size:12px" id="btn-refresh-review">Refresh</button>';
      pane.appendChild(empty);
      setTimeout(function () {
        var b = document.getElementById('btn-refresh-review');
        if (b) b.onclick = function () { fetchReview(); };
      }, 0);
      return pane;
    }

    var wrap = el('div', 'admin-table-wrap');
    var table = el('table', 'admin-table');
    table.innerHTML =
      '<thead><tr>' +
      '<th>Date</th><th>Country</th><th>Text</th><th>Label</th><th>Subtype</th><th>Actions</th>' +
      '</tr></thead>';
    var tbody = el('tbody', '');

    reviewData.forEach(function (post, idx) {
      var tr = el('tr', '');
      var labelClass = (post.label || 'normal').toLowerCase();
      tr.innerHTML =
        '<td>' + esc(post.date || '-') + '</td>' +
        '<td>' + esc(post.country || '-') + '</td>' +
        '<td class="text-col">' + esc(post.text || '-') + '</td>' +
        '<td><span class="status-badge ' + labelClass + '">' + esc(post.label || '-') + '</span></td>' +
        '<td>' + esc(post.subtype || '-') + '</td>' +
        '<td><div id="review-actions-' + idx + '"></div></td>';
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    pane.appendChild(wrap);

    /* Bind review action buttons */
    setTimeout(function () {
      reviewData.forEach(function (post, idx) {
        var container = document.getElementById('review-actions-' + idx);
        if (!container) return;

        var group = el('div', 'action-group');

        var btnC = el('button', 'btn-confirm'); btnC.textContent = 'Confirm';
        btnC.onclick = function () { annotatePost(post, 'confirmed', null, null, idx); };

        var btnCorr = el('button', 'btn-correct'); btnCorr.textContent = 'Correct';

        /* Correction dropdowns */
        var selLabel = el('select', 'correction-select');
        selLabel.id = 'corr-label-' + idx;
        selLabel.innerHTML = '<option value="">Label...</option><option value="hate">hate</option><option value="abusive">abusive</option><option value="offensive">offensive</option><option value="normal">normal</option>';

        var selSubtype = el('select', 'correction-select');
        selSubtype.id = 'corr-subtype-' + idx;
        selSubtype.innerHTML = '<option value="">Subtype...</option><option value="ethnic">ethnic</option><option value="religious">religious</option><option value="gender">gender</option><option value="political">political</option><option value="other">other</option><option value="none">none</option>';

        btnCorr.onclick = function () {
          var newLabel = selLabel.value || null;
          var newSubtype = selSubtype.value || null;
          if (!newLabel && !newSubtype) { showToast('Select a correction first'); return; }
          annotatePost(post, 'corrected', newLabel, newSubtype, idx);
        };

        var btnFl = el('button', 'btn-flag'); btnFl.textContent = 'Flag';
        btnFl.onclick = function () { annotatePost(post, 'flagged', null, null, idx); };

        group.appendChild(btnC);
        group.appendChild(selLabel);
        group.appendChild(selSubtype);
        group.appendChild(btnCorr);
        group.appendChild(btnFl);
        container.appendChild(group);
      });
    }, 0);

    return pane;
  }

  function annotatePost(post, action, correctedLabel, correctedSubtype, idx) {
    var body = {
      post_id: post.id || post.post_id,
      action: action,
      analyst_name: localStorage.getItem(LS_NAME)
    };
    if (correctedLabel) body.corrected_label = correctedLabel;
    if (correctedSubtype) body.corrected_subtype = correctedSubtype;

    apiFetch('/posts/annotate', 'POST', body)
      .then(function () {
        reviewData.splice(idx, 1);
        render();
        showToast('Post ' + action);
      })
      .catch(function () { showToast('Error — try again'); });
  }

  /* ── Stats tab ── */
  function buildStatsTab() {
    var pane = el('div', '');

    if (!statsData) {
      var loading = el('div', 'admin-loading');
      loading.innerHTML = '<span class="spinner"></span> Loading stats...';
      pane.appendChild(loading);
      return pane;
    }

    var grid = el('div', 'stats-grid');
    var cards = [
      { label: 'Total Documents', value: statsData.total_documents || 0 },
      { label: 'Desk Review Items', value: statsData.desk_review_count || 0 },
      { label: 'Events Indexed', value: statsData.events_count || 0 },
      { label: 'Posts Indexed', value: statsData.posts_count || 0 },
      { label: 'Verified Findings', value: statsData.verified_count || 0 },
      { label: 'Pending Verification', value: statsData.pending_count || 0 }
    ];

    cards.forEach(function (c) {
      var card = el('div', 'stat-card');
      card.innerHTML =
        '<div class="stat-card-label">' + c.label + '</div>' +
        '<div class="stat-card-value">' + c.value.toLocaleString() + '</div>';
      grid.appendChild(card);
    });

    pane.appendChild(grid);

    /* Country breakdown if available */
    if (statsData.by_country) {
      var sub = el('div', '');
      sub.style.marginTop = '24px';
      var subTitle = el('h3', '');
      subTitle.textContent = 'By Country';
      subTitle.style.cssText = 'font-family:"DM Serif Display",serif;font-size:18px;margin-bottom:12px;color:#1A3A34';
      sub.appendChild(subTitle);

      var subGrid = el('div', 'stats-grid');
      Object.keys(statsData.by_country).forEach(function (country) {
        var d = statsData.by_country[country];
        var card = el('div', 'stat-card');
        card.innerHTML =
          '<div class="stat-card-label">' + esc(country) + '</div>' +
          '<div class="stat-card-value">' + (d.total || 0).toLocaleString() + '</div>' +
          '<div class="stat-card-sub">' + (d.hate || 0) + ' hate / ' + (d.abusive || 0) + ' abusive</div>';
        subGrid.appendChild(card);
      });
      sub.appendChild(subGrid);
      pane.appendChild(sub);
    }

    return pane;
  }

  /* ── API helpers ── */
  function authHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + localStorage.getItem(LS_KEY)
    };
  }

  function apiFetch(path, method, body) {
    var opts = { method: method || 'GET', headers: authHeaders() };
    if (body) opts.body = JSON.stringify(body);
    return fetch(API_BASE + path, opts).then(function (r) {
      if (!r.ok) throw new Error('API error ' + r.status);
      return r.json();
    });
  }

  function fetchVerify() {
    apiFetch('/verification/pending', 'GET')
      .then(function (data) {
        verifyData = data.findings || data.items || data || [];
        render();
      })
      .catch(function () { verifyData = []; render(); });
  }

  function fetchReview() {
    var params = [];
    if (reviewCountry) params.push('country=' + encodeURIComponent(reviewCountry));
    if (reviewSubtype) params.push('subtype=' + encodeURIComponent(reviewSubtype));
    var qs = params.length ? '?' + params.join('&') : '';

    apiFetch('/posts/review-queue' + qs, 'GET')
      .then(function (data) {
        reviewData = data.posts || data.items || data || [];
        render();
      })
      .catch(function () { reviewData = []; render(); });
  }

  function fetchStats() {
    apiFetch('/knowledge/stats', 'GET')
      .then(function (data) {
        statsData = data;
        render();
      })
      .catch(function () { statsData = {}; render(); });
  }

  function loadInitialData() {
    fetchVerify();
    fetchReview();
    fetchStats();
  }

  /* ── Toast ── */
  function showToast(msg) {
    var existing = document.querySelector('.admin-toast');
    if (existing) existing.remove();
    var t = document.createElement('div');
    t.className = 'admin-toast';
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.classList.add('visible'); });
    setTimeout(function () {
      t.classList.remove('visible');
      setTimeout(function () { t.remove(); }, 200);
    }, 2500);
  }

  /* ── Helpers ── */
  function el(tag, className) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    return e;
  }

  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  /* ── Init ── */
  render();
  if (localStorage.getItem(LS_PIN) && localStorage.getItem(LS_KEY) && localStorage.getItem(LS_NAME)) {
    loadInitialData();
  }

})();

// MERLx — East Africa Disinfo Monitor v5.0
// Narrative-Based Disinformation Tracking + Hate Speech Wheel
// D3.js Radial Threat Wheel + Hate Speech Radial Wheel

(function() {
  'use strict';

  // ─── State ───────────────────────────────────────────────────────
  let allEvents = [];
  let narrativeRef = {};
  let filteredEvents = [];
  let selectedEvent = null;
  let pinnedEvent = null;
  let currentView = 'wheel'; // 'wheel' or 'hatespeech'
  let brushExtent = null;
  let wheelPositions = new Map();
  let wheelZoom = null;
  let wheelG = null;
  let playbackTimer = null;
  let playbackIndex = 0;
  let isPlaying = false;
  let playbackSpeed = 1;

  // Hate Speech state
  let allHSPosts = [];
  let filteredHSPosts = [];
  let hsBrushExtent = null;
  let hsWheelZoom = null;
  let pinnedHSPost = null;

  // Disinfo subtypes (new taxonomy v4)
  const SUBTYPE_LABELS = {
    'propaganda': 'Propaganda',
    'foreign_propaganda': 'Foreign Propaganda',
    'misinformation': 'Misinformation',
    'biased_reporting': 'Biased Reporting',
    'coordinated_campaign': 'Coordinated Campaign',
    'deepfake': 'Deepfake / AI-Generated',
    'incitement': 'Incitement'
  };

  // ─── Country-Based Color System ─────────────────────────────────
  const COUNTRY_COLORS = {
    'Somalia':     { dark: '#1A3A34', light: '#A8C5BC', mid: '#4A7A6E' },
    'South Sudan': { dark: '#CA5D0F', light: '#E8C4A8', mid: '#D9936A' },
    'Kenya':       { dark: '#6B5CA8', light: '#C4BBE0', mid: '#9A8DC8' },
    'Regional':    { dark: '#4A3F6B', light: '#B8B3CC', mid: '#7E76A0' }
  };

  function eventColor(e) {
    const cc = COUNTRY_COLORS[e.country] || COUNTRY_COLORS['Regional'];
    return e.event_type === 'DISINFO' ? cc.dark : cc.light;
  }
  function countryDark(country) {
    return (COUNTRY_COLORS[country] || COUNTRY_COLORS['Regional']).dark;
  }
  function countryLight(country) {
    return (COUNTRY_COLORS[country] || COUNTRY_COLORS['Regional']).light;
  }

  // HS Color: dark = Hate, light = Abusive (per country)
  function hsPostColor(post) {
    const cc = COUNTRY_COLORS[post.c] || COUNTRY_COLORS['Regional'];
    if (post.pr === 'Hate') return cc.dark;
    if (post.pr === 'Questionable') return cc.mid || '#9E9E9E';
    return cc.light;  // Abusive
  }

  const SUBTYPE_COLORS = {
    'propaganda': '#B83A2A',
    'foreign_propaganda': '#4A3F6B',
    'misinformation': '#CA5D0F',
    'biased_reporting': '#9E9E9E',
    'coordinated_campaign': '#1A3A34',
    'deepfake': '#635499',
    'incitement': '#A84B0C'
  };
  const TYPE_COLORS = {
    'DISINFO': '#CA5D0F',
    'CONTEXT': '#C8C3BA'
  };
  const THREAT_COLORS = {
    'P1 CRITICAL': '#B83A2A',
    'P2 HIGH': '#CA5D0F',
    'P3 MODERATE': '#1A3A34'
  };

  const filters = {
    country: new Set(),
    type: new Set(),
    subtype: new Set(),
    narrative: new Set()
  };

  // HS Filters
  const hsFilters = {
    country: new Set(),
    classification: new Set(),
    platform: new Set(),
    toxicity: new Set(),
    subtype: new Set()
  };

  // ─── HS Subtopic Axes (8 NLP-classified categories) ─────────────
  const HS_AXES = [
    'Political Incitement', 'Clan Targeting', 'Religious Incitement',
    'Dehumanisation', 'Anti-Foreign', 'Ethnic Targeting',
    'General Abuse', 'Gendered Violence'
  ];

  // Map subtopic names to axes (identity map — all posts now classified)
  const SUBTOPIC_MAP = {
    'Political Incitement': 'Political Incitement',
    'Clan Targeting': 'Clan Targeting',
    'Religious Incitement': 'Religious Incitement',
    'Dehumanisation': 'Dehumanisation',
    'Anti-Foreign': 'Anti-Foreign',
    'Ethnic Targeting': 'Ethnic Targeting',
    'General Abuse': 'General Abuse',
    'Gendered Violence': 'Gendered Violence'
  };

  function normalizeToxicity(tx) {
    if (!tx || tx === '') return 'low';
    return tx; // 'very_high', 'high', 'medium', 'low'
  }

  function getHSSubtopic(post) {
    if (!post.st || post.st.length === 0) return 'Unclassified';
    const best = post.st.reduce((a, b) => a.s > b.s ? a : b);
    return SUBTOPIC_MAP[best.n] || 'Unclassified';
  }

  function hsEngagement(post) {
    if (!post.en) return 0;
    return (post.en.l || 0) + (post.en.s || 0) + (post.en.c || 0);
  }

  // ─── Playback Constants ─────────────────────────────────────────
  const HEAT_PER_EVENT = 1.0;
  const HEAT_DECAY_PER_WEEK = 0.25;
  const HEAT_VISIBLE_THRESHOLD = 0.05;
  const HEAT_MAX = 5.0;

  // ─── Data Loading ────────────────────────────────────────────────
  async function loadData() {
    const [eventsRes, narrRes, hsRes] = await Promise.all([
      fetch('data/events.json'),
      fetch('data/narratives.json'),
      fetch('data/hate_speech_posts.json')
    ]);
    allEvents = await eventsRes.json();
    narrativeRef = await narrRes.json();
    allHSPosts = await hsRes.json();
    filteredEvents = [...allEvents];
    filteredHSPosts = [...allHSPosts];

    // Show last updated date from most recent data
    const allDates = [
      ...allEvents.map(e => e.last_seen || e.date),
      ...allHSPosts.map(p => p.d)
    ].filter(Boolean).sort();
    const lastDate = allDates[allDates.length - 1];
    if (lastDate) {
      const el = document.getElementById('last-updated');
      if (el) el.textContent = `Updated ${lastDate}`;
    }

    return true;
  }

  // ─── Filtering ───────────────────────────────────────────────────
  function applyFilters() {
    filteredEvents = allEvents.filter(e => {
      if (filters.country.size && !filters.country.has(e.country)) return false;
      if (filters.type.size && !filters.type.has(e.event_type)) return false;
      if (filters.subtype.size) {
        if (!e.disinfo_subtype || !filters.subtype.has(e.disinfo_subtype)) return false;
      }
      if (filters.narrative.size) {
        const narrs = e.disinfo_narratives || [];
        if (!narrs.some(n => filters.narrative.has(n))) return false;
      }
      if (brushExtent) {
        const d = new Date(e.date);
        if (d < brushExtent[0] || d > brushExtent[1]) return false;
      }
      return true;
    });
    updateStats();
    if (currentView === 'wheel') renderWheel();
  }

  function applyHSFilters() {
    filteredHSPosts = allHSPosts.filter(p => {
      if (hsFilters.country.size && !hsFilters.country.has(p.c)) return false;
      if (hsFilters.classification.size && !hsFilters.classification.has(p.pr)) return false;
      if (hsFilters.platform.size && !hsFilters.platform.has(p.p)) return false;
      if (hsFilters.toxicity.size) {
        const tox = normalizeToxicity(p.tx);
        if (!hsFilters.toxicity.has(tox)) return false;
      }
      if (hsFilters.subtype.size) {
        const st = getHSSubtopic(p);
        if (st === 'Unclassified') return false;
        if (!hsFilters.subtype.has(st)) return false;
      }
      if (hsBrushExtent) {
        const d = new Date(p.d);
        if (d < hsBrushExtent[0] || d > hsBrushExtent[1]) return false;
      }
      return true;
    });
    updateHSStats();
    if (currentView === 'hatespeech') renderHSWheel();
  }

  function toggleFilter(category, value) {
    if (filters[category].has(value)) filters[category].delete(value);
    else filters[category].add(value);
    applyFilters();
    updateFilterUI();
  }

  function toggleHSFilter(category, value) {
    if (hsFilters[category].has(value)) hsFilters[category].delete(value);
    else hsFilters[category].add(value);
    applyHSFilters();
    updateHSFilterUI();
  }

  function resetFilters() {
    if (currentView === 'wheel') {
      Object.keys(filters).forEach(k => filters[k].clear());
      brushExtent = null;
      scrubberZoomState = null;
      applyFilters();
      updateFilterUI();
      renderScrubber();
    } else {
      Object.keys(hsFilters).forEach(k => hsFilters[k].clear());
      hsBrushExtent = null;
      hsScrubberZoomState = null;
      applyHSFilters();
      updateHSFilterUI();
      renderHSScrubber();
    }
  }

  // ─── Filter UI ───────────────────────────────────────────────────
  function buildFilterUI() {
    // Countries
    const countries = d3.rollup(allEvents, v => v.length, d => d.country);
    const countryDiv = document.getElementById('filter-country');
    countryDiv.innerHTML = '';
    [...countries.entries()].sort((a, b) => b[1] - a[1]).forEach(([country, count]) => {
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:${countryDark(country)}"></span>
        <span>${country}</span><span class="filter-count">${count}</span>`;
      item.addEventListener('click', () => toggleFilter('country', country));
      item.dataset.value = country;
      item.dataset.category = 'country';
      countryDiv.appendChild(item);
    });

    // Event Type
    const types = d3.rollup(allEvents, v => v.length, d => d.event_type);
    const typeDiv = document.getElementById('filter-type');
    typeDiv.innerHTML = '';
    ['DISINFO', 'CONTEXT'].forEach(type => {
      const count = types.get(type) || 0;
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:${TYPE_COLORS[type]}"></span>
        <span>${type === 'DISINFO' ? 'Disinformation' : 'Context'}</span><span class="filter-count">${count}</span>`;
      item.addEventListener('click', () => toggleFilter('type', type));
      item.dataset.value = type;
      item.dataset.category = 'type';
      typeDiv.appendChild(item);
    });

    // Disinfo Subtypes
    const subtypes = {};
    allEvents.forEach(e => {
      if (e.disinfo_subtype) subtypes[e.disinfo_subtype] = (subtypes[e.disinfo_subtype] || 0) + 1;
    });
    const subtypeDiv = document.getElementById('filter-subtype');
    subtypeDiv.innerHTML = '';
    Object.entries(subtypes).sort((a, b) => b[1] - a[1]).forEach(([st, count]) => {
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:#9E9E9E"></span>
        <span>${SUBTYPE_LABELS[st] || st}</span><span class="filter-count">${count}</span>`;
      item.addEventListener('click', () => toggleFilter('subtype', st));
      item.dataset.value = st;
      item.dataset.category = 'subtype';
      subtypeDiv.appendChild(item);
    });

    // Narratives
    const narrCounts = {};
    allEvents.forEach(e => {
      (e.disinfo_narratives || []).forEach(n => {
        narrCounts[n] = (narrCounts[n] || 0) + 1;
      });
    });
    const narrDiv = document.getElementById('filter-narrative');
    narrDiv.innerHTML = '';
    Object.entries(narrCounts).sort((a, b) => b[1] - a[1]).forEach(([nid, count]) => {
      const narr = narrativeRef[nid];
      if (!narr) return;
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span>${narr.short_name || narr.name}</span><span class="filter-count">${count}</span>`;
      item.addEventListener('click', () => toggleFilter('narrative', nid));
      item.dataset.value = nid;
      item.dataset.category = 'narrative';
      narrDiv.appendChild(item);
    });
  }

  function buildHSFilterUI() {
    const PLATFORM_LABELS = { 'x': 'X', 'facebook': 'Facebook', 'tiktok': 'TikTok' };

    // Country
    const countries = d3.rollup(allHSPosts, v => v.length, d => d.c);
    const countryDiv = document.getElementById('hs-filter-country');
    countryDiv.innerHTML = '';
    [...countries.entries()].sort((a, b) => b[1] - a[1]).forEach(([country, count]) => {
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:${countryDark(country)}"></span>
        <span>${country}</span><span class="filter-count">${count.toLocaleString()}</span>`;
      item.addEventListener('click', () => toggleHSFilter('country', country));
      item.dataset.value = country;
      item.dataset.category = 'country';
      countryDiv.appendChild(item);
    });

    // Classification
    const classes = d3.rollup(allHSPosts, v => v.length, d => d.pr);
    const classDiv = document.getElementById('hs-filter-class');
    classDiv.innerHTML = '';
    ['Hate', 'Abusive', 'Questionable'].forEach(cls => {
      const count = classes.get(cls) || 0;
      const color = cls === 'Hate' ? '#B83A2A' : cls === 'Questionable' ? '#9E9E9E' : '#8071BC';
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:${color}"></span>
        <span>${cls}</span><span class="filter-count">${count.toLocaleString()}</span>`;
      item.addEventListener('click', () => toggleHSFilter('classification', cls));
      item.dataset.value = cls;
      item.dataset.category = 'classification';
      classDiv.appendChild(item);
    });

    // Platform
    const platforms = d3.rollup(allHSPosts, v => v.length, d => d.p);
    const platDiv = document.getElementById('hs-filter-platform');
    platDiv.innerHTML = '';
    [...platforms.entries()].sort((a, b) => b[1] - a[1]).forEach(([plat, count]) => {
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:#9E9E9E"></span>
        <span>${PLATFORM_LABELS[plat] || plat}</span><span class="filter-count">${count.toLocaleString()}</span>`;
      item.addEventListener('click', () => toggleHSFilter('platform', plat));
      item.dataset.value = plat;
      item.dataset.category = 'platform';
      platDiv.appendChild(item);
    });

    // Toxicity
    const toxCounts = { high: 0, medium: 0, low: 0 };
    allHSPosts.forEach(p => {
      const t = normalizeToxicity(p.tx);
      toxCounts[t] = (toxCounts[t] || 0) + 1;
    });
    const toxDiv = document.getElementById('hs-filter-toxicity');
    toxDiv.innerHTML = '';
    const toxColors = { very_high: '#7A1A1A', high: '#B83A2A', medium: '#CA5D0F', low: '#1A3A34' };
    ['very_high', 'high', 'medium', 'low'].forEach(tox => {
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span class="filter-dot" style="background:${toxColors[tox]}"></span>
        <span>${tox === 'very_high' ? 'Very High' : tox.charAt(0).toUpperCase() + tox.slice(1)}</span><span class="filter-count">${(toxCounts[tox] || 0).toLocaleString()}</span>`;
      item.addEventListener('click', () => toggleHSFilter('toxicity', tox));
      item.dataset.value = tox;
      item.dataset.category = 'toxicity';
      toxDiv.appendChild(item);
    });

    // HS Subtype
    const stCounts = {};
    allHSPosts.forEach(p => {
      const st = getHSSubtopic(p);
      if (st !== 'Unclassified') stCounts[st] = (stCounts[st] || 0) + 1;
    });
    const stDiv = document.getElementById('hs-filter-subtype');
    stDiv.innerHTML = '';
    Object.entries(stCounts).sort((a, b) => b[1] - a[1]).forEach(([st, count]) => {
      const item = document.createElement('div');
      item.className = 'filter-item active';
      item.innerHTML = `<span>${st}</span><span class="filter-count">${count}</span>`;
      item.addEventListener('click', () => toggleHSFilter('subtype', st));
      item.dataset.value = st;
      item.dataset.category = 'subtype';
      stDiv.appendChild(item);
    });
  }

  function updateFilterUI() {
    // Recount based on filtered events
    const fCountry = d3.rollup(filteredEvents, v => v.length, d => d.country);
    const fType = d3.rollup(filteredEvents, v => v.length, d => d.event_type);
    const fSubtype = {};
    const fNarr = {};
    filteredEvents.forEach(e => {
      if (e.disinfo_subtype) fSubtype[e.disinfo_subtype] = (fSubtype[e.disinfo_subtype] || 0) + 1;
      (e.disinfo_narratives || []).forEach(n => {
        fNarr[n] = (fNarr[n] || 0) + 1;
      });
    });

    document.querySelectorAll('#disinfo-filters .filter-item').forEach(item => {
      const cat = item.dataset.category;
      const val = item.dataset.value;
      if (!cat || !val) return;
      const isActive = filters[cat].size === 0 || filters[cat].has(val);
      item.classList.toggle('active', isActive);

      // Update count to reflect filtered data
      const countEl = item.querySelector('.filter-count');
      if (!countEl) return;
      let count = 0;
      if (cat === 'country') count = fCountry.get(val) || 0;
      else if (cat === 'type') count = fType.get(val) || 0;
      else if (cat === 'subtype') count = fSubtype[val] || 0;
      else if (cat === 'narrative') count = fNarr[val] || 0;
      countEl.textContent = count;
    });
  }

  function updateHSFilterUI() {
    // Recount based on filtered posts
    const fCountry = d3.rollup(filteredHSPosts, v => v.length, d => d.c);
    const fClass = d3.rollup(filteredHSPosts, v => v.length, d => d.pr);
    const fPlat = d3.rollup(filteredHSPosts, v => v.length, d => d.p);
    const fTox = {};
    const fSub = {};
    filteredHSPosts.forEach(p => {
      const t = normalizeToxicity(p.tx);
      fTox[t] = (fTox[t] || 0) + 1;
      const st = getHSSubtopic(p);
      if (st !== 'Unclassified') fSub[st] = (fSub[st] || 0) + 1;
    });

    document.querySelectorAll('#hs-filters .filter-item').forEach(item => {
      const cat = item.dataset.category;
      const val = item.dataset.value;
      if (!cat || !val) return;
      const isActive = hsFilters[cat].size === 0 || hsFilters[cat].has(val);
      item.classList.toggle('active', isActive);

      // Update count to reflect filtered data
      const countEl = item.querySelector('.filter-count');
      if (!countEl) return;
      let count = 0;
      if (cat === 'country') count = fCountry.get(val) || 0;
      else if (cat === 'classification') count = fClass.get(val) || 0;
      else if (cat === 'platform') count = fPlat.get(val) || 0;
      else if (cat === 'toxicity') count = fTox[val] || 0;
      else if (cat === 'subtype') count = fSub[val] || 0;
      countEl.textContent = count.toLocaleString();
    });
  }

  function updateStats() {
    document.getElementById('stat-total').textContent = filteredEvents.length;
    document.getElementById('stat-disinfo').textContent = filteredEvents.filter(e => e.event_type === 'DISINFO').length;
    document.getElementById('stat-context').textContent = filteredEvents.filter(e => e.event_type === 'CONTEXT').length;
  }

  function updateHSStats() {
    document.getElementById('stat-hs-total').textContent = filteredHSPosts.length.toLocaleString();
    document.getElementById('stat-hs-hate').textContent = filteredHSPosts.filter(p => p.pr === 'Hate').length.toLocaleString();
    document.getElementById('stat-hs-abusive').textContent = filteredHSPosts.filter(p => p.pr === 'Abusive').length.toLocaleString();
    document.getElementById('stat-hs-questionable').textContent = filteredHSPosts.filter(p => p.pr === 'Questionable').length.toLocaleString();
  }

  // ─── Tooltip ─────────────────────────────────────────────────────
  let tooltipEl;
  function createTooltip() {
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'tooltip';
    document.body.appendChild(tooltipEl);
  }
  function showTooltip(event, d) {
    const typeLabel = d.event_type === 'DISINFO'
      ? (SUBTYPE_LABELS[d.disinfo_subtype] || 'Disinfo')
      : 'Context';
    tooltipEl.innerHTML = `<div class="tooltip-headline">${d.headline}</div>
      <div class="tooltip-meta">${d.date} · ${d.country} · ${typeLabel} · ${d.threat_level}</div>`;
    tooltipEl.classList.add('visible');
    positionTooltip(event);
  }
  function showHSTooltip(event, post) {
    const PLAT = { 'x': 'X', 'facebook': 'Facebook', 'tiktok': 'TikTok' };
    const textPreview = post.t ? post.t.substring(0, 120) + (post.t.length > 120 ? '...' : '') : '(no text)';
    tooltipEl.innerHTML = `<div class="tooltip-headline">${textPreview}</div>
      <div class="tooltip-meta">${post.d} · ${post.c} · ${PLAT[post.p] || post.p} · ${post.pr} · ${post.a}</div>`;
    tooltipEl.classList.add('visible');
    positionTooltip(event);
  }
  function showHSClusterTooltip(event, cluster) {
    tooltipEl.innerHTML = `<div class="tooltip-headline">${cluster.country} — ${cluster.toxicity} toxicity</div>
      <div class="tooltip-meta">${cluster.month} · ${cluster.count} posts · ${cluster.classification}</div>`;
    tooltipEl.classList.add('visible');
    positionTooltip(event);
  }
  function positionTooltip(event) {
    const rect = tooltipEl.getBoundingClientRect();
    let x = event.clientX + 12;
    let y = event.clientY - 12;
    if (x + rect.width > window.innerWidth) x = event.clientX - rect.width - 12;
    if (y + rect.height > window.innerHeight) y = event.clientY - rect.height - 12;
    tooltipEl.style.left = x + 'px';
    tooltipEl.style.top = y + 'px';
  }
  function hideTooltip() {
    tooltipEl.classList.remove('visible');
  }

  // ─── Detail Panel (Disinfo) ─────────────────────────────────────
  function showDetail(d) {
    // Hide HS detail if visible
    document.getElementById('hs-detail-content').classList.add('hidden');
    const placeholder = document.getElementById('detail-placeholder');
    const content = document.getElementById('detail-content');
    placeholder.style.display = 'none';
    content.classList.remove('hidden');

    const typeEl = document.getElementById('detail-type');
    typeEl.textContent = d.event_type === 'DISINFO' ? 'Disinfo' : 'Context';
    typeEl.className = 'detail-badge ' + (d.event_type === 'DISINFO' ? 'disinfo' : 'context');

    const subtypeEl = document.getElementById('detail-subtype');
    if (d.disinfo_subtype) {
      subtypeEl.textContent = SUBTYPE_LABELS[d.disinfo_subtype] || d.disinfo_subtype;
      subtypeEl.className = 'detail-badge subtype';
      subtypeEl.style.display = '';
      subtypeEl.style.background = (SUBTYPE_COLORS[d.disinfo_subtype] || '#9E9E9E') + '1A';
      subtypeEl.style.color = SUBTYPE_COLORS[d.disinfo_subtype] || '#9E9E9E';
    } else {
      subtypeEl.style.display = 'none';
    }

    const countryEl = document.getElementById('detail-country');
    countryEl.textContent = d.country;
    countryEl.className = 'detail-badge country';

    document.getElementById('detail-headline').textContent = d.headline;
    const dateText = d.last_seen && d.last_seen !== d.date
      ? `${d.date} \u2192 ${d.last_seen}`
      : d.date;
    document.getElementById('detail-date').textContent = dateText;
    document.getElementById('detail-summary').textContent = d.summary;

    // Show event status and observation count if available
    const statusEl = document.getElementById('detail-status');
    if (statusEl) {
      if (d.observations && d.observations.length > 1) {
        const statusColor = d.status === 'active' ? '#CA5D0F' : d.status === 'dormant' ? '#666' : '#1A3A34';
        statusEl.innerHTML = `<span style="color:${statusColor};font-size:12px">${d.status || 'active'}</span> \u00b7 <span style="font-size:12px">${d.observation_count || d.observations.length} observations</span>`;
        statusEl.style.display = '';
      } else {
        statusEl.style.display = 'none';
      }
    }

    // Claims
    const claimsSection = document.getElementById('detail-claims-section');
    const claimsDiv = document.getElementById('detail-claims');
    const claims = d.extracted_claims || [];
    if (claims.length > 0) {
      claimsSection.style.display = '';
      claimsDiv.innerHTML = claims.map(c =>
        `<div class="claim-item"><span class="claim-bullet">\u2716</span> ${c}</div>`
      ).join('');
    } else {
      claimsSection.style.display = 'none';
    }

    // Reach
    const reachSection = document.getElementById('detail-reach-section');
    const reachDiv = document.getElementById('detail-reach');
    const reach = d.reach_data;
    if (reach && Object.keys(reach).length > 0) {
      reachSection.style.display = '';
      let reachHTML = '';
      const metricLabels = {
        views: 'Views', mentions: 'Mentions', impressions: 'Impressions',
        engagement: 'Engagement', shares: 'Shares', comments: 'Comments',
        trend_duration: 'Trend Duration', notes: 'Notes',
        channels: 'Distribution Channels', speed_of_spread: 'Speed',
        diaspora_amplification: 'Diaspora Amplification',
        facebook: 'Facebook', whatsapp: 'WhatsApp', instagram: 'Instagram',
        reach_note: 'Note', total_views: 'Total Views',
        total_impressions: 'Total Impressions', tiktok: 'TikTok'
      };
      for (const [key, val] of Object.entries(reach)) {
        if (val === null || val === undefined || key.startsWith('_')) continue;
        const label = metricLabels[key] || key.replace(/_/g, ' ');
        const valStr = typeof val === 'object' ? JSON.stringify(val) : String(val);
        reachHTML += `<div class="reach-item"><span class="reach-label">${label}:</span> <span class="reach-value">${valStr}</span></div>`;
      }
      reachDiv.innerHTML = reachHTML;
    } else {
      reachSection.style.display = 'none';
    }

    // Observation timeline
    const obsSection = document.getElementById('detail-observations-section');
    const obsDiv = document.getElementById('detail-observations');
    if (obsSection && d.observations && d.observations.length > 1) {
      obsSection.style.display = '';
      const _daysBetween = (d1, d2) => { const a = new Date(d1), b = new Date(d2); return Math.max(1, Math.round(Math.abs(b - a) / 86400000)); };
      let obsHTML = `<div style="font-size:11px;color:#9E9E9E;margin-bottom:8px">${d.observation_count || d.observations.length} sightings over ${_daysBetween(d.date, d.last_seen || d.date)} days</div>`;
      // Activity bar chart (last 30 days)
      obsHTML += '<div style="display:flex;gap:1px;align-items:flex-end;height:30px;margin-bottom:4px">';
      const _today = new Date();
      for (let i = 29; i >= 0; i--) {
        const day = new Date(_today);
        day.setDate(day.getDate() - i);
        const ds = day.toISOString().slice(0, 10);
        const dayObs = d.observations.filter(o => o.date === ds);
        const h = dayObs.length > 0 ? Math.max(6, dayObs.length * 10) : 2;
        const color = dayObs.length > 0 ? '#CA5D0F' : 'rgba(255,255,255,0.05)';
        obsHTML += `<div title="${ds}: ${dayObs.length} sighting(s)" style="flex:1;height:${h}px;background:${color};border-radius:1px"></div>`;
      }
      obsHTML += '</div>';
      // List recent observations
      const recentObs = d.observations.slice(-5).reverse();
      obsHTML += '<div style="margin-top:8px">';
      for (const obs of recentObs) {
        const urlLink = obs.url ? `<a href="${obs.url}" target="_blank" style="color:#CA5D0F;font-size:10px">\u2197 source</a>` : '';
        obsHTML += `<div style="padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:11px">
          <span style="color:#9E9E9E">${obs.date}</span> ${obs.summary || ''} ${urlLink}
        </div>`;
      }
      obsHTML += '</div>';
      obsDiv.innerHTML = obsHTML;
    } else if (obsSection) {
      obsSection.style.display = 'none';
    }

    // Narratives
    const narrSection = document.getElementById('detail-narratives-section');
    const narrDiv = document.getElementById('detail-narratives');
    const narrs = d.disinfo_narratives || [];
    if (narrs.length > 0) {
      narrSection.style.display = '';
      narrDiv.innerHTML = '';
      narrs.forEach(nid => {
        const narr = narrativeRef[nid];
        if (!narr) return;
        const card = document.createElement('div');
        card.className = 'narrative-card';
        const exClaims = narr.example_claims || [];
        const claimsHtml = exClaims.length ? `<div class="narrative-card-claims"><div class="narrative-card-claims-title">Key claims tracked:</div>${exClaims.slice(0,3).map(c => `<div class="narrative-claim-item">\u2022 ${c}</div>`).join('')}</div>` : '';
        const ncPrefix = nid.split('-')[1];
        const ncCountryMap = { 'SS': 'South Sudan', 'SO': 'Somalia', 'KE': 'Kenya', 'FP': 'Regional' };
        const ncColor = countryDark(ncCountryMap[ncPrefix] || 'Regional');
        card.innerHTML = `<div class="narrative-card-header">
          <span class="narrative-card-dot" style="background:${ncColor}"></span>
          <span class="narrative-card-name">${narr.name}</span>
        </div>
        <div class="narrative-card-desc">${narr.description}</div>
        ${claimsHtml}
        ${narr.competing_narratives?.length ? `<div class="narrative-card-competing">Competing: ${narr.competing_narratives.map(cn => narrativeRef[cn]?.short_name || cn).join(', ')}</div>` : ''}`;
        card.addEventListener('click', () => {
          filters.narrative.clear();
          filters.narrative.add(nid);
          applyFilters();
          updateFilterUI();
        });
        narrDiv.appendChild(card);
      });
    } else {
      narrSection.style.display = 'none';
    }

    // Actors
    const actorsDiv = document.getElementById('detail-actors');
    actorsDiv.innerHTML = d.actors.map(a => `<span class="detail-tag">${a}</span>`).join('');

    // Platforms
    const platformsDiv = document.getElementById('detail-platforms');
    platformsDiv.innerHTML = d.platforms.map(p => `<span class="detail-tag">${p}</span>`).join('');

    // Related
    const relatedSection = document.getElementById('detail-related-section');
    const relatedDiv = document.getElementById('detail-related');
    if (d.related_events && d.related_events.length > 0) {
      relatedSection.style.display = '';
      relatedDiv.innerHTML = '';
      d.related_events.slice(0, 8).forEach(relId => {
        const rel = allEvents.find(e => e.id === relId);
        if (rel) {
          const link = document.createElement('a');
          link.className = 'related-link';
          link.textContent = `${relId}: ${rel.headline.substring(0, 60)}...`;
          link.addEventListener('click', () => {
            pinnedEvent = rel;
            showDetail(rel);
            highlightEvent(rel);
          });
          relatedDiv.appendChild(link);
        }
      });
    } else {
      relatedSection.style.display = 'none';
    }

    // Sources
    const sourcesSection = document.getElementById('detail-sources-section');
    const sourcesDiv = document.getElementById('detail-sources');
    if (d.sources && d.sources.length > 0) {
      sourcesSection.style.display = '';
      sourcesDiv.innerHTML = d.sources.map(s =>
        s.url ? `<a class="source-link" href="${s.url}" target="_blank" rel="noopener">${s.publisher}</a>` :
        `<span class="source-link">${s.publisher}</span>`
      ).join('');
    } else {
      sourcesSection.style.display = 'none';
    }

    document.getElementById('detail-panel').classList.add('open');
  }

  // ─── Detail Panel (HS) ──────────────────────────────────────────
  function showHSDetail(post) {
    const PLAT = { 'x': 'X', 'facebook': 'Facebook', 'tiktok': 'TikTok' };
    // Hide disinfo detail
    document.getElementById('detail-content').classList.add('hidden');
    const placeholder = document.getElementById('detail-placeholder');
    const content = document.getElementById('hs-detail-content');
    placeholder.style.display = 'none';
    content.classList.remove('hidden');

    // Header badges
    const header = document.getElementById('hs-detail-header');
    const badgeColor = post.pr === 'Hate' ? 'background:rgba(184,58,42,0.1);color:#B83A2A'
      : post.pr === 'Questionable' ? 'background:rgba(158,158,158,0.12);color:#9E9E9E'
      : 'background:rgba(128,113,188,0.12);color:#8071BC';
    const confPct = Math.round(post.co * 100);
    const toxLabel = normalizeToxicity(post.tx);
    const toxColors = { very_high: 'background:rgba(122,26,26,0.12);color:#7A1A1A', high: 'background:rgba(184,58,42,0.1);color:#B83A2A', medium: 'background:rgba(202,93,15,0.1);color:#CA5D0F', low: 'background:rgba(26,58,52,0.1);color:#1A3A34' };
    const toxDisplay = toxLabel === 'very_high' ? 'very high' : toxLabel;
    header.innerHTML = `
      <span class="detail-badge" style="${badgeColor}">${post.pr} (${confPct}%)</span>
      <span class="detail-badge" style="${toxColors[toxLabel] || toxColors.low}">${toxDisplay} toxicity</span>
      <span class="detail-badge country">${post.c}</span>
    `;

    document.getElementById('hs-detail-headline').textContent = post.a || 'Unknown';
    document.getElementById('hs-detail-date').textContent = `${post.d} · ${PLAT[post.p] || post.p}`;
    document.getElementById('hs-detail-text').textContent = post.t || '(no text)';

    // Engagement
    const engSection = document.getElementById('hs-detail-engagement-section');
    const engDiv = document.getElementById('hs-detail-engagement');
    if (post.en && (post.en.l || post.en.s || post.en.c)) {
      engSection.style.display = '';
      engDiv.innerHTML = `
        <div class="reach-item"><span class="reach-label">Likes:</span> <span class="reach-value">${post.en.l || 0}</span></div>
        <div class="reach-item"><span class="reach-label">Shares:</span> <span class="reach-value">${post.en.s || 0}</span></div>
        <div class="reach-item"><span class="reach-label">Comments:</span> <span class="reach-value">${post.en.c || 0}</span></div>
      `;
    } else {
      engSection.style.display = 'none';
    }

    // Toxicity dimensions
    const toxDimSection = document.getElementById('hs-detail-toxdim-section');
    const toxDimDiv = document.getElementById('hs-detail-toxdim');
    if (toxDimSection && post.txd) {
      const dimLabels = { sev: 'Severe Toxicity', ins: 'Insult', idt: 'Identity Attack', thr: 'Threat' };
      const dimColors = { very_high: '#7A1A1A', high: '#B83A2A', medium: '#CA5D0F', low: '#1A3A34' };
      const dims = Object.entries(post.txd).filter(([k,v]) => v && dimLabels[k]);
      if (dims.length > 0) {
        toxDimSection.style.display = '';
        toxDimDiv.innerHTML = dims.map(([k, v]) => {
          const label = dimLabels[k];
          const color = dimColors[v] || '#9E9E9E';
          const display = v === 'very_high' ? 'Very High' : v.charAt(0).toUpperCase() + v.slice(1);
          return `<div class="reach-item"><span class="reach-label">${label}:</span> <span class="reach-value" style="color:${color}">${display}</span></div>`;
        }).join('');
      } else {
        toxDimSection.style.display = 'none';
      }
    } else if (toxDimSection) {
      toxDimSection.style.display = 'none';
    }

    // Subtopics
    const stSection = document.getElementById('hs-detail-subtopics-section');
    const stDiv = document.getElementById('hs-detail-subtopics');
    if (post.st && post.st.length > 0) {
      stSection.style.display = '';
      stDiv.innerHTML = post.st.map(s =>
        `<span class="detail-tag">${s.n} (${Math.round(s.s * 100)}%)</span>`
      ).join('');
    } else {
      stSection.style.display = 'none';
    }

    // LLM Explanation
    const expSection = document.getElementById('hs-detail-explanation-section');
    const expDiv = document.getElementById('hs-detail-explanation');
    if (expSection) {
      if (post.exp && post.exp.length > 5) {
        expSection.style.display = '';
        expDiv.textContent = post.exp;
      } else {
        expSection.style.display = 'none';
      }
    }

    // QC section removed — classification now driven by LLM QA into pr field
    const qcSection = document.getElementById('hs-detail-qc-section');
    if (qcSection) qcSection.style.display = 'none';

    // Model agreement
    const modelSection = document.getElementById('hs-detail-model-section');
    const modelP = document.getElementById('hs-detail-model');
    if (post.ma && post.ma > 0) {
      modelSection.style.display = '';
      modelP.textContent = `${post.ma}/3 models agree`;
    } else {
      modelSection.style.display = 'none';
    }

    // Link
    const linkDiv = document.getElementById('hs-detail-link');
    linkDiv.innerHTML = post.l
      ? `<a class="source-link" href="${post.l}" target="_blank" rel="noopener">${post.l.substring(0, 60)}...</a>`
      : '<span class="source-link">No link available</span>';

    document.getElementById('detail-panel').classList.add('open');
  }

  function hideDetail() {
    pinnedEvent = null;
    pinnedHSPost = null;
    document.getElementById('detail-placeholder').style.display = '';
    document.getElementById('detail-content').classList.add('hidden');
    document.getElementById('hs-detail-content').classList.add('hidden');
    document.getElementById('detail-panel').classList.remove('open');
    clearHighlight();
  }

  function highlightEvent(d) {
    d3.selectAll('.event-dot')
      .classed('selected', e => e && e.id === d.id)
      .classed('dimmed', e => e && e.id !== d.id && !(d.related_events && d.related_events.includes(e.id)));
    d3.selectAll('.event-link')
      .classed('visible', function(link) {
        if (!link || !d.related_events) return false;
        return (link.source === d.id || link.target === d.id);
      })
      .each(function(link) {
        if (!link || !d.related_events) return;
        if (link.source === d.id || link.target === d.id) {
          const el = d3.select(this);
          const totalLen = this.getTotalLength ? this.getTotalLength() : 100;
          el.attr('stroke-dasharray', totalLen)
            .attr('stroke-dashoffset', totalLen)
            .transition().duration(600).ease(d3.easeCubicOut)
            .attr('stroke-dashoffset', 0);
        }
      });
  }

  function clearHighlight() {
    d3.selectAll('.event-dot').classed('selected', false).classed('dimmed', false);
    d3.selectAll('.event-link').classed('visible', false)
      .attr('stroke-dasharray', null).attr('stroke-dashoffset', null);
    d3.selectAll('.hs-dot').classed('selected', false).classed('dimmed', false);
  }

  // ─── Get narrative list for wheel segments ──────────────────────
  function getUsedNarratives() {
    const narrCounts = {};
    filteredEvents.forEach(e => {
      (e.disinfo_narratives || []).forEach(n => {
        narrCounts[n] = (narrCounts[n] || 0) + 1;
      });
    });
    return Object.entries(narrCounts)
      .sort((a, b) => b[1] - a[1])
      .filter(([nid]) => narrativeRef[nid]);
  }
  function getUsedNarrativeIds() {
    return getUsedNarratives().map(d => d[0]);
  }

  // ─── RADIAL THREAT WHEEL (DISINFO) ──────────────────────────────
  function renderWheel() {
    const svg = d3.select('#wheel-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('panel-wheel');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const cx = width / 2;
    const cy = height / 2;
    const mobilePad = window.innerWidth <= 900 ? 95 : 40;
    const maxRadius = Math.min(cx, cy) - mobilePad;
    const innerRadius = maxRadius * 0.12;

    // Defs
    const defs = svg.append('defs');
    const glowFilter = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'blur');
    const merge = glowFilter.append('feMerge');
    merge.append('feMergeNode').attr('in', 'blur');
    merge.append('feMergeNode').attr('in', 'SourceGraphic');
    const linkGrad = defs.append('linearGradient').attr('id', 'link-gradient');
    linkGrad.append('stop').attr('offset', '0%').attr('stop-color', '#1A3A34').attr('stop-opacity', 0.5);
    linkGrad.append('stop').attr('offset', '50%').attr('stop-color', '#8071BC').attr('stop-opacity', 0.3);
    linkGrad.append('stop').attr('offset', '100%').attr('stop-color', '#1A3A34').attr('stop-opacity', 0.5);

    const zoomGroup = svg.append('g').attr('class', 'wheel-zoom-group');
    wheelG = zoomGroup.append('g').attr('transform', `translate(${cx},${cy})`);
    const g = wheelG;

    wheelZoom = d3.zoom()
      .scaleExtent([0.5, 6])
      .on('zoom', function(event) { zoomGroup.attr('transform', event.transform); });
    svg.call(wheelZoom);
    svg.call(wheelZoom.transform, d3.zoomIdentity);
    svg.append('text')
      .attr('class', 'zoom-hint')
      .attr('x', width - 12).attr('y', height - 12)
      .attr('text-anchor', 'end')
      .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '9px')
      .style('fill', '#9E9E9E').style('opacity', 0.6)
      .text(window.innerWidth <= 900 ? 'Pinch to zoom · Drag to pan' : 'Scroll to zoom · Drag to pan · Double-click to reset');
    svg.on('dblclick.zoom', function() {
      svg.transition().duration(500).call(wheelZoom.transform, d3.zoomIdentity);
    });

    // Ring guides
    const rings = [
      { r: innerRadius + (maxRadius - innerRadius) * 0.15, label: 'P1 CRITICAL', color: '#B83A2A' },
      { r: innerRadius + (maxRadius - innerRadius) * 0.50, label: 'P2 HIGH', color: '#CA5D0F' },
      { r: innerRadius + (maxRadius - innerRadius) * 0.85, label: 'P3 MODERATE', color: '#1A3A34' }
    ];
    rings.forEach(ring => {
      g.append('circle').attr('r', ring.r).attr('class', 'wheel-ring')
        .style('stroke', ring.color).style('opacity', 0.15);
      g.append('text').attr('x', 5).attr('y', -ring.r - 3).attr('class', 'wheel-ring-label')
        .style('fill', ring.color).style('opacity', 0.6).text(ring.label);
    });

    // Narrative segments
    const usedNarrativesWithCounts = getUsedNarratives();
    if (usedNarrativesWithCounts.length === 0) return;
    const usedNarratives = usedNarrativesWithCounts.map(d => d[0]);
    const narrWeights = new Map(usedNarrativesWithCounts);
    const totalWeight = usedNarrativesWithCounts.reduce((s, d) => s + d[1], 0);
    const segmentPad = 0.02;
    const MIN_ANGLE = 0.12;
    const totalPad = segmentPad * 2 * usedNarratives.length;
    const totalMinAngle = MIN_ANGLE * usedNarratives.length;
    const availAngle = 2 * Math.PI - totalPad;
    const useMin = totalMinAngle >= availAngle;
    const narrAngles = [];
    let cumAngle = -Math.PI / 2;
    usedNarrativesWithCounts.forEach(([nid, count]) => {
      let segAngle;
      if (useMin) {
        segAngle = (2 * Math.PI) / usedNarratives.length;
      } else {
        const extraAngle = availAngle - totalMinAngle;
        segAngle = MIN_ANGLE + (count / totalWeight) * extraAngle + segmentPad * 2;
      }
      narrAngles.push({ nid, start: cumAngle + segmentPad, end: cumAngle + segAngle - segmentPad, count });
      cumAngle += segAngle;
    });

    narrAngles.forEach(({ nid, start: startAngle, end: endAngle }) => {
      const narr = narrativeRef[nid];
      const x1 = Math.cos(startAngle) * innerRadius;
      const y1 = Math.sin(startAngle) * innerRadius;
      const x2 = Math.cos(startAngle) * maxRadius;
      const y2 = Math.sin(startAngle) * maxRadius;
      g.append('line').attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2)
        .style('stroke', '#D5D0C7').style('opacity', 0.35);

      const midAngle = (startAngle + endAngle) / 2;
      const labelR = maxRadius + 16;
      const lx = Math.cos(midAngle) * labelR;
      const ly = Math.sin(midAngle) * labelR;
      const degAngle = midAngle * 180 / Math.PI;
      const flip = degAngle > 90 || degAngle < -90;
      const textAnchor = flip ? 'end' : 'start';
      const rotation = flip ? degAngle + 180 : degAngle;
      const shortName = narr.short_name || narr.name;
      const displayName = shortName.length > 20 ? shortName.substring(0, 18) + '...' : shortName;
      g.append('text').attr('class', 'wheel-segment-label')
        .attr('transform', `translate(${lx},${ly}) rotate(${rotation})`)
        .attr('text-anchor', textAnchor).attr('dominant-baseline', 'middle')
        .text(displayName);
    });

    // Map events to positions
    const positions = new Map();
    const eventsByNarr = new Map();
    filteredEvents.forEach(e => {
      const narrs = (e.disinfo_narratives || []).filter(n => usedNarratives.includes(n));
      const bestNarr = narrs[0] || null;
      if (bestNarr) {
        if (!eventsByNarr.has(bestNarr)) eventsByNarr.set(bestNarr, []);
        eventsByNarr.get(bestNarr).push(e);
      }
    });

    narrAngles.forEach(({ nid, start, end }) => {
      const events = eventsByNarr.get(nid) || [];
      const startAngle = start + 0.03;
      const endAngle = end - 0.03;
      events.forEach((e, j) => {
        const hash = e.id.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
        const pseudo = ((hash * 9301 + 49297) % 233280) / 233280;
        const pseudo2 = ((hash * 7919 + 12345) % 233280) / 233280;
        let rNorm;
        if (e.threat_level === 'P1 CRITICAL') rNorm = 0.08 + pseudo * 0.28;
        else if (e.threat_level === 'P2 HIGH') rNorm = 0.36 + pseudo * 0.28;
        else rNorm = 0.64 + pseudo * 0.28;
        const r = innerRadius + rNorm * (maxRadius - innerRadius);
        const angleRange = endAngle - startAngle;
        const baseAngle = startAngle + (angleRange * (j + 0.5)) / Math.max(events.length, 1);
        const jitter = (pseudo2 - 0.5) * angleRange * 0.15;
        const angle = baseAngle + jitter;
        positions.set(e.id, { x: Math.cos(angle) * r, y: Math.sin(angle) * r });
      });
    });

    wheelPositions = positions;

    // Links
    const linkGroup = g.append('g').attr('class', 'links-group');
    const drawnLinks = new Set();
    filteredEvents.forEach(e => {
      if (e.related_events) {
        e.related_events.forEach(relId => {
          const linkKey = [e.id, relId].sort().join('::');
          if (drawnLinks.has(linkKey)) return;
          drawnLinks.add(linkKey);
          const from = positions.get(e.id);
          const to = positions.get(relId);
          if (from && to) {
            linkGroup.append('path').attr('class', 'event-link')
              .attr('d', `M${from.x},${from.y} Q${(from.x+to.x)*0.3},${(from.y+to.y)*0.3} ${to.x},${to.y}`)
              .datum({ source: e.id, target: relId });
          }
        });
      }
    });

    // Dots
    const dotsGroup = g.append('g').attr('class', 'dots-group');
    filteredEvents.forEach(e => {
      const pos = positions.get(e.id);
      if (!pos) return;
      const dotScale = window.innerWidth <= 900 ? 0.55 : 1;
      const obsBoost = e.observation_count ? Math.min(3, e.observation_count * 0.3) : 0;
      const size = Math.max(2, Math.min(14, 2 + e.spread * 1.5 + obsBoost)) * dotScale;
      const color = eventColor(e);
      dotsGroup.append('circle').attr('class', 'event-dot')
        .attr('cx', pos.x).attr('cy', pos.y).attr('r', size)
        .attr('fill', color)
        .attr('fill-opacity', e.event_type === 'CONTEXT' ? 0.35 : 0.9)
        .attr('filter', e.event_type === 'DISINFO' ? 'url(#glow)' : null)
        .datum(e)
        .on('mouseenter', function(event) {
          if (!pinnedEvent) { showTooltip(event, e); showDetail(e); highlightEvent(e); }
          else showTooltip(event, e);
        })
        .on('mousemove', function(event) { showTooltip(event, e); })
        .on('mouseleave', function() { hideTooltip(); if (!pinnedEvent) hideDetail(); })
        .on('click', function() {
          if (pinnedEvent && pinnedEvent.id === e.id) { pinnedEvent = null; hideDetail(); }
          else { pinnedEvent = e; showDetail(e); highlightEvent(e); }
        });
    });

    // Center label
    g.append('text').attr('text-anchor', 'middle').attr('dy', -6)
      .style('font-family', "'DM Serif Display', Georgia, serif").style('font-style', 'italic')
      .style('font-size', '14px').style('fill', '#9E9E9E').text('Highest');
    g.append('text').attr('text-anchor', 'middle').attr('dy', 12)
      .style('font-family', "'DM Serif Display', Georgia, serif").style('font-style', 'italic')
      .style('font-size', '14px').style('fill', '#9E9E9E').text('Threat');
  }

  // ═══════════════════════════════════════════════════════════════════
  // HATE SPEECH RADIAL WHEEL
  // ═══════════════════════════════════════════════════════════════════
  function renderHSWheel() {
    const svg = d3.select('#hs-wheel-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('panel-hatespeech');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const cx = width / 2;
    const cy = height / 2;
    const hsMobilePad = window.innerWidth <= 900 ? 85 : 50;
    const maxRadius = Math.min(cx, cy) - hsMobilePad;
    const innerRadius = maxRadius * 0.10;

    // Defs
    const defs = svg.append('defs');
    const glowFilter = defs.append('filter').attr('id', 'hs-glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'blur');
    const merge = glowFilter.append('feMerge');
    merge.append('feMergeNode').attr('in', 'blur');
    merge.append('feMergeNode').attr('in', 'SourceGraphic');

    const zoomGroup = svg.append('g').attr('class', 'hs-wheel-zoom-group');
    const g = zoomGroup.append('g').attr('transform', `translate(${cx},${cy})`);

    hsWheelZoom = d3.zoom()
      .scaleExtent([0.5, 8])
      .on('zoom', function(event) { zoomGroup.attr('transform', event.transform); });
    svg.call(hsWheelZoom);
    svg.call(hsWheelZoom.transform, d3.zoomIdentity);
    svg.append('text')
      .attr('class', 'zoom-hint')
      .attr('x', width - 12).attr('y', height - 12)
      .attr('text-anchor', 'end')
      .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '9px')
      .style('fill', '#9E9E9E').style('opacity', 0.6)
      .text(window.innerWidth <= 900 ? 'Pinch to zoom · Drag to pan' : 'Scroll to zoom · Drag to pan · Double-click to reset');
    svg.on('dblclick.zoom', function() {
      svg.transition().duration(500).call(hsWheelZoom.transform, d3.zoomIdentity);
    });

    // Toxicity rings: very_high=innermost, high, medium, low=outermost
    const toxRings = [
      { tox: 'very_high', rStart: 0.0,   rEnd: 0.25, label: 'VERY HIGH', color: '#7A1A1A' },
      { tox: 'high',      rStart: 0.25,  rEnd: 0.50, label: 'HIGH',      color: '#B83A2A' },
      { tox: 'medium',    rStart: 0.50,  rEnd: 0.75, label: 'MEDIUM',    color: '#CA5D0F' },
      { tox: 'low',       rStart: 0.75,  rEnd: 1.0,  label: 'LOW',       color: '#1A3A34' }
    ];

    const ringR = toxRings.map(tr => ({
      ...tr,
      r: innerRadius + (tr.rStart + tr.rEnd) / 2 * (maxRadius - innerRadius),
      rInner: innerRadius + tr.rStart * (maxRadius - innerRadius),
      rOuter: innerRadius + tr.rEnd * (maxRadius - innerRadius)
    }));

    // Draw ring guides
    ringR.forEach(ring => {
      g.append('circle').attr('r', ring.r).attr('class', 'wheel-ring')
        .style('stroke', ring.color).style('opacity', 0.12);
      g.append('text').attr('x', 5).attr('y', -ring.r - 3).attr('class', 'wheel-ring-label')
        .style('fill', ring.color).style('opacity', 0.5).text(ring.label);
    });

    // Classify posts by axis
    const postsByAxis = new Map();
    HS_AXES.forEach(axis => postsByAxis.set(axis, []));
    filteredHSPosts.forEach(p => {
      const axis = getHSSubtopic(p);
      if (postsByAxis.has(axis)) postsByAxis.get(axis).push(p);
      else {
        // Fallback: assign to General Abuse
        postsByAxis.get('General Abuse').push(p);
      }
    });

    // All 8 axes proportional to post count with minimum
    const segmentPad = 0.015;
    const totalPad = segmentPad * 2 * HS_AXES.length;
    const availAngle = 2 * Math.PI - totalPad;
    const MIN_ANGLE = 0.15; // min angle per axis
    const axisCounts = HS_AXES.map(a => ({ axis: a, count: postsByAxis.get(a).length }));
    const totalPosts = axisCounts.reduce((s, c) => s + c.count, 0) || 1;
    const minAngleTotal = MIN_ANGLE * HS_AXES.length;
    const extraAvail = Math.max(0, availAngle - minAngleTotal);

    const axisAngles = [];
    let cumAngle = -Math.PI / 2;

    axisCounts.forEach(({ axis, count }) => {
      const propAngle = MIN_ANGLE + (count / totalPosts) * extraAvail;
      axisAngles.push({
        axis,
        start: cumAngle + segmentPad,
        end: cumAngle + propAngle - segmentPad,
        count
      });
      cumAngle += propAngle;
    });

    // Draw segment dividers and labels
    axisAngles.forEach(({ axis, start, end }) => {
      // Divider line
      const x1 = Math.cos(start) * innerRadius;
      const y1 = Math.sin(start) * innerRadius;
      const x2 = Math.cos(start) * maxRadius;
      const y2 = Math.sin(start) * maxRadius;
      g.append('line').attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2)
        .style('stroke', '#D5D0C7').style('opacity', 0.3);

      // Label
      const midAngle = (start + end) / 2;
      const labelR = maxRadius + 16;
      const lx = Math.cos(midAngle) * labelR;
      const ly = Math.sin(midAngle) * labelR;
      const degAngle = midAngle * 180 / Math.PI;
      const flip = degAngle > 90 || degAngle < -90;
      const textAnchor = flip ? 'end' : 'start';
      const rotation = flip ? degAngle + 180 : degAngle;
      const displayName = axis.length > 22 ? axis.substring(0, 20) + '...' : axis;
      g.append('text').attr('class', 'wheel-segment-label')
        .attr('transform', `translate(${lx},${ly}) rotate(${rotation})`)
        .attr('text-anchor', textAnchor).attr('dominant-baseline', 'middle')
        .text(displayName);
    });

    // ─── Place dots for ALL posts (individual per axis) ────────────
    const axisAngleMap = new Map(axisAngles.map(a => [a.axis, a]));

    HS_AXES.forEach(axis => {
      const posts = postsByAxis.get(axis);
      const angles = axisAngleMap.get(axis);
      if (!angles || posts.length === 0) return;
      const startAngle = angles.start + 0.02;
      const endAngle = angles.end - 0.02;
      const angleRange = endAngle - startAngle;

      posts.forEach((p, j) => {
        const hash = p.i.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
        const pseudo = ((hash * 9301 + 49297) % 233280) / 233280;
        const pseudo2 = ((hash * 7919 + 12345) % 233280) / 233280;

        // Radial position based on toxicity (4 rings)
        const tox = normalizeToxicity(p.tx);
        let rNorm;
        if (tox === 'very_high') rNorm = 0.02 + pseudo * 0.20;
        else if (tox === 'high') rNorm = 0.27 + pseudo * 0.20;
        else if (tox === 'medium') rNorm = 0.52 + pseudo * 0.20;
        else rNorm = 0.77 + pseudo * 0.20;
        const r = innerRadius + rNorm * (maxRadius - innerRadius);

        // Angular position
        const baseAngle = startAngle + (angleRange * (j + 0.5)) / Math.max(posts.length, 1);
        const jitter = (pseudo2 - 0.5) * angleRange * 0.15;
        const angle = baseAngle + jitter;

        const eng = hsEngagement(p);
        const hsDotScale = window.innerWidth <= 900 ? 0.55 : 1;
        const size = Math.max(2, Math.min(12, 3 + Math.sqrt(eng) * 0.8)) * hsDotScale;
        const color = hsPostColor(p);

        g.append('circle').attr('class', 'hs-dot')
          .attr('cx', Math.cos(angle) * r).attr('cy', Math.sin(angle) * r).attr('r', size)
          .attr('fill', color)
          .attr('fill-opacity', p.pr === 'Hate' ? 0.9 : p.pr === 'Abusive' ? 0.85 : 0.3)
          .attr('filter', p.pr === 'Hate' ? 'url(#hs-glow)' : null)
          .datum(p)
          .on('mouseenter', function(event) {
            if (!pinnedHSPost) { showHSTooltip(event, p); showHSDetail(p); }
            else showHSTooltip(event, p);
          })
          .on('mousemove', function(event) { showHSTooltip(event, p); })
          .on('mouseleave', function() { hideTooltip(); if (!pinnedHSPost) hideDetail(); })
          .on('click', function() {
            if (pinnedHSPost && pinnedHSPost.i === p.i) { pinnedHSPost = null; hideDetail(); }
            else { pinnedHSPost = p; showHSDetail(p); }
          });
      });
    });

    // Center label
    g.append('text').attr('text-anchor', 'middle').attr('dy', -6)
      .style('font-family', "'DM Serif Display', Georgia, serif").style('font-style', 'italic')
      .style('font-size', '14px').style('fill', '#9E9E9E').text('Highest');
    g.append('text').attr('text-anchor', 'middle').attr('dy', 12)
      .style('font-family', "'DM Serif Display', Georgia, serif").style('font-style', 'italic')
      .style('font-size', '14px').style('fill', '#9E9E9E').text('Toxicity');
  }

  // ═══════════════════════════════════════════════════════════════════
  // NARRATIVE LIFECYCLE PLAYBACK (Disinfo wheel only)
  // ═══════════════════════════════════════════════════════════════════

  function buildWeekTimeline(events) {
    const dates = events.map(e => new Date(e.date));
    const minDate = d3.min(dates);
    const maxDate = d3.max(dates);
    const firstMonday = d3.timeMonday.floor(minDate);
    const lastMonday = d3.timeMonday.ceil(maxDate);
    return d3.timeMonday.range(firstMonday, d3.timeMonday.offset(lastMonday, 1));
  }

  function computeNarrativeHeatTimeline(events, weeks) {
    const eventsByWeek = new Map();
    weeks.forEach(w => eventsByWeek.set(w.getTime(), []));
    events.forEach(e => {
      const d = new Date(e.date);
      const weekStart = d3.timeMonday.floor(d);
      const key = weekStart.getTime();
      if (eventsByWeek.has(key)) {
        eventsByWeek.get(key).push(e);
      } else {
        const firstKey = weeks[0].getTime();
        eventsByWeek.get(firstKey).push(e);
      }
    });

    const heatState = new Map();
    const timeline = [];

    weeks.forEach(week => {
      const weekEvents = eventsByWeek.get(week.getTime()) || [];
      for (const [nid, heat] of heatState) {
        const newHeat = heat - HEAT_DECAY_PER_WEEK;
        if (newHeat <= HEAT_VISIBLE_THRESHOLD) heatState.delete(nid);
        else heatState.set(nid, newHeat);
      }
      const weekNarrEvents = new Map();
      weekEvents.forEach(e => {
        (e.disinfo_narratives || []).forEach(nid => {
          if (!narrativeRef[nid]) return;
          const current = heatState.get(nid) || 0;
          heatState.set(nid, Math.min(HEAT_MAX, current + HEAT_PER_EVENT));
          if (!weekNarrEvents.has(nid)) weekNarrEvents.set(nid, []);
          weekNarrEvents.get(nid).push(e);
        });
      });
      timeline.push({ week, narrativeHeat: new Map(heatState), newEvents: weekEvents, weekNarrEvents });
    });

    return timeline;
  }

  function renderPlaybackWheel(weekState, allWeeksSoFar, allNarrativesSeen) {
    const svg = d3.select('#wheel-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('panel-wheel');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const cx = width / 2;
    const cy = height / 2;
    const maxRadius = Math.min(cx, cy) - 40;
    const innerRadius = maxRadius * 0.12;

    const defs = svg.append('defs');
    const glowFilter = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'blur');
    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'blur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    const pulseFilter = defs.append('filter').attr('id', 'pulse-glow').attr('x', '-100%').attr('y', '-100%').attr('width', '300%').attr('height', '300%');
    pulseFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
    const pm = pulseFilter.append('feMerge');
    pm.append('feMergeNode').attr('in', 'blur');
    pm.append('feMergeNode').attr('in', 'SourceGraphic');
    const linkGrad = defs.append('linearGradient').attr('id', 'link-gradient');
    linkGrad.append('stop').attr('offset', '0%').attr('stop-color', '#1A3A34').attr('stop-opacity', 0.5);
    linkGrad.append('stop').attr('offset', '50%').attr('stop-color', '#8071BC').attr('stop-opacity', 0.3);
    linkGrad.append('stop').attr('offset', '100%').attr('stop-color', '#1A3A34').attr('stop-opacity', 0.5);

    const zoomGroup = svg.append('g').attr('class', 'wheel-zoom-group');
    const g = zoomGroup.append('g').attr('transform', `translate(${cx},${cy})`);
    if (wheelZoom) svg.call(wheelZoom);

    const rings = [
      { r: innerRadius + (maxRadius - innerRadius) * 0.15, label: 'P1 CRITICAL', color: '#B83A2A' },
      { r: innerRadius + (maxRadius - innerRadius) * 0.50, label: 'P2 HIGH', color: '#CA5D0F' },
      { r: innerRadius + (maxRadius - innerRadius) * 0.85, label: 'P3 MODERATE', color: '#1A3A34' }
    ];
    rings.forEach(ring => {
      g.append('circle').attr('r', ring.r).attr('class', 'wheel-ring')
        .style('stroke', ring.color).style('opacity', 0.08);
    });

    const activeNarratives = [...weekState.narrativeHeat.entries()]
      .filter(([_, heat]) => heat > HEAT_VISIBLE_THRESHOLD)
      .sort((a, b) => b[1] - a[1]);

    if (activeNarratives.length === 0) {
      g.append('text').attr('text-anchor', 'middle').attr('dy', 0)
        .style('font-family', "'DM Serif Display', Georgia, serif").style('font-style', 'italic')
        .style('font-size', '16px').style('fill', '#9E9E9E').style('opacity', 0.5)
        .text('No active narratives');
      return;
    }

    const segmentPad = 0.02;
    const PB_MIN_ANGLE = 0.12;
    const totalHeat = activeNarratives.reduce((s, [_, h]) => s + h, 0);
    const pbAvailAngle = 2 * Math.PI - segmentPad * 2 * activeNarratives.length;
    const pbTotalMinAngle = PB_MIN_ANGLE * activeNarratives.length;
    const pbUseMin = pbTotalMinAngle >= pbAvailAngle;
    const pbNarrAngles = new Map();
    let pbCumAngle = -Math.PI / 2;
    activeNarratives.forEach(([nid, heat]) => {
      let segAngle;
      if (pbUseMin) segAngle = (2 * Math.PI) / activeNarratives.length;
      else {
        const extraAngle = pbAvailAngle - pbTotalMinAngle;
        segAngle = PB_MIN_ANGLE + (heat / totalHeat) * extraAngle + segmentPad * 2;
      }
      pbNarrAngles.set(nid, { start: pbCumAngle + segmentPad, end: pbCumAngle + segAngle - segmentPad });
      pbCumAngle += segAngle;
    });

    const visibleEvents = [];
    const visibleEventIds = new Set();
    allWeeksSoFar.forEach(ws => {
      ws.newEvents.forEach(e => {
        if (!visibleEventIds.has(e.id)) { visibleEventIds.add(e.id); visibleEvents.push(e); }
      });
    });

    activeNarratives.forEach(([nid, heat]) => {
      const narr = narrativeRef[nid];
      if (!narr) return;
      const angles = pbNarrAngles.get(nid);
      if (!angles) return;
      const startAngle = angles.start;
      const endAngle = angles.end;
      const heatNorm = Math.min(heat / HEAT_MAX, 1);

      const x1 = Math.cos(startAngle) * innerRadius;
      const y1 = Math.sin(startAngle) * innerRadius;
      const x2 = Math.cos(startAngle) * maxRadius;
      const y2 = Math.sin(startAngle) * maxRadius;
      const playNarrPrefix = nid.split('-')[1];
      const playNarrCountryMap = { 'SS': 'South Sudan', 'SO': 'Somalia', 'KE': 'Kenya', 'FP': 'Regional' };
      const narrColor = countryDark(playNarrCountryMap[playNarrPrefix] || 'Regional');

      g.append('line').attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2)
        .style('stroke', narrColor).style('opacity', 0.1 + heatNorm * 0.3);

      const arc = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(innerRadius + (maxRadius - innerRadius) * (0.3 + heatNorm * 0.7))
        .startAngle(startAngle + Math.PI / 2)
        .endAngle(endAngle + Math.PI / 2);
      g.append('path').attr('d', arc)
        .attr('fill', narrColor).attr('fill-opacity', heatNorm * 0.06)
        .attr('class', 'narrative-heat-arc');

      const midAngle = (startAngle + endAngle) / 2;
      const labelR = maxRadius + 16;
      const lx = Math.cos(midAngle) * labelR;
      const ly = Math.sin(midAngle) * labelR;
      const degAngle = midAngle * 180 / Math.PI;
      const flip = degAngle > 90 || degAngle < -90;
      const textAnchor = flip ? 'end' : 'start';
      const rotation = flip ? degAngle + 180 : degAngle;
      const shortName = narr.short_name || narr.name;
      const displayName = shortName.length > 20 ? shortName.substring(0, 18) + '...' : shortName;

      g.append('text').attr('class', 'wheel-segment-label')
        .attr('transform', `translate(${lx},${ly}) rotate(${rotation})`)
        .attr('text-anchor', textAnchor).attr('dominant-baseline', 'middle')
        .style('opacity', 0.3 + heatNorm * 0.7)
        .style('font-size', `${7.5 + heatNorm * 2}px`)
        .text(displayName);
    });

    const activeNarrIds = new Set(activeNarratives.map(([nid]) => nid));
    const positions = new Map();
    const eventsByNarr = new Map();

    visibleEvents.forEach(e => {
      const narrs = (e.disinfo_narratives || []).filter(n => activeNarrIds.has(n));
      const bestNarr = narrs[0] || null;
      if (bestNarr) {
        if (!eventsByNarr.has(bestNarr)) eventsByNarr.set(bestNarr, []);
        eventsByNarr.get(bestNarr).push(e);
      }
    });

    activeNarratives.forEach(([nid, heat]) => {
      const events = eventsByNarr.get(nid) || [];
      const angles = pbNarrAngles.get(nid);
      if (!angles) return;
      const startAngle = angles.start + 0.03;
      const endAngle = angles.end - 0.03;

      events.forEach((e, j) => {
        const hash = e.id.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
        const pseudo = ((hash * 9301 + 49297) % 233280) / 233280;
        const pseudo2 = ((hash * 7919 + 12345) % 233280) / 233280;
        let rNorm;
        if (e.threat_level === 'P1 CRITICAL') rNorm = 0.08 + pseudo * 0.28;
        else if (e.threat_level === 'P2 HIGH') rNorm = 0.36 + pseudo * 0.28;
        else rNorm = 0.64 + pseudo * 0.28;
        const r = innerRadius + rNorm * (maxRadius - innerRadius);
        const angleRange = endAngle - startAngle;
        const baseAngle = startAngle + (angleRange * (j + 0.5)) / Math.max(events.length, 1);
        const jitter = (pseudo2 - 0.5) * angleRange * 0.15;
        const angle = baseAngle + jitter;
        positions.set(e.id, { x: Math.cos(angle) * r, y: Math.sin(angle) * r });
      });
    });

    const linkGroup = g.append('g').attr('class', 'links-group');
    const drawnLinks = new Set();
    visibleEvents.forEach(e => {
      if (e.related_events) {
        e.related_events.forEach(relId => {
          const linkKey = [e.id, relId].sort().join('::');
          if (drawnLinks.has(linkKey)) return;
          drawnLinks.add(linkKey);
          const from = positions.get(e.id);
          const to = positions.get(relId);
          if (from && to) {
            linkGroup.append('path').attr('class', 'event-link')
              .attr('d', `M${from.x},${from.y} Q${(from.x+to.x)*0.3},${(from.y+to.y)*0.3} ${to.x},${to.y}`)
              .datum({ source: e.id, target: relId });
          }
        });
      }
    });

    const thisWeekIds = new Set(weekState.newEvents.map(e => e.id));
    const dotsGroup = g.append('g').attr('class', 'dots-group');

    visibleEvents.forEach(e => {
      const pos = positions.get(e.id);
      if (!pos) return;
      const bestNarr = (e.disinfo_narratives || []).find(n => activeNarrIds.has(n));
      const narrHeat = bestNarr ? (weekState.narrativeHeat.get(bestNarr) || 0) : 0;
      const heatNorm = Math.min(narrHeat / HEAT_MAX, 1);
      const isNew = thisWeekIds.has(e.id);
      const animDotScale = window.innerWidth <= 900 ? 0.55 : 1;
      const animObsBoost = e.observation_count ? Math.min(3, e.observation_count * 0.3) : 0;
      const baseSize = Math.max(2, Math.min(14, 2 + e.spread * 1.5 + animObsBoost)) * animDotScale;
      const color = eventColor(e);
      let opacity;
      if (e.event_type === 'CONTEXT') opacity = 0.08 + heatNorm * 0.25;
      else opacity = 0.4 + heatNorm * 0.55;

      const dot = dotsGroup.append('circle').attr('class', 'event-dot')
        .attr('cx', pos.x).attr('cy', pos.y)
        .attr('r', isNew ? 0 : baseSize)
        .attr('fill', color).attr('fill-opacity', opacity)
        .attr('filter', (e.event_type === 'DISINFO' && isNew) ? 'url(#pulse-glow)' : (e.event_type === 'DISINFO' ? 'url(#glow)' : null))
        .datum(e)
        .on('mouseenter', function(event) {
          if (!pinnedEvent) { showTooltip(event, e); showDetail(e); }
          else showTooltip(event, e);
        })
        .on('mousemove', function(event) { showTooltip(event, e); })
        .on('mouseleave', function() { hideTooltip(); if (!pinnedEvent) hideDetail(); })
        .on('click', function() {
          if (pinnedEvent && pinnedEvent.id === e.id) { pinnedEvent = null; hideDetail(); }
          else { pinnedEvent = e; showDetail(e); }
        });

      if (isNew) {
        dot.transition().duration(400).ease(d3.easeElasticOut.amplitude(1).period(0.4))
          .attr('r', baseSize * 1.8)
          .transition().duration(300)
          .attr('r', baseSize);
      }
    });

    const activeCount = activeNarratives.length;
    g.append('text').attr('text-anchor', 'middle').attr('dy', -12)
      .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '24px')
      .style('font-weight', '700').style('fill', '#CA5D0F').style('opacity', 0.85)
      .text(activeCount);
    g.append('text').attr('text-anchor', 'middle').attr('dy', 8)
      .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '8px')
      .style('fill', '#9E9E9E').style('letter-spacing', '1.5px').style('text-transform', 'uppercase')
      .text(activeCount === 1 ? 'narrative' : 'narratives');
    g.append('text').attr('text-anchor', 'middle').attr('dy', 22)
      .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '8px')
      .style('fill', '#9E9E9E').style('letter-spacing', '1.5px').style('text-transform', 'uppercase')
      .text('active');
  }

  // ─── ANIMATED TIME PLAYBACK ────────────────────────────────────
  let pbData = null;
  let pbPaused = false;

  function pbBuildData() {
    const sorted = [...filteredEvents].sort((a, b) => new Date(a.date) - new Date(b.date));
    if (sorted.length === 0) return null;
    const weeks = buildWeekTimeline(sorted);
    const heatTimeline = computeNarrativeHeatTimeline(sorted, weeks);
    const allNarrativesSeen = [];
    const seenSet = new Set();
    heatTimeline.forEach(ws => {
      for (const [nid] of ws.narrativeHeat) {
        if (!seenSet.has(nid)) { seenSet.add(nid); allNarrativesSeen.push(nid); }
      }
    });
    return { heatTimeline, allNarrativesSeen };
  }

  function pbRenderFrame(idx) {
    if (!pbData || idx < 0 || idx >= pbData.heatTimeline.length) return;
    playbackIndex = idx;
    const weekState = pbData.heatTimeline[idx];
    const allWeeksSoFar = pbData.heatTimeline.slice(0, idx + 1);
    const pct = ((idx + 1) / pbData.heatTimeline.length * 100);

    document.getElementById('playback-progress').style.width = pct + '%';
    document.getElementById('playback-handle').style.left = pct + '%';
    document.getElementById('playback-date').textContent = d3.timeFormat('%b %d, %Y')(weekState.week);

    const activeCount = [...weekState.narrativeHeat.values()].filter(h => h > HEAT_VISIBLE_THRESHOLD).length;
    const statsEl = document.getElementById('playback-stats');
    if (statsEl) statsEl.textContent = `${activeCount} narratives · ${weekState.newEvents.length} new events`;

    renderPlaybackWheel(weekState, allWeeksSoFar, pbData.allNarrativesSeen);
  }

  function pbUpdateUI() {
    const btn = document.getElementById('btn-play');
    const icon = document.getElementById('play-icon');
    const bar = document.getElementById('playback-bar');
    btn.classList.remove('playing', 'paused');
    bar.classList.remove('pb-playing', 'pb-paused');
    bar.classList.toggle('has-data', !!pbData);
    if (isPlaying) {
      btn.classList.add('playing');
      bar.classList.add('pb-playing');
      icon.textContent = '⏸';
    } else if (pbPaused && pbData) {
      btn.classList.add('paused');
      bar.classList.add('pb-paused');
      icon.textContent = '▶';
    } else {
      icon.textContent = '▶';
    }
  }

  function pbScheduleNext() {
    if (!isPlaying) return;
    const interval = Math.round(400 / playbackSpeed);
    playbackTimer = setTimeout(pbStep, interval);
  }

  function pbStep() {
    if (!isPlaying || !pbData) return;
    const nextIdx = playbackIndex + 1;
    if (nextIdx >= pbData.heatTimeline.length) { pausePlayback(); return; }
    pbRenderFrame(nextIdx);
    pbScheduleNext();
  }

  function startPlayback() {
    if (currentView !== 'wheel') return;
    if (isPlaying) return;
    if (pbPaused && pbData) {
      isPlaying = true;
      pbPaused = false;
      pbUpdateUI();
      pbScheduleNext();
      return;
    }
    pbData = pbBuildData();
    if (!pbData) return;
    playbackIndex = 0;
    isPlaying = true;
    pbPaused = false;
    pbUpdateUI();
    pbRenderFrame(0);
    pbScheduleNext();
  }

  function pausePlayback() {
    if (!isPlaying && !pbData) return;
    isPlaying = false;
    pbPaused = true;
    clearTimeout(playbackTimer);
    pbUpdateUI();
  }

  function resetPlayback() {
    isPlaying = false;
    pbPaused = false;
    clearTimeout(playbackTimer);
    pbData = null;
    playbackIndex = 0;
    document.getElementById('playback-progress').style.width = '0%';
    document.getElementById('playback-handle').style.left = '0%';
    document.getElementById('playback-date').textContent = '';
    const statsEl = document.getElementById('playback-stats');
    if (statsEl) statsEl.textContent = '';
    pbUpdateUI();
    if (currentView === 'wheel') renderWheel();
  }

  function togglePlayback() {
    if (isPlaying) pausePlayback();
    else startPlayback();
  }

  function pbStepForward() {
    if (currentView !== 'wheel') return;
    if (!pbData) {
      pbData = pbBuildData();
      if (!pbData) return;
      isPlaying = false;
      pbPaused = true;
      pbUpdateUI();
      pbRenderFrame(0);
      return;
    }
    if (isPlaying) pausePlayback();
    pbPaused = true;
    const next = Math.min(playbackIndex + 1, pbData.heatTimeline.length - 1);
    pbRenderFrame(next);
    pbUpdateUI();
  }

  function pbStepBack() {
    if (!pbData) return;
    if (isPlaying) pausePlayback();
    pbPaused = true;
    const prev = Math.max(playbackIndex - 1, 0);
    pbRenderFrame(prev);
    pbUpdateUI();
  }

  function pbScrub(e) {
    if (currentView !== 'wheel') return;
    if (!pbData) {
      pbData = pbBuildData();
      if (!pbData) return;
      pbPaused = true;
    }
    if (isPlaying) pausePlayback();
    pbPaused = true;
    const track = document.getElementById('playback-track');
    const rect = track.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const idx = Math.round(pct * (pbData.heatTimeline.length - 1));
    pbRenderFrame(idx);
    pbUpdateUI();
  }

  function stopPlayback() { resetPlayback(); }

  function cycleSpeed() {
    const speeds = [0.5, 1, 2, 3];
    const labels = ['0.5×', '1×', '2×', '3×'];
    const currentIdx = speeds.indexOf(playbackSpeed);
    const nextIdx = (currentIdx + 1) % speeds.length;
    playbackSpeed = speeds[nextIdx];
    const btn = document.getElementById('btn-speed');
    if (btn) btn.textContent = labels[nextIdx];
  }

  // ─── SCRUBBER ───────────────────────────────────────────────────
  let scrubberZoomState = null;

  function scrubberDateFmt(domain) {
    const spanMs = domain[1] - domain[0];
    const spanDays = spanMs / (1000 * 60 * 60 * 24);
    if (spanDays < 60) return d3.timeFormat('%d %b %Y');
    if (spanDays < 365) return d3.timeFormat('%b %Y');
    return d3.timeFormat('%b %Y');
  }

  function renderScrubber() {
    const svg = d3.select('#scrubber-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('scrubber-track');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    const dateExtent = d3.extent(allEvents, d => new Date(d.date));
    if (!dateExtent[0]) return;

    const xFull = d3.scaleTime().domain(dateExtent).range([0, width]);
    let xCurrent = xFull.copy();
    const barsGroup = svg.append('g').attr('class', 'scrubber-bars');

    function drawBars() {
      barsGroup.selectAll('*').remove();
      const domain = xCurrent.domain();
      const visibleEvents = allEvents.filter(e => {
        const d = new Date(e.date);
        return d >= domain[0] && d <= domain[1];
      });
      const bins = d3.bin().domain(domain)
        .thresholds(d3.timeWeek.range(domain[0], domain[1]))
        .value(d => new Date(d.date))(visibleEvents);
      const yMax = d3.max(bins, b => b.length) || 1;
      const barH = d3.scaleLinear().domain([0, yMax]).range([0, height - 6]);

      bins.forEach(bin => {
        const bx = xCurrent(bin.x0);
        const bw = Math.max(1, xCurrent(bin.x1) - xCurrent(bin.x0) - 1);
        const bh = barH(bin.length);
        const disinfoCount = bin.filter(e => e.event_type === 'DISINFO').length;
        const disinfoBh = bh * (disinfoCount / (bin.length || 1));
        const contextBh = bh - disinfoBh;
        if (contextBh > 0) {
          barsGroup.append('rect').attr('class', 'scrubber-bar')
            .attr('x', bx).attr('y', height - bh - 2).attr('width', bw).attr('height', contextBh)
            .attr('fill', '#D5D0C7').attr('opacity', 0.5).attr('rx', 1);
        }
        if (disinfoBh > 0) {
          barsGroup.append('rect').attr('class', 'scrubber-bar')
            .attr('x', bx).attr('y', height - disinfoBh - 2).attr('width', bw).attr('height', disinfoBh)
            .attr('fill', '#8071BC').attr('opacity', 0.75).attr('rx', 1);
        }
      });
    }

    function updateDateLabels() {
      const domain = xCurrent.domain();
      const fmt = scrubberDateFmt(domain);
      document.getElementById('date-range-start').textContent = fmt(domain[0]);
      document.getElementById('date-range-end').textContent = fmt(domain[1]);
    }

    drawBars();
    updateDateLabels();

    // ── d3.brushX: drag to select a date range ──
    const brush = d3.brushX()
      .extent([[0, 0], [width, height]])
      .on('brush', function(event) {
        if (!event.selection || !event.sourceEvent) return;
        const [x0, x1] = event.selection;
        const d0 = xCurrent.invert(x0);
        const d1 = xCurrent.invert(x1);
        const fmt = scrubberDateFmt([d0, d1]);
        document.getElementById('date-range-start').textContent = fmt(d0);
        document.getElementById('date-range-end').textContent = fmt(d1);
      })
      .on('end', function(event) {
        if (!event.sourceEvent) return;
        if (!event.selection) {
          brushExtent = null;
          updateDateLabels();
        } else {
          const [x0, x1] = event.selection;
          brushExtent = [xCurrent.invert(x0), xCurrent.invert(x1)];
        }
        applyFilters();
      });

    const brushG = svg.append('g').attr('class', 'scrubber-brush').call(brush);

    // Style the brush
    brushG.select('.selection')
      .attr('fill', 'var(--iris, #8071BC)').attr('fill-opacity', 0.12)
      .attr('stroke', 'var(--iris, #8071BC)').attr('stroke-opacity', 0.3)
      .attr('stroke-width', 1).attr('rx', 2);
    brushG.selectAll('.handle')
      .attr('fill', 'var(--iris, #8071BC)').attr('fill-opacity', 0.4)
      .attr('width', 3).attr('rx', 1.5);
    brushG.select('.overlay').style('cursor', 'default');
    brushG.select('.selection').style('cursor', 'default');
    brushG.selectAll('.handle').style('cursor', 'ew-resize');

    // ── Scroll-to-zoom: wheel zooms the x axis ──
    const zoom = d3.zoom()
      .scaleExtent([1, 20])
      .translateExtent([[0, 0], [width, height]])
      .extent([[0, 0], [width, height]])
      .filter(event => event.type === 'wheel' || event.type === 'dblclick')
      .on('zoom', function(event) {
        xCurrent = event.transform.rescaleX(xFull);
        drawBars();
        // Remap brush selection to new scale
        if (brushExtent) {
          const newX0 = xCurrent(brushExtent[0]);
          const newX1 = xCurrent(brushExtent[1]);
          if (newX0 >= 0 && newX1 <= width) {
            brushG.call(brush.move, [newX0, newX1]);
          } else {
            brushG.call(brush.move, null);
            brushExtent = null;
            applyFilters();
          }
        }
        updateDateLabels();
        scrubberZoomState = event.transform;
      });

    svg.call(zoom);
    svg.on('dblclick.zoom', function() {
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
      brushG.call(brush.move, null);
      brushExtent = null;
      applyFilters();
    });

    // Restore previous zoom state
    if (scrubberZoomState) {
      svg.call(zoom.transform, scrubberZoomState);
    }
  }

  let hsScrubberZoomState = null;

  function renderHSScrubber() {
    const svg = d3.select('#scrubber-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('scrubber-track');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    const dateExtent = d3.extent(allHSPosts, d => new Date(d.d));
    if (!dateExtent[0]) return;

    const xFull = d3.scaleTime().domain(dateExtent).range([0, width]);
    let xCurrent = xFull.copy();
    const barsGroup = svg.append('g').attr('class', 'scrubber-bars');

    function drawBars() {
      barsGroup.selectAll('*').remove();
      const domain = xCurrent.domain();
      const visiblePosts = allHSPosts.filter(p => {
        const d = new Date(p.d);
        return d >= domain[0] && d <= domain[1];
      });
      const weekRange = d3.timeWeek.range(domain[0], domain[1]);
      if (weekRange.length === 0) return;
      const bins = d3.bin().domain(domain)
        .thresholds(weekRange)
        .value(d => new Date(d.d))(visiblePosts);
      const yMax = d3.max(bins, b => b.length) || 1;
      const barH = d3.scaleLinear().domain([0, yMax]).range([0, height - 6]);

      bins.forEach(bin => {
        const bx = xCurrent(bin.x0);
        const bw = Math.max(1, xCurrent(bin.x1) - xCurrent(bin.x0) - 1);
        const bh = barH(bin.length);
        const hateCount = bin.filter(p => p.pr === 'Hate').length;
        const hateBh = bh * (hateCount / (bin.length || 1));
        const abusiveBh = bh - hateBh;
        if (abusiveBh > 0) {
          barsGroup.append('rect').attr('class', 'scrubber-bar')
            .attr('x', bx).attr('y', height - bh - 2).attr('width', bw).attr('height', abusiveBh)
            .attr('fill', '#C4BBE0').attr('opacity', 0.5).attr('rx', 1);
        }
        if (hateBh > 0) {
          barsGroup.append('rect').attr('class', 'scrubber-bar')
            .attr('x', bx).attr('y', height - hateBh - 2).attr('width', bw).attr('height', hateBh)
            .attr('fill', '#B83A2A').attr('opacity', 0.65).attr('rx', 1);
        }
      });
    }

    function updateDateLabels() {
      const domain = xCurrent.domain();
      const fmt = scrubberDateFmt(domain);
      document.getElementById('date-range-start').textContent = fmt(domain[0]);
      document.getElementById('date-range-end').textContent = fmt(domain[1]);
    }

    drawBars();
    updateDateLabels();

    // ── d3.brushX: drag to select a date range ──
    const brush = d3.brushX()
      .extent([[0, 0], [width, height]])
      .on('brush', function(event) {
        if (!event.selection || !event.sourceEvent) return;
        const [x0, x1] = event.selection;
        const d0 = xCurrent.invert(x0);
        const d1 = xCurrent.invert(x1);
        const fmt = scrubberDateFmt([d0, d1]);
        document.getElementById('date-range-start').textContent = fmt(d0);
        document.getElementById('date-range-end').textContent = fmt(d1);
      })
      .on('end', function(event) {
        if (!event.sourceEvent) return;
        if (!event.selection) {
          hsBrushExtent = null;
          updateDateLabels();
        } else {
          const [x0, x1] = event.selection;
          hsBrushExtent = [xCurrent.invert(x0), xCurrent.invert(x1)];
        }
        applyHSFilters();
      });

    const brushG = svg.append('g').attr('class', 'scrubber-brush').call(brush);

    // Style the brush
    brushG.select('.selection')
      .attr('fill', 'var(--iris, #8071BC)').attr('fill-opacity', 0.12)
      .attr('stroke', 'var(--iris, #8071BC)').attr('stroke-opacity', 0.3)
      .attr('stroke-width', 1).attr('rx', 2);
    brushG.selectAll('.handle')
      .attr('fill', 'var(--iris, #8071BC)').attr('fill-opacity', 0.4)
      .attr('width', 3).attr('rx', 1.5);
    brushG.select('.overlay').style('cursor', 'default');
    brushG.select('.selection').style('cursor', 'default');
    brushG.selectAll('.handle').style('cursor', 'ew-resize');

    // ── Scroll-to-zoom: wheel zooms the x axis ──
    const zoom = d3.zoom()
      .scaleExtent([1, 20])
      .translateExtent([[0, 0], [width, height]])
      .extent([[0, 0], [width, height]])
      .filter(event => event.type === 'wheel' || event.type === 'dblclick')
      .on('zoom', function(event) {
        xCurrent = event.transform.rescaleX(xFull);
        drawBars();
        if (hsBrushExtent) {
          const newX0 = xCurrent(hsBrushExtent[0]);
          const newX1 = xCurrent(hsBrushExtent[1]);
          if (newX0 >= 0 && newX1 <= width) {
            brushG.call(brush.move, [newX0, newX1]);
          } else {
            brushG.call(brush.move, null);
            hsBrushExtent = null;
            applyHSFilters();
          }
        }
        updateDateLabels();
        hsScrubberZoomState = event.transform;
      });

    svg.call(zoom);
    svg.on('dblclick.zoom', function() {
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
      brushG.call(brush.move, null);
      hsBrushExtent = null;
      applyHSFilters();
    });

    // Restore previous zoom state
    if (hsScrubberZoomState) {
      svg.call(zoom.transform, hsScrubberZoomState);
    }
  }

  // ─── View Toggle ────────────────────────────────────────────────
  function switchView(view) {
    // Stop playback if switching away from disinfo
    if (view !== 'wheel' && isPlaying) resetPlayback();

    currentView = view;
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === view);
    });
    document.getElementById('panel-wheel').classList.toggle('hidden', view !== 'wheel');
    document.getElementById('panel-hatespeech').classList.toggle('hidden', view !== 'hatespeech');

    // Toggle stat pills
    document.getElementById('stats-disinfo').classList.toggle('hidden', view !== 'wheel');
    document.getElementById('stats-hs').classList.toggle('hidden', view !== 'hatespeech');

    // Toggle filter sections
    document.getElementById('disinfo-filters').classList.toggle('hidden', view !== 'wheel');
    document.getElementById('hs-filters').classList.toggle('hidden', view !== 'hatespeech');

    // Toggle playback visibility (only for disinfo)
    document.getElementById('playback-bar').style.display = view === 'wheel' ? '' : 'none';

    // Hide detail panel
    hideDetail();

    if (view === 'wheel') {
      renderWheel();
      renderScrubber();
    } else if (view === 'hatespeech') {
      renderHSWheel();
      renderHSScrubber();
    }
  }

  function onResize() {
    if (currentView === 'wheel') renderWheel();
    else if (currentView === 'hatespeech') renderHSWheel();
    if (currentView === 'wheel') renderScrubber();
    else renderHSScrubber();
  }

  // ─── Init ───────────────────────────────────────────────────────
  async function init() {
    createTooltip();
    await loadData();
    buildFilterUI();
    buildHSFilterUI();
    updateStats();
    updateHSStats();
    renderWheel();
    renderScrubber();

    document.getElementById('btn-wheel').addEventListener('click', () => switchView('wheel'));
    document.getElementById('btn-hatespeech').addEventListener('click', () => switchView('hatespeech'));
    document.getElementById('btn-reset').addEventListener('click', resetFilters);
    document.getElementById('detail-close').addEventListener('click', hideDetail);
    document.getElementById('hs-detail-close').addEventListener('click', hideDetail);
    document.getElementById('btn-play').addEventListener('click', togglePlayback);
    document.getElementById('btn-step-back').addEventListener('click', pbStepBack);
    document.getElementById('btn-step-fwd').addEventListener('click', pbStepForward);
    document.getElementById('btn-pb-reset').addEventListener('click', resetPlayback);
    document.getElementById('playback-track').addEventListener('click', pbScrub);

    const pbTrack = document.getElementById('playback-track');
    let pbDragging = false;
    pbTrack.addEventListener('mousedown', (e) => { pbDragging = true; pbScrub(e); });
    window.addEventListener('mousemove', (e) => { if (pbDragging) pbScrub(e); });
    window.addEventListener('mouseup', () => { pbDragging = false; });

    const speedBtn = document.getElementById('btn-speed');
    if (speedBtn) speedBtn.addEventListener('click', cycleSpeed);

    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code === 'Space' && currentView === 'wheel') { e.preventDefault(); togglePlayback(); }
      else if (e.code === 'ArrowRight' && pbData) { e.preventDefault(); pbStepForward(); }
      else if (e.code === 'ArrowLeft' && pbData) { e.preventDefault(); pbStepBack(); }
      else if (e.code === 'Escape' && pbData) { e.preventDefault(); resetPlayback(); }
    });

    let resizeTimer;
    window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(onResize, 200); });

    const dateExtent = d3.extent(allEvents, d => new Date(d.date));
    const fmt = d3.timeFormat('%b %Y');
    if (dateExtent[0]) {
      document.getElementById('date-range-start').textContent = fmt(dateExtent[0]);
      document.getElementById('date-range-end').textContent = fmt(dateExtent[1]);
    }
  }

  init();

  // ═══ MANUAL SUBMISSION MODAL ═══
  (function initSubmitModal() {
    const overlay = document.getElementById('submit-modal');
    if (!overlay) return;
    const btnOpen = document.getElementById('btn-submit');
    const btnClose = document.getElementById('modal-close');
    const btnCancel = document.getElementById('btn-cancel-submit');
    const btnSubmit = document.getElementById('btn-submit-event');

    const stepUrl = document.getElementById('step-url');
    const stepSuccess = document.getElementById('step-success');

    const GH_REPO = 'KSvend/brace4peace';
    const SUBMISSIONS_PATH = 'docs/data/submissions.json';

    async function persistSubmission(submission) {
      // Read current submissions file from GitHub
      try {
        const getResp = await fetch(`https://api.github.com/repos/${GH_REPO}/contents/${SUBMISSIONS_PATH}`);
        let submissions = [];
        let sha = null;
        if (getResp.ok) {
          const fileData = await getResp.json();
          sha = fileData.sha;
          submissions = JSON.parse(atob(fileData.content));
        }
        submissions.push(submission);
        const content = btoa(unescape(encodeURIComponent(JSON.stringify(submissions, null, 2))));
        const putBody = {
          message: `Submit: ${submission.type} post — ${submission.url.substring(0, 60)}`,
          content: content,
          committer: { name: 'BRACE4PEACE Dashboard', email: 'krdasv@me.com' }
        };
        if (sha) putBody.sha = sha;
        const putResp = await fetch(`https://api.github.com/repos/${GH_REPO}/contents/${SUBMISSIONS_PATH}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(putBody)
        });
        return putResp.ok;
      } catch (e) {
        console.warn('Could not persist submission to GitHub:', e);
        return false;
      }
    }

    function detectPlatform(url) {
      if (!url) return 'Unknown';
      if (url.includes('x.com') || url.includes('twitter.com')) return 'X (Twitter)';
      if (url.includes('facebook.com') || url.includes('fb.com')) return 'Facebook';
      if (url.includes('tiktok.com')) return 'TikTok';
      if (url.includes('telegram')) return 'Telegram';
      if (url.includes('youtube.com') || url.includes('youtu.be')) return 'YouTube';
      if (url.includes('instagram.com')) return 'Instagram';
      return 'Web';
    }

    function detectCountry(url) {
      const lower = url.toLowerCase();
      if (/somalia|somali|mogadishu|puntland|al.?shabaab/.test(lower)) return 'Somalia';
      if (/south.?sudan|juba|sspdf|akobo|olony/.test(lower)) return 'South Sudan';
      if (/kenya|nairobi|ruto|gachagua/.test(lower)) return 'Kenya';
      return 'Regional';
    }

    function showStep(step) {
      [stepUrl, stepSuccess].forEach(s => { if (s) s.classList.add('hidden'); });
      if (step) step.classList.remove('hidden');
      if (btnSubmit) btnSubmit.classList.toggle('hidden', step === stepSuccess);
      if (btnCancel) btnCancel.textContent = step === stepSuccess ? 'Close' : 'Cancel';
    }

    function openModal() {
      overlay.classList.remove('hidden');
      showStep(stepUrl);
      const urlInput = document.getElementById('submit-url');
      const noteInput = document.getElementById('submit-note');
      if (urlInput) { urlInput.value = ''; urlInput.focus(); }
      if (noteInput) noteInput.value = '';
    }
    function closeModal() {
      overlay.classList.add('hidden');
      showStep(stepUrl);
    }

    if (btnOpen) btnOpen.addEventListener('click', openModal);
    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !overlay.classList.contains('hidden')) closeModal();
    });

    // Type toggle buttons
    let submitType = 'disinfo';
    const btnTypeDisinfo = document.getElementById('submit-type-disinfo');
    const btnTypeHS = document.getElementById('submit-type-hs');
    if (btnTypeDisinfo && btnTypeHS) {
      [btnTypeDisinfo, btnTypeHS].forEach(btn => {
        btn.addEventListener('click', () => {
          submitType = btn.dataset.type;
          btnTypeDisinfo.classList.toggle('active', submitType === 'disinfo');
          btnTypeHS.classList.toggle('active', submitType === 'hatespeech');
        });
      });
    }

    if (btnSubmit) {
      btnSubmit.addEventListener('click', () => {
        const url = document.getElementById('submit-url')?.value?.trim();
        if (!url) { alert('Please enter a URL.'); return; }
        if (!/^https?:\/\//i.test(url)) { alert('Please enter a valid URL starting with http:// or https://'); return; }

        const note = document.getElementById('submit-note')?.value?.trim() || '';
        const platform = detectPlatform(url);
        const country = detectCountry(url);
        const date = new Date().toISOString().split('T')[0];

        const submission = {
          type: submitType === 'hatespeech' ? 'hatespeech' : 'disinfo',
          url: url,
          note: note,
          platform: platform,
          country: country,
          date: date,
          submitted_at: new Date().toISOString(),
          status: 'pending'
        };

        // Persist to GitHub (async, don't block UI)
        persistSubmission(submission).then(ok => {
          if (!ok) console.warn('Submission saved locally but GitHub persist failed — will be picked up on next pipeline run if committed manually.');
        });

        if (submitType === 'hatespeech') {
          const postId = `sub-${Date.now().toString(36)}`;
          const newPost = {
            i: postId,
            t: note || 'Submitted link — pending analysis',
            d: date,
            c: country,
            p: platform === 'X (Twitter)' ? 'x' : platform === 'Facebook' ? 'facebook' : platform === 'TikTok' ? 'tiktok' : 'web',
            a: 'submitted',
            l: url,
            pr: 'Hate',
            co: 0,
            tx: 'medium',
            st: [],
            txd: { sev: 'medium', ins: 'medium', idt: 'medium', thr: 'medium' },
            en: { l: 0, s: 0, c: 0 },
            qc: 'auto_sweep',
            _source: 'user_submission'
          };
          allHSPosts.push(newPost);
          filteredHSPosts = [...allHSPosts];
          showStep(stepSuccess);
          showToast('Hate speech post submitted — will be processed on next pipeline run');
        } else {
          const eventId = `SUB-${date}-${String(allEvents.length + 1).padStart(3, '0')}`;
          const newEvent = {
            id: eventId,
            date: date,
            country: country,
            event_type: 'DISINFO',
            disinfo_subtype: 'pending_classification',
            threat_level: 'P3 MODERATE',
            headline: `Submitted link — pending analysis`,
            summary: note || `Link submitted for automated review.`,
            actors: [],
            platforms: [platform],
            sources: [{ publisher: 'User submission', url: url, date: date }],
            spread: 1,
            disinfo_narratives: [],
            related_events: [],
            disinfo_confidence: 'PENDING',
            disinfo_justification: 'Submitted by user — awaiting automated analysis',
            detection_method: 'manual_submission',
            content_observed: false,
            source_basis: 'user_submission',
            verification_status: 'pending_review',
            narrative_families: [],
            ve_related: false,
            al_shabaab_related: false,
            tags: ['user_submission', 'pending_analysis'],
            data_source: 'manual',
            detected_by: 'user',
            detection_timestamp: new Date().toISOString()
          };
          allEvents.push(newEvent);
          applyFilters();
          showStep(stepSuccess);
          showToast('Disinfo post submitted — will be processed on next pipeline run');
        }
      });

      const urlInput = document.getElementById('submit-url');
      if (urlInput) {
        urlInput.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') { e.preventDefault(); btnSubmit.click(); }
        });
      }
    }

    function showToast(msg) {
      const t = document.createElement('div');
      t.className = 'toast';
      t.textContent = msg;
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    }
  })();

  // ═══ MOBILE ENHANCEMENTS ═══
  (function initMobile() {
    const isMobile = () => window.innerWidth <= 900;

    // --- Mobile Filter Drawer ---
    const filterFab = document.getElementById('mobile-filter-fab');
    const filterDrawer = document.getElementById('mobile-filter-drawer');
    const filterOverlay = document.getElementById('mobile-filter-overlay');
    const filterClose = document.getElementById('mobile-filter-close');
    const filterBody = document.getElementById('mobile-filter-body');
    const filterBadge = document.getElementById('mobile-filter-badge');
    const mobileResetBtn = document.getElementById('mobile-reset-filters');
    const mobileApplyBtn = document.getElementById('mobile-apply-filters');

    function openFilterDrawer() {
      // Clone current sidebar content into the drawer
      const sidebar = document.getElementById('sidebar');
      if (sidebar && filterBody) {
        filterBody.innerHTML = '';
        // Clone the visible filter sections (not hidden ones)
        const disinfoFilters = document.getElementById('disinfo-filters');
        const hsFilters = document.getElementById('hs-filters');
        if (currentView === 'wheel' && disinfoFilters) {
          const clone = disinfoFilters.cloneNode(true);
          clone.classList.remove('hidden');
          clone.id = 'mobile-disinfo-filters';
          filterBody.appendChild(clone);
        } else if (currentView === 'hatespeech' && hsFilters) {
          const clone = hsFilters.cloneNode(true);
          clone.classList.remove('hidden');
          clone.id = 'mobile-hs-filters';
          filterBody.appendChild(clone);
        }
        // Re-bind click handlers on cloned filter items
        filterBody.querySelectorAll('.filter-item').forEach(item => {
          item.addEventListener('click', () => {
            // Find the matching item in the real sidebar and click it
            const filterGroup = item.closest('.filter-group');
            const filterIdx = Array.from(filterGroup.children).indexOf(item);
            const origGroupId = item.closest('.filter-group')?.id?.replace('mobile-', '');
            // Match by text content
            const itemText = item.querySelector('span:nth-child(2)')?.textContent;
            const realItems = sidebar.querySelectorAll('.filter-item');
            for (const ri of realItems) {
              const riText = ri.querySelector('span:nth-child(2)')?.textContent;
              if (riText === itemText) {
                ri.click();
                // Sync the active state
                item.classList.toggle('active', ri.classList.contains('active'));
                break;
              }
            }
            updateFilterBadge();
          });
        });
      }

      filterOverlay?.classList.add('active');
      filterOverlay?.classList.remove('hidden');
      requestAnimationFrame(() => {
        filterDrawer?.classList.add('open');
      });
    }

    function closeFilterDrawer() {
      filterDrawer?.classList.remove('open');
      setTimeout(() => {
        filterOverlay?.classList.remove('active');
      }, 300);
    }

    function updateFilterBadge() {
      if (!filterBadge) return;
      let count = 0;
      if (currentView === 'wheel') {
        count = filters.country.size + filters.type.size + filters.subtype.size + filters.narrative.size;
      } else {
        count = hsFilters.country.size + hsFilters.classification.size + hsFilters.platform.size + hsFilters.toxicity.size + hsFilters.subtype.size;
      }
      if (count > 0) {
        filterBadge.textContent = count;
        filterBadge.classList.remove('hidden');
      } else {
        filterBadge.classList.add('hidden');
      }
    }

    if (filterFab) filterFab.addEventListener('click', openFilterDrawer);
    if (filterClose) filterClose.addEventListener('click', closeFilterDrawer);
    if (filterOverlay) filterOverlay.addEventListener('click', closeFilterDrawer);
    if (mobileApplyBtn) mobileApplyBtn.addEventListener('click', closeFilterDrawer);
    if (mobileResetBtn) {
      mobileResetBtn.addEventListener('click', () => {
        document.getElementById('btn-reset')?.click();
        closeFilterDrawer();
        updateFilterBadge();
      });
    }

    // --- Mobile Submit FAB ---
    const submitFab = document.getElementById('mobile-submit-fab');
    if (submitFab) {
      submitFab.addEventListener('click', () => {
        document.getElementById('btn-submit')?.click();
      });
    }

    // --- Detail Panel swipe-to-dismiss ---
    const detailPanel = document.getElementById('detail-panel');
    if (detailPanel) {
      let startY = 0;
      let currentY = 0;
      let isDragging = false;

      detailPanel.addEventListener('touchstart', (e) => {
        if (!isMobile()) return;
        if (detailPanel.scrollTop > 5) return; // Only drag from top
        startY = e.touches[0].clientY;
        isDragging = true;
      }, { passive: true });

      detailPanel.addEventListener('touchmove', (e) => {
        if (!isDragging || !isMobile()) return;
        currentY = e.touches[0].clientY;
        const diff = currentY - startY;
        if (diff > 0) {
          detailPanel.style.transition = 'none';
          detailPanel.style.transform = `translateY(${diff}px)`;
        }
      }, { passive: true });

      detailPanel.addEventListener('touchend', () => {
        if (!isDragging || !isMobile()) return;
        isDragging = false;
        detailPanel.style.transition = '';
        const diff = currentY - startY;
        if (diff > 80) {
          // Dismiss
          hideDetail();
        } else {
          detailPanel.style.transform = '';
          if (detailPanel.classList.contains('open')) {
            detailPanel.style.transform = 'translateY(0)';
          }
        }
      }, { passive: true });
    }

    // Update badge whenever filters change
    const origApplyFilters = window._origApply;
    // Use MutationObserver on sidebar to detect filter changes
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      const observer = new MutationObserver(() => updateFilterBadge());
      observer.observe(sidebar, { subtree: true, attributes: true, attributeFilter: ['class'] });
    }

    // Initial badge update
    updateFilterBadge();
  })();
})();

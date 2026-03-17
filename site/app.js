// MERLx — East Africa Disinfo Monitor v4.2
// Narrative-Based Disinformation Tracking
// Narrative Lifecycle Playback with Heat Model
// D3.js Radial Threat Wheel + Timeline + Narrative Trends

(function() {
  'use strict';

  // ─── State ───────────────────────────────────────────────────────
  let allEvents = [];
  let narrativeRef = {};
  let filteredEvents = [];
  let selectedEvent = null;
  let pinnedEvent = null;
  let currentView = 'wheel';
  let brushExtent = null;
  let wheelPositions = new Map();
  let wheelZoom = null;
  let wheelG = null;
  let playbackTimer = null;
  let playbackIndex = 0;
  let isPlaying = false;
  let playbackSpeed = 1; // 1=normal, 2=fast, 0.5=slow

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
  // Dark = Disinformation, Light = Context for each country
  const COUNTRY_COLORS = {
    'Somalia':     { dark: '#1A3A34', light: '#A8C5BC', mid: '#4A7A6E' },
    'South Sudan': { dark: '#CA5D0F', light: '#E8C4A8', mid: '#D9936A' },
    'Kenya':       { dark: '#6B5CA8', light: '#C4BBE0', mid: '#9A8DC8' },
    'Regional':    { dark: '#4A3F6B', light: '#B8B3CC', mid: '#7E76A0' }
  };

  // Helper: get event color based on country + type
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

  // Subtype colors are no longer used for dots — kept for badge display only
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

  // ─── Playback Constants ─────────────────────────────────────────
  const HEAT_PER_EVENT = 1.0;         // Heat added per event
  const HEAT_DECAY_PER_WEEK = 0.25;   // Heat lost per week with no events
  const HEAT_VISIBLE_THRESHOLD = 0.05; // Below this → narrative disappears
  const HEAT_MAX = 5.0;               // Cap for heat
  const FADE_OUT_WEEKS = 4;           // ~4 weeks to fully fade (1.0 / 0.25 = 4)

  // ─── Data Loading ────────────────────────────────────────────────
  async function loadData() {
    const [eventsRes, narrRes] = await Promise.all([
      fetch('data/events.json'),
      fetch('data/narratives.json')
    ]);
    allEvents = await eventsRes.json();
    narrativeRef = await narrRes.json();
    filteredEvents = [...allEvents];
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
    else if (currentView === 'timeline') renderTimeline();
    else if (currentView === 'trends') renderNarrativeTrends();
  }

  function toggleFilter(category, value) {
    if (filters[category].has(value)) {
      filters[category].delete(value);
    } else {
      filters[category].add(value);
    }
    applyFilters();
    updateFilterUI();
  }

  function resetFilters() {
    Object.keys(filters).forEach(k => filters[k].clear());
    brushExtent = null;
    applyFilters();
    updateFilterUI();
    renderScrubber();
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

    // Event Type (DISINFO vs CONTEXT)
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

    // Disinformation Narratives
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

  function updateFilterUI() {
    document.querySelectorAll('.filter-item').forEach(item => {
      const cat = item.dataset.category;
      const val = item.dataset.value;
      if (!cat || !val) return;
      const isActive = filters[cat].size === 0 || filters[cat].has(val);
      item.classList.toggle('active', isActive);
    });
  }

  function updateStats() {
    document.getElementById('stat-total').textContent = filteredEvents.length;
    document.getElementById('stat-disinfo').textContent = filteredEvents.filter(e => e.event_type === 'DISINFO').length;
    document.getElementById('stat-context').textContent = filteredEvents.filter(e => e.event_type === 'CONTEXT').length;
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

  // ─── Detail Panel ────────────────────────────────────────────────
  function showDetail(d) {
    const placeholder = document.getElementById('detail-placeholder');
    const content = document.getElementById('detail-content');
    placeholder.style.display = 'none';
    content.classList.remove('hidden');

    // Type badge
    const typeEl = document.getElementById('detail-type');
    typeEl.textContent = d.event_type === 'DISINFO' ? 'Disinfo' : 'Context';
    typeEl.className = 'detail-badge ' + (d.event_type === 'DISINFO' ? 'disinfo' : 'context');

    // Subtype badge
    const subtypeEl = document.getElementById('detail-subtype');
    if (d.disinfo_subtype) {
      subtypeEl.textContent = SUBTYPE_LABELS[d.disinfo_subtype] || d.disinfo_subtype;
      subtypeEl.className = 'detail-badge subtype';
      subtypeEl.style.display = '';
      subtypeEl.style.background = SUBTYPE_COLORS[d.disinfo_subtype] + '1A';
      subtypeEl.style.color = SUBTYPE_COLORS[d.disinfo_subtype];
    } else {
      subtypeEl.style.display = 'none';
    }

    // Country badge
    const countryEl = document.getElementById('detail-country');
    countryEl.textContent = d.country;
    countryEl.className = 'detail-badge country';

    document.getElementById('detail-headline').textContent = d.headline;
    document.getElementById('detail-date').textContent = d.date;
    document.getElementById('detail-summary').textContent = d.summary;

    // Extracted False Claims
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

    // Reach & Spread
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

    // Disinfo Narratives
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

    // Related events
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

  function hideDetail() {
    pinnedEvent = null;
    document.getElementById('detail-placeholder').style.display = '';
    document.getElementById('detail-content').classList.add('hidden');
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
  // Helper: get just the IDs from getUsedNarratives
  function getUsedNarrativeIds() {
    return getUsedNarratives().map(d => d[0]);
  }

  // ─── RADIAL THREAT WHEEL ──────────────────────────────────────
  function renderWheel() {
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
      .attr('x', width - 12).attr('y', height - 12)
      .attr('text-anchor', 'end')
      .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '9px')
      .style('fill', '#9E9E9E').style('opacity', 0.6)
      .text('Scroll to zoom · Drag to pan · Double-click to reset');
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

    // Narrative segments — proportional to event count
    const usedNarrativesWithCounts = getUsedNarratives(); // [[nid, count], ...]
    if (usedNarrativesWithCounts.length === 0) return;
    const usedNarratives = usedNarrativesWithCounts.map(d => d[0]);
    const narrWeights = new Map(usedNarrativesWithCounts);
    const totalWeight = usedNarrativesWithCounts.reduce((s, d) => s + d[1], 0);
    const segmentPad = 0.02;
    // Give each narrative a minimum slice so thin ones are still visible
    const MIN_ANGLE = 0.12; // ~7 degrees minimum
    const totalPad = segmentPad * 2 * usedNarratives.length;
    const totalMinAngle = MIN_ANGLE * usedNarratives.length;
    const availAngle = 2 * Math.PI - totalPad;
    // If min angles exceed available, just use min (equal tiny slices)
    const useMin = totalMinAngle >= availAngle;
    // Precompute cumulative start angles
    const narrAngles = []; // [{nid, start, end, count}]
    let cumAngle = -Math.PI / 2;
    usedNarrativesWithCounts.forEach(([nid, count]) => {
      let segAngle;
      if (useMin) {
        segAngle = (2 * Math.PI) / usedNarratives.length;
      } else {
        // Proportional: distribute available space minus minimums by weight, then add minimum
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
      const size = Math.max(3, Math.min(12, 2 + e.spread * 1.5));
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
  // NARRATIVE LIFECYCLE PLAYBACK
  // Each narrative has a "heat" value that rises with events and decays
  // over time. The wheel dynamically shows only narratives that are
  // currently "alive" (heat > threshold). Narratives grow, fade, and
  // disappear organically.
  // ═══════════════════════════════════════════════════════════════════

  function buildWeekTimeline(events) {
    // Generate array of Monday-start weeks spanning the data range
    const dates = events.map(e => new Date(e.date));
    const minDate = d3.min(dates);
    const maxDate = d3.max(dates);
    const firstMonday = d3.timeMonday.floor(minDate);
    const lastMonday = d3.timeMonday.ceil(maxDate);
    return d3.timeMonday.range(firstMonday, d3.timeMonday.offset(lastMonday, 1));
  }

  function computeNarrativeHeatTimeline(events, weeks) {
    // For each week, compute which narratives are "alive" and their heat
    // Returns array of { week, narrativeHeat: Map<nid, heat>, newEvents: [...] }

    // Index events by week
    const eventsByWeek = new Map();
    weeks.forEach(w => eventsByWeek.set(w.getTime(), []));
    events.forEach(e => {
      const d = new Date(e.date);
      const weekStart = d3.timeMonday.floor(d);
      const key = weekStart.getTime();
      if (eventsByWeek.has(key)) {
        eventsByWeek.get(key).push(e);
      } else {
        // Event falls before first week — attach to first week
        const firstKey = weeks[0].getTime();
        eventsByWeek.get(firstKey).push(e);
      }
    });

    // Walk through weeks, maintaining heat state
    const heatState = new Map(); // nid → heat
    const timeline = [];

    weeks.forEach(week => {
      const weekEvents = eventsByWeek.get(week.getTime()) || [];

      // 1. Decay all existing narratives
      for (const [nid, heat] of heatState) {
        const newHeat = heat - HEAT_DECAY_PER_WEEK;
        if (newHeat <= HEAT_VISIBLE_THRESHOLD) {
          heatState.delete(nid);
        } else {
          heatState.set(nid, newHeat);
        }
      }

      // 2. Add heat from this week's events
      const weekNarrEvents = new Map(); // nid → events this week
      weekEvents.forEach(e => {
        (e.disinfo_narratives || []).forEach(nid => {
          if (!narrativeRef[nid]) return;
          const current = heatState.get(nid) || 0;
          heatState.set(nid, Math.min(HEAT_MAX, current + HEAT_PER_EVENT));
          if (!weekNarrEvents.has(nid)) weekNarrEvents.set(nid, []);
          weekNarrEvents.get(nid).push(e);
        });
      });

      // 3. Snapshot this week's state
      timeline.push({
        week,
        narrativeHeat: new Map(heatState),
        newEvents: weekEvents,
        weekNarrEvents
      });
    });

    return timeline;
  }

  function renderPlaybackWheel(weekState, allWeeksSoFar, allNarrativesSeen) {
    // Renders the wheel for a specific moment in time during playback
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

    // Defs
    const defs = svg.append('defs');
    const glowFilter = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'blur');
    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'blur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    // Pulse animation filter
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

    // Ring guides (faded during playback for drama)
    const rings = [
      { r: innerRadius + (maxRadius - innerRadius) * 0.15, label: 'P1 CRITICAL', color: '#B83A2A' },
      { r: innerRadius + (maxRadius - innerRadius) * 0.50, label: 'P2 HIGH', color: '#CA5D0F' },
      { r: innerRadius + (maxRadius - innerRadius) * 0.85, label: 'P3 MODERATE', color: '#1A3A34' }
    ];
    rings.forEach(ring => {
      g.append('circle').attr('r', ring.r).attr('class', 'wheel-ring')
        .style('stroke', ring.color).style('opacity', 0.08);
    });

    // Get active narratives (heat > threshold) — sorted by heat descending
    const activeNarratives = [...weekState.narrativeHeat.entries()]
      .filter(([_, heat]) => heat > HEAT_VISIBLE_THRESHOLD)
      .sort((a, b) => b[1] - a[1]);

    if (activeNarratives.length === 0) {
      // Show empty state
      g.append('text').attr('text-anchor', 'middle').attr('dy', 0)
        .style('font-family', "'DM Serif Display', Georgia, serif").style('font-style', 'italic')
        .style('font-size', '16px').style('fill', '#9E9E9E').style('opacity', 0.5)
        .text('No active narratives');
      return;
    }

    // Proportional angle assignment based on heat (bigger heat = bigger slice)
    // Only active narratives get slices
    const segmentPad = 0.02;
    const PB_MIN_ANGLE = 0.12;
    const totalHeat = activeNarratives.reduce((s, [_, h]) => s + h, 0);
    const pbAvailAngle = 2 * Math.PI - segmentPad * 2 * activeNarratives.length;
    const pbTotalMinAngle = PB_MIN_ANGLE * activeNarratives.length;
    const pbUseMin = pbTotalMinAngle >= pbAvailAngle;
    // Build angle map for active narratives
    const pbNarrAngles = new Map(); // nid -> {start, end}
    let pbCumAngle = -Math.PI / 2;
    activeNarratives.forEach(([nid, heat]) => {
      let segAngle;
      if (pbUseMin) {
        segAngle = (2 * Math.PI) / activeNarratives.length;
      } else {
        const extraAngle = pbAvailAngle - pbTotalMinAngle;
        segAngle = PB_MIN_ANGLE + (heat / totalHeat) * extraAngle + segmentPad * 2;
      }
      pbNarrAngles.set(nid, { start: pbCumAngle + segmentPad, end: pbCumAngle + segAngle - segmentPad });
      pbCumAngle += segAngle;
    });

    // Collect all visible events (from all weeks so far)
    const visibleEvents = [];
    const visibleEventIds = new Set();
    allWeeksSoFar.forEach(ws => {
      ws.newEvents.forEach(e => {
        if (!visibleEventIds.has(e.id)) {
          visibleEventIds.add(e.id);
          visibleEvents.push(e);
        }
      });
    });

    // Draw segment lines and labels for active narratives
    activeNarratives.forEach(([nid, heat]) => {
      const narr = narrativeRef[nid];
      if (!narr) return;
      const angles = pbNarrAngles.get(nid);
      if (!angles) return;
      const startAngle = angles.start;
      const endAngle = angles.end;
      const heatNorm = Math.min(heat / HEAT_MAX, 1); // 0..1

      // Segment divider line — opacity scales with heat
      const x1 = Math.cos(startAngle) * innerRadius;
      const y1 = Math.sin(startAngle) * innerRadius;
      const x2 = Math.cos(startAngle) * maxRadius;
      const y2 = Math.sin(startAngle) * maxRadius;
      // Derive narrative country color
      const playNarrPrefix = nid.split('-')[1];
      const playNarrCountryMap = { 'SS': 'South Sudan', 'SO': 'Somalia', 'KE': 'Kenya', 'FP': 'Regional' };
      const narrColor = countryDark(playNarrCountryMap[playNarrPrefix] || 'Regional');

      g.append('line').attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2)
        .style('stroke', narrColor)
        .style('opacity', 0.1 + heatNorm * 0.3);

      // Segment background arc — glow effect showing heat intensity
      const arc = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(innerRadius + (maxRadius - innerRadius) * (0.3 + heatNorm * 0.7))
        .startAngle(startAngle + Math.PI / 2)
        .endAngle(endAngle + Math.PI / 2);
      g.append('path').attr('d', arc)
        .attr('fill', narrColor)
        .attr('fill-opacity', heatNorm * 0.06)
        .attr('class', 'narrative-heat-arc');

      // Label — opacity and size scale with heat
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

    // Map events to positions — only active narratives get dots
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

    // Links for this week's new events
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

    // Dots — all visible events, but newer ones in this week pulse
    const thisWeekIds = new Set(weekState.newEvents.map(e => e.id));
    const dotsGroup = g.append('g').attr('class', 'dots-group');

    visibleEvents.forEach(e => {
      const pos = positions.get(e.id);
      if (!pos) return;

      // Events in narratives that are fading get reduced opacity
      const bestNarr = (e.disinfo_narratives || []).find(n => activeNarrIds.has(n));
      const narrHeat = bestNarr ? (weekState.narrativeHeat.get(bestNarr) || 0) : 0;
      const heatNorm = Math.min(narrHeat / HEAT_MAX, 1);

      const isNew = thisWeekIds.has(e.id);
      const baseSize = Math.max(3, Math.min(12, 2 + e.spread * 1.5));
      const color = eventColor(e);

      // Opacity based on narrative heat + event type
      let opacity;
      if (e.event_type === 'CONTEXT') {
        opacity = 0.08 + heatNorm * 0.25;
      } else {
        opacity = 0.4 + heatNorm * 0.55;
      }

      const dot = dotsGroup.append('circle').attr('class', 'event-dot')
        .attr('cx', pos.x).attr('cy', pos.y)
        .attr('r', isNew ? 0 : baseSize)
        .attr('fill', color)
        .attr('fill-opacity', opacity)
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

      // New event pulse animation
      if (isNew) {
        dot.transition().duration(400).ease(d3.easeElasticOut.amplitude(1).period(0.4))
          .attr('r', baseSize * 1.8)
          .transition().duration(300)
          .attr('r', baseSize);
      }
    });

    // Show active narrative count in center
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

  // ─── ANIMATED TIME PLAYBACK (v4.1 — Narrative Lifecycle) ────────
  // ─── Playback engine (play / pause / scrub / step) ─────────
  let pbData = null;  // { heatTimeline, allNarrativesSeen } — persists while playback is active
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
    if (nextIdx >= pbData.heatTimeline.length) {
      // Reached the end — pause at final frame
      pausePlayback();
      return;
    }
    pbRenderFrame(nextIdx);
    pbScheduleNext();
  }

  function startPlayback() {
    if (isPlaying) return;
    // If we have cached data and are resuming from pause, just resume
    if (pbPaused && pbData) {
      isPlaying = true;
      pbPaused = false;
      pbUpdateUI();
      pbScheduleNext();
      return;
    }
    // Fresh start
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
    renderWheel();
  }

  function togglePlayback() {
    if (isPlaying) pausePlayback();
    else startPlayback();
  }

  function pbStepForward() {
    if (!pbData) {
      // Initialize data but don't auto-play
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

  // Legacy alias for stopPlayback references
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

  // ─── TIMELINE VIEW ──────────────────────────────────────────────
  function renderTimeline() {
    const svg = d3.select('#timeline-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('panel-timeline');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    const margin = { top: 30, right: 30, bottom: 40, left: 60 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const dateExtent = d3.extent(filteredEvents, d => new Date(d.date));
    if (!dateExtent[0]) return;
    const x = d3.scaleTime().domain(dateExtent).range([0, innerW]);
    const countries = ['Somalia', 'South Sudan', 'Kenya', 'Regional'];
    const y = d3.scaleBand().domain(countries).range([0, innerH]).padding(0.15);

    g.append('g').attr('class', 'timeline-axis').attr('transform', `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(d3.timeMonth.every(2)).tickFormat(d3.timeFormat('%b %Y')));
    g.append('g').attr('class', 'timeline-axis').call(d3.axisLeft(y));

    countries.forEach((c, i) => {
      g.append('rect').attr('x', 0).attr('y', y(c)).attr('width', innerW).attr('height', y.bandwidth())
        .attr('fill', i % 2 === 0 ? '#EDE9E1' : '#F5F3EE').attr('fill-opacity', 0.6);
      g.append('rect').attr('x', 0).attr('y', y(c)).attr('width', 3).attr('height', y.bandwidth())
        .attr('fill', countryDark(c)).attr('fill-opacity', 0.5);
    });

    filteredEvents.forEach(e => {
      const ex = x(new Date(e.date));
      const ey = y(e.country);
      if (ex === undefined || ey === undefined) return;
      const hash = e.id.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
      const jitter = (((hash * 9301 + 49297) % 233280) / 233280 - 0.5) * y.bandwidth() * 0.6;
      const color = eventColor(e);
      const size = Math.max(3, Math.min(10, 2 + e.spread * 1.2));

      g.append('circle').attr('class', 'timeline-event event-dot')
        .attr('cx', ex).attr('cy', ey + y.bandwidth() / 2 + jitter)
        .attr('r', size).attr('fill', color)
        .attr('fill-opacity', e.event_type === 'CONTEXT' ? 0.35 : 0.9)
        .datum(e)
        .on('mouseenter', function(event) {
          if (!pinnedEvent) { showTooltip(event, e); showDetail(e); } else showTooltip(event, e);
        })
        .on('mousemove', function(event) { showTooltip(event, e); })
        .on('mouseleave', function() { hideTooltip(); if (!pinnedEvent) hideDetail(); })
        .on('click', function() {
          if (pinnedEvent && pinnedEvent.id === e.id) { pinnedEvent = null; hideDetail(); }
          else { pinnedEvent = e; showDetail(e); }
        });
    });
  }

  // ─── NARRATIVE TREND CHARTS ─────────────────────────────────────
  function renderNarrativeTrends() {
    const container = document.getElementById('panel-trends');
    container.innerHTML = '';

    const narrCounts = {};
    filteredEvents.forEach(e => (e.disinfo_narratives || []).forEach(n => {
      narrCounts[n] = (narrCounts[n] || 0) + 1;
    }));
    const topNarratives = Object.entries(narrCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(d => d[0])
      .filter(nid => narrativeRef[nid]);

    if (topNarratives.length === 0) {
      container.innerHTML = '<div class="trends-empty">No narratives for current filters</div>';
      return;
    }

    const dateExtent = d3.extent(filteredEvents, d => new Date(d.date));
    if (!dateExtent[0]) return;
    const months = d3.timeMonth.range(d3.timeMonth.floor(dateExtent[0]), d3.timeMonth.offset(d3.timeMonth.floor(dateExtent[1]), 1));

    const narrativeData = {};
    topNarratives.forEach(nid => {
      narrativeData[nid] = months.map(m => {
        const mEnd = d3.timeMonth.offset(m, 1);
        let count = 0;
        let disinfoCount = 0;
        filteredEvents.forEach(e => {
          const d = new Date(e.date);
          if (d >= m && d < mEnd && (e.disinfo_narratives || []).includes(nid)) {
            count++;
            if (e.event_type === 'DISINFO') disinfoCount++;
          }
        });
        return { month: m, count, disinfoCount };
      });
    });

    const chartW = 420, chartH = 90;
    const margin = { top: 22, right: 12, bottom: 18, left: 30 };
    const innerW = chartW - margin.left - margin.right;
    const innerH = chartH - margin.top - margin.bottom;
    const x = d3.scaleTime().domain(dateExtent).range([0, innerW]);

    topNarratives.forEach(nid => {
      const data = narrativeData[nid];
      const narr = narrativeRef[nid];
      const card = document.createElement('div');
      card.className = 'trend-card';
      const maxCount = d3.max(data, d => d.count) || 1;
      const y = d3.scaleLinear().domain([0, maxCount]).range([innerH, 0]);
      // Derive color from narrative's country prefix
      const narrPrefix = nid.split('-')[1];
      const narrCountryMap = { 'SS': 'South Sudan', 'SO': 'Somalia', 'KE': 'Kenya', 'FP': 'Regional' };
      const color = countryDark(narrCountryMap[narrPrefix] || 'Regional');

      const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgEl.setAttribute('viewBox', `0 0 ${chartW} ${chartH}`);
      svgEl.setAttribute('width', '100%');
      svgEl.setAttribute('height', chartH);
      svgEl.style.display = 'block';
      const svgD3 = d3.select(svgEl);
      const g = svgD3.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      // Context area (total)
      g.append('path').datum(data)
        .attr('d', d3.area().x(d => x(d.month)).y0(innerH).y1(d => y(d.count)).curve(d3.curveMonotoneX))
        .attr('fill', color).attr('fill-opacity', 0.08);
      // Disinfo area
      g.append('path').datum(data)
        .attr('d', d3.area().x(d => x(d.month)).y0(innerH).y1(d => y(d.disinfoCount)).curve(d3.curveMonotoneX))
        .attr('fill', color).attr('fill-opacity', 0.25);
      // Total line
      g.append('path').datum(data)
        .attr('d', d3.line().x(d => x(d.month)).y(d => y(d.count)).curve(d3.curveMonotoneX))
        .attr('fill', 'none').attr('stroke', color).attr('stroke-width', 1).attr('stroke-dasharray', '3,2');
      // Disinfo line
      g.append('path').datum(data)
        .attr('d', d3.line().x(d => x(d.month)).y(d => y(d.disinfoCount)).curve(d3.curveMonotoneX))
        .attr('fill', 'none').attr('stroke', color).attr('stroke-width', 1.5);

      // Y axis
      g.append('g').attr('class', 'trend-axis').call(d3.axisLeft(y).ticks(3).tickSize(-innerW))
        .selectAll('text').style('font-size', '8px');
      g.selectAll('.trend-axis .domain').remove();
      g.selectAll('.trend-axis line').style('stroke', '#E5E1DA').style('stroke-dasharray', '2,2');

      // X axis
      g.append('g').attr('class', 'trend-axis').attr('transform', `translate(0,${innerH})`)
        .call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat("%b'%y")))
        .selectAll('text').style('font-size', '8px');

      // Title
      svgD3.append('text').attr('x', margin.left).attr('y', 13)
        .style('font-family', "'Inter', sans-serif").style('font-size', '10px')
        .style('font-weight', '600').style('fill', '#111111').style('letter-spacing', '-0.2px')
        .text(narr.short_name || narr.name);

      const totalDisinfo = d3.sum(data, d => d.disinfoCount);
      const totalAll = d3.sum(data, d => d.count);
      svgD3.append('text').attr('x', chartW - margin.right).attr('y', 13).attr('text-anchor', 'end')
        .style('font-family', "'IBM Plex Mono', monospace").style('font-size', '9px')
        .style('fill', color).style('font-weight', '600')
        .text(`${totalDisinfo} disinfo / ${totalAll} total`);

      card.appendChild(svgEl);
      container.appendChild(card);
    });
  }

  // ─── SCRUBBER ───────────────────────────────────────────────────
  function renderScrubber() {
    const svg = d3.select('#scrubber-svg');
    svg.selectAll('*').remove();
    const container = document.getElementById('scrubber-track');
    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    const dateExtent = d3.extent(allEvents, d => new Date(d.date));
    const x = d3.scaleTime().domain(dateExtent).range([0, width]);

    const bins = d3.bin().domain(dateExtent)
      .thresholds(d3.timeWeek.range(dateExtent[0], dateExtent[1]))
      .value(d => new Date(d.date))(allEvents);
    const yMax = d3.max(bins, b => b.length);
    const barH = d3.scaleLinear().domain([0, yMax]).range([0, height - 6]);

    bins.forEach(bin => {
      const bx = x(bin.x0);
      const bw = Math.max(1, x(bin.x1) - x(bin.x0) - 1);
      const bh = barH(bin.length);
      const disinfoCount = bin.filter(e => e.event_type === 'DISINFO').length;
      const contextCount = bin.length - disinfoCount;
      const totalBh = bh;
      const disinfoBh = totalBh * (disinfoCount / bin.length);
      const contextBh = totalBh - disinfoBh;
      // Context portion (bottom, lighter)
      if (contextBh > 0) {
        svg.append('rect').attr('class', 'scrubber-bar')
          .attr('x', bx).attr('y', height - totalBh - 2).attr('width', bw).attr('height', contextBh)
          .attr('fill', '#D5D0C7').attr('opacity', 0.5).attr('rx', 1);
      }
      // Disinfo portion (top, darker)
      if (disinfoBh > 0) {
        svg.append('rect').attr('class', 'scrubber-bar')
          .attr('x', bx).attr('y', height - disinfoBh - 2).attr('width', bw).attr('height', disinfoBh)
          .attr('fill', '#8071BC').attr('opacity', 0.75).attr('rx', 1);
      }
    });

    const brush = d3.brushX().extent([[0, 0], [width, height]])
      .on('end', function(event) {
        if (!event.selection) { brushExtent = null; }
        else {
          brushExtent = event.selection.map(x.invert);
          const fmt = d3.timeFormat('%b %Y');
          document.getElementById('date-range-start').textContent = fmt(brushExtent[0]);
          document.getElementById('date-range-end').textContent = fmt(brushExtent[1]);
        }
        applyFilters();
      });
    svg.append('g').attr('class', 'brush').call(brush);
  }

  // ─── View Toggle ────────────────────────────────────────────────
  function switchView(view) {
    currentView = view;
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === view);
    });
    document.getElementById('panel-wheel').classList.toggle('hidden', view !== 'wheel');
    document.getElementById('panel-timeline').classList.toggle('hidden', view !== 'timeline');
    document.getElementById('panel-trends').classList.toggle('hidden', view !== 'trends');
    if (view === 'wheel') renderWheel();
    else if (view === 'timeline') renderTimeline();
    else if (view === 'trends') renderNarrativeTrends();
  }

  function onResize() {
    if (currentView === 'wheel') renderWheel();
    else if (currentView === 'timeline') renderTimeline();
    else if (currentView === 'trends') renderNarrativeTrends();
    renderScrubber();
  }

  // ─── Init ───────────────────────────────────────────────────────
  async function init() {
    createTooltip();
    await loadData();
    buildFilterUI();
    updateStats();
    renderWheel();
    renderScrubber();

    document.getElementById('btn-wheel').addEventListener('click', () => switchView('wheel'));
    document.getElementById('btn-timeline').addEventListener('click', () => switchView('timeline'));
    document.getElementById('btn-trends').addEventListener('click', () => switchView('trends'));
    document.getElementById('btn-reset').addEventListener('click', resetFilters);
    document.getElementById('detail-close').addEventListener('click', hideDetail);
    document.getElementById('btn-play').addEventListener('click', togglePlayback);
    document.getElementById('btn-step-back').addEventListener('click', pbStepBack);
    document.getElementById('btn-step-fwd').addEventListener('click', pbStepForward);
    document.getElementById('btn-pb-reset').addEventListener('click', resetPlayback);
    document.getElementById('playback-track').addEventListener('click', pbScrub);

    // Drag-scrub on playback track
    const pbTrack = document.getElementById('playback-track');
    let pbDragging = false;
    pbTrack.addEventListener('mousedown', (e) => { pbDragging = true; pbScrub(e); });
    window.addEventListener('mousemove', (e) => { if (pbDragging) pbScrub(e); });
    window.addEventListener('mouseup', () => { pbDragging = false; });

    const speedBtn = document.getElementById('btn-speed');
    if (speedBtn) speedBtn.addEventListener('click', cycleSpeed);

    // Keyboard shortcuts for playback
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
    document.getElementById('date-range-start').textContent = fmt(dateExtent[0]);
    document.getElementById('date-range-end').textContent = fmt(dateExtent[1]);
  }

  init();

  // ═══ MANUAL SUBMISSION MODAL — SIMPLE LINK + SUBMIT ═══
  (function initSubmitModal() {
    const overlay = document.getElementById('submit-modal');
    if (!overlay) return;
    const btnOpen = document.getElementById('btn-submit');
    const btnClose = document.getElementById('modal-close');
    const btnCancel = document.getElementById('btn-cancel-submit');
    const btnSubmit = document.getElementById('btn-submit-event');

    const stepUrl = document.getElementById('step-url');
    const stepSuccess = document.getElementById('step-success');

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
      // Hide submit button on success, show on URL step
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

    // Submit handler — takes the link, creates a pending event, shows success
    if (btnSubmit) {
      btnSubmit.addEventListener('click', () => {
        const url = document.getElementById('submit-url')?.value?.trim();
        if (!url) { alert('Please enter a URL.'); return; }
        if (!/^https?:\/\//i.test(url)) { alert('Please enter a valid URL starting with http:// or https://'); return; }

        const note = document.getElementById('submit-note')?.value?.trim() || '';
        const platform = detectPlatform(url);
        const country = detectCountry(url);
        const date = new Date().toISOString().split('T')[0];
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
        showToast('Link submitted for review');
      });

      // Enter key submits
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
})();

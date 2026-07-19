/**
 * ARIA — Main Results Table (interactive)
 *
 *  - Reads assets/data/main_table.json
 *  - Renders an Apple-style data table with:
 *      · column views: "compact" / "all metrics" / "ranking" (toggle)
 *      · category filter chips (ablation, rag-baseline, aria)
 *      · per-row mini bar (visualises the chosen metric)
 *      · auto-generated per-column mini-charts below the table
 *  - No build step. Pure DOM + D3-shaped helpers.
 */
(function () {
  'use strict';

  var root;
  var data;
  var state = {
    view: 'compact',        // 'compact' | 'all' | 'ranking'
    categories: { ablation: true, 'rag-baseline': true, aria: true },
    sortKey: 'overall',
    sortDir: 'desc',
    highlightKey: 'overall',
  };

  function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function fmt(val, format) {
    if (val == null || isNaN(val)) return '—';
    if (format === 'pct') return (val * (val > 1.5 ? 1 : 100)).toFixed(val > 1.5 ? 1 : 0) + (val > 1.5 ? '' : '%');
    if (format === 'ms') return Math.round(val) + ' ms';
    return String(val);
  }

  function fmtRaw(val, format) {
    if (val == null || isNaN(val)) return '—';
    if (format === 'pct') {
      // values are in [0,1] except phys_violation_pct and preference_pct (0..100)
      if (val > 1.5) return val.toFixed(1) + '%';
      return (val * 100).toFixed(0) + '%';
    }
    if (format === 'ms') return Math.round(val).toLocaleString() + ' ms';
    return String(val);
  }

  function visibleRows() {
    return data.rows.filter(function (r) { return state.categories[r.category]; });
  }

  function sortedRows() {
    var rows = visibleRows().slice();
    rows.sort(function (a, b) {
      var av = a[state.sortKey], bv = b[state.sortKey];
      if (av == null) return 1;
      if (bv == null) return -1;
      return state.sortDir === 'desc' ? bv - av : av - bv;
    });
    return rows;
  }

  function bestInColumn(key, format) {
    var rows = visibleRows();
    var best = -Infinity, dir = 'desc';
    if (key === 'latency_ms' || key === 'phys_violation_pct') dir = 'asc';
    rows.forEach(function (r) {
      var v = r[key];
      if (v == null) return;
      if (dir === 'desc') best = Math.max(best, v);
      else best = Math.min(best, v);
    });
    return best;
  }

  // ─── Mini bar inside a cell ───
  function miniBar(value, colMin, colMax, color, lowerIsBetter) {
    if (value == null) return '';
    var range = colMax - colMin;
    var pct = range > 0 ? ((value - colMin) / range) * 100 : 0;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    return '<div class="mt-cell-bar"><div class="mt-cell-bar__fill" style="width:' +
      pct.toFixed(1) + '%; background:' + color + ';"></div></div>';
  }

  // ─── Column views ───
  function getVisibleColumns() {
    if (state.view === 'all') return data.columns;
    if (state.view === 'ranking') {
      return data.columns.filter(function (c) { return c.key === 'overall' || c.key === 'phys_consistency' || c.key === 'preference_pct'; });
    }
    // compact default
    return data.columns.filter(function (c) { return c.key === 'forward_pooled' || c.key === 'inverse_pooled' || c.key === 'overall' || c.key === 'phys_consistency' || c.key === 'latency_ms'; });
  }

  function renderHeader() {
    var cols = getVisibleColumns();
    var html = '<tr>';
    html += '<th class="mt-th mt-th--method" data-sort="method" rowspan="2">Method</th>';
    html += '<th class="mt-th mt-th--bar" rowspan="2">Visual</th>';
    cols.forEach(function (c) {
      var sortInd = state.sortKey === c.key ? (state.sortDir === 'desc' ? ' ↓' : ' ↑') : '';
      html += '<th class="mt-th" data-sort="' + c.key + '" rowspan="2">' + c.label + sortInd + '</th>';
    });
    html += '</tr>';
    return html;
  }

  function renderRow(row) {
    var cols = getVisibleColumns();
    var html = '<tr>';
    html += '<td class="mt-td mt-td--method"><strong>' + row.method + '</strong>';
    if (row.preference_pct != null) {
      html += '<div class="mt-row-meta">' + row.preference_pct.toFixed(1) + '% judge preference</div>';
    }
    html += '</td>';
    var col = data.columns.find(function (c) { return c.key === state.highlightKey; });
    var color = getCSSVar(row.color_token) || '#0066cc';
    html += '<td class="mt-td mt-td--bar">' + miniBar(row[state.highlightKey], col.min, col.max, color) + '</td>';
    cols.forEach(function (c) {
      var v = row[c.key];
      var best = bestInColumn(c.key, c.format);
      var isBest = v != null && v === best;
      var cellColor = getCSSVar(row.color_token);
      html += '<td class="mt-td' + (isBest ? ' mt-td--best' : '') + '" data-key="' + c.key + '">';
      html += '<span class="mt-td__value" style="color:' + cellColor + '">' + fmtRaw(v, c.format) + '</span>';
      html += miniBar(v, c.min, c.max, cellColor, c.key === 'latency_ms' || c.key === 'phys_violation_pct');
      html += '</td>';
    });
    html += '</tr>';
    return html;
  }

  function renderTable() {
    var html = '<table class="mt-table">';
    html += '<thead>' + renderHeader() + '</thead>';
    html += '<tbody>';
    sortedRows().forEach(function (r) { html += renderRow(r); });
    html += '</tbody></table>';
    var t = document.getElementById('mt-table-host');
    if (t) t.innerHTML = html;
    bindSortHandlers();
  }

  function bindSortHandlers() {
    var ths = document.querySelectorAll('#mt-table-host th[data-sort]');
    Array.prototype.forEach.call(ths, function (th) {
      th.addEventListener('click', function () {
        var k = th.getAttribute('data-sort');
        if (k === 'method') return;
        if (state.sortKey === k) state.sortDir = state.sortDir === 'desc' ? 'asc' : 'desc';
        else { state.sortKey = k; state.sortDir = (k === 'latency_ms' || k === 'phys_violation_pct') ? 'asc' : 'desc'; }
        renderTable();
      });
    });
  }

  // ─── Per-column mini-chart (auto-generated) ───
  function renderColumnCharts() {
    var host = document.getElementById('mt-column-charts');
    if (!host) return;
    var html = '<div class="mt-col-charts">';
    data.columns.forEach(function (c) {
      var best = bestInColumn(c.key, c.format);
      var lowerBetter = c.key === 'latency_ms' || c.key === 'phys_violation_pct';
      html += '<div class="mt-col-chart" data-key="' + c.key + '">';
      html += '<h4 class="mt-col-chart__title">' + c.label + '</h4>';
      html += '<p class="mt-col-chart__desc">' + c.description + '</p>';
      html += '<div class="mt-col-chart__bars">';
      visibleRows().forEach(function (r) {
        var v = r[c.key];
        if (v == null) { html += '<div class="mt-col-chart__row mt-col-chart__row--empty"><span class="mt-col-chart__name">' + r.short + '</span><span class="mt-col-chart__val">—</span></div>'; return; }
        var pct = ((v - c.min) / (c.max - c.min)) * 100;
        if (pct < 0) pct = 0; if (pct > 100) pct = 100;
        var isBest = v === best;
        var color = getCSSVar(r.color_token);
        html += '<div class="mt-col-chart__row' + (isBest ? ' mt-col-chart__row--best' : '') + '">';
        html += '<span class="mt-col-chart__name">' + r.short + '</span>';
        html += '<span class="mt-col-chart__track"><span class="mt-col-chart__fill" style="width:' + pct.toFixed(1) + '%; background:' + color + ';"></span></span>';
        html += '<span class="mt-col-chart__val" style="color:' + color + '">' + fmtRaw(v, c.format) + '</span>';
        html += '</div>';
      });
      html += '</div>';
      html += '<div class="mt-col-chart__legend">' + (lowerBetter ? 'Lower is better' : 'Higher is better') + '</div>';
      html += '</div>';
    });
    html += '</div>';
    host.innerHTML = html;
  }

  // ─── Header controls (view toggle, category filter, highlight selector) ───
  function renderControls() {
    var cats = ['ablation', 'rag-baseline', 'aria'];
    var catLabels = { 'ablation': 'Ablations', 'rag-baseline': 'RAG baselines', 'aria': 'ARIA' };
    var html = '<div class="mt-controls">';
    html += '<div class="mt-controls__row">';
    html += '<div class="mt-controls__group">';
    html += '<span class="mt-controls__label">View:</span>';
    ['compact', 'all', 'ranking'].forEach(function (v) {
      var lbl = v === 'compact' ? 'Compact' : v === 'all' ? 'All metrics' : 'Ranking';
      html += '<button class="mt-toggle' + (state.view === v ? ' is-active' : '') + '" data-view="' + v + '">' + lbl + '</button>';
    });
    html += '</div>';
    html += '<div class="mt-controls__group">';
    html += '<span class="mt-controls__label">Method category:</span>';
    cats.forEach(function (c) {
      html += '<label class="mt-chip"><input type="checkbox" data-cat="' + c + '"' + (state.categories[c] ? ' checked' : '') + '> ' + catLabels[c] + '</label>';
    });
    html += '</div>';
    html += '<div class="mt-controls__group">';
    html += '<span class="mt-controls__label">Row visual:</span>';
    html += '<select class="mt-select" id="mt-highlight-key">';
    data.columns.forEach(function (c) {
      html += '<option value="' + c.key + '"' + (state.highlightKey === c.key ? ' selected' : '') + '>' + c.label + '</option>';
    });
    html += '</select>';
    html += '</div>';
    html += '</div>';
    html += '</div>';
    var c = document.getElementById('mt-controls-host');
    if (c) c.innerHTML = html;
    bindControlHandlers();
  }

  function bindControlHandlers() {
    var viewBtns = document.querySelectorAll('#mt-controls-host .mt-toggle[data-view]');
    Array.prototype.forEach.call(viewBtns, function (b) {
      b.addEventListener('click', function () {
        state.view = b.getAttribute('data-view');
        renderControls();
        renderTable();
      });
    });
    var chips = document.querySelectorAll('#mt-controls-host .mt-chip input');
    Array.prototype.forEach.call(chips, function (c) {
      c.addEventListener('change', function () {
        state.categories[c.getAttribute('data-cat')] = c.checked;
        renderTable();
        renderColumnCharts();
      });
    });
    var sel = document.getElementById('mt-highlight-key');
    if (sel) sel.addEventListener('change', function () {
      state.highlightKey = sel.value;
      renderTable();
    });
  }

  // ─── Stat-tests panel ───
  function renderStatTests() {
    var host = document.getElementById('mt-stat-tests');
    if (!host || !data.stat_tests) return;
    var html = '<div class="mt-stat-tests">';
    html += '<h3 class="mt-stat-tests__title">Statistical significance</h3>';
    html += '<p class="mt-stat-tests__desc">' + data.stat_tests.description + '</p>';
    html += '<table class="mt-stat-table"><thead><tr><th>Comparison</th><th>p-value</th></tr></thead><tbody>';
    Object.keys(data.stat_tests.p_values).forEach(function (k) {
      var lbl = k.replace(/^vs_/, '').replace(/_/g, ' ');
      lbl = lbl.charAt(0).toUpperCase() + lbl.slice(1);
      html += '<tr><td>ARIA-FULL vs ' + lbl + '</td><td><code>' + data.stat_tests.p_values[k] + '</code></td></tr>';
    });
    html += '</tbody></table>';
    html += '<p class="mt-stat-tests__caption">All p-values &lt;&nbsp;0.001 unless noted; effect size (Cohen\'s d) ranges 0.6–1.4.</p>';
    html += '</div>';
    host.innerHTML = html;
  }

  // ─── Tier distribution donut ───
  function renderTierDonut() {
    var host = document.getElementById('mt-tier-donut');
    if (!host || !data.tier_distribution) return;
    var fwd = data.tier_distribution.forward;
    var inv = data.tier_distribution.inverse;
    var html = '<div class="mt-tier-donut">';
    html += '<h3>Tier activation by direction</h3>';
    html += '<div class="mt-tier-donut__pair">';
    function donut(title, dist) {
      var total = dist.tier1 + dist.tier2 + dist.tier3;
      var segs = [
        { key: 'Tier 1', pct: dist.tier1, color: getCSSVar('--tier-1') },
        { key: 'Tier 2', pct: dist.tier2, color: getCSSVar('--tier-2') },
        { key: 'Tier 3', pct: dist.tier3, color: getCSSVar('--tier-3') }
      ];
      var cumPct = 0;
      var r = 56, c = 2 * Math.PI * r;
      var ring = '';
      segs.forEach(function (s) {
        var dash = (s.pct / total) * c;
        var gap = c - dash;
        ring += '<circle r="' + r + '" cx="80" cy="80" fill="none" stroke="' + s.color + '" stroke-width="22" stroke-dasharray="' + dash.toFixed(2) + ' ' + gap.toFixed(2) + '" stroke-dashoffset="' + (-cumPct * c / total).toFixed(2) + '" transform="rotate(-90 80 80)"></circle>';
        cumPct += s.pct;
      });
      var o = '<div class="mt-tier-donut__one">';
      o += '<h4>' + title + '</h4>';
      o += '<svg width="160" height="160" viewBox="0 0 160 160" role="img" aria-label="' + title + ' tier distribution">' + ring +
        '<text x="80" y="76" text-anchor="middle" font-family="var(--font-body)" font-size="22" font-weight="600" fill="var(--apple-ink)">' + (dist.tier1 * 100).toFixed(0) + '%</text>' +
        '<text x="80" y="96" text-anchor="middle" font-family="var(--font-body)" font-size="11" fill="var(--apple-ink-muted-48)">Tier 1</text></svg>';
      o += '<ul class="mt-tier-donut__legend">';
      segs.forEach(function (s) {
        o += '<li><span class="mt-tier-donut__swatch" style="background:' + s.color + '"></span>' + s.key + ' · ' + (s.pct * 100).toFixed(0) + '%</li>';
      });
      o += '</ul></div>';
      return o;
    }
    html += donut('Forward prediction', fwd);
    html += donut('Inverse design', inv);
    html += '</div>';
    html += '<p class="mt-tier-donut__caption">Asymmetric reachability: forward queries find a complete PSP path 62.5% of the time; inverse queries only 0%. The Tier 1 ↔ Tier 3 mix explains why ARIA is strong forward and conservative inverse.</p>';
    html += '</div>';
    host.innerHTML = html;
  }

  // ─── Boot ───
  function init() {
    var el = document.getElementById('main-table-root');
    if (!el) return;
    root = el;
    data = window.ARIA_MAIN_TABLE;
    if (!data || !data.rows) {
      // Try fetching
      fetch('assets/data/main_table.json').then(function (r) { return r.json(); }).then(function (j) {
        window.ARIA_MAIN_TABLE = j;
        data = j;
        render();
      }).catch(function (err) { console.error('[MainTable] failed to load', err); });
      return;
    }
    render();
  }

  function render() {
    renderControls();
    renderTable();
    renderColumnCharts();
    renderStatTests();
    renderTierDonut();
  }

  window.ARIA = window.ARIA || {};
  window.ARIA.mainTable = { init: init, setData: function (d) { data = d; window.ARIA_MAIN_TABLE = d; render(); } };
})();

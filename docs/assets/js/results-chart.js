/**
 * ResultsChart — D3 bar charts and visualizations for the ARIA results section.
 *
 * Loads data from '../data/benchmark_results.json' (falls back to built-in defaults).
 *
 * Exposes global class: ResultsChart
 */
(function () {
  'use strict';

  /* ── colour palette ─────────────────────────────────────────────── */
  const COLORS = {
    jhuBlue:   '#002D72',
    accent:    '#E8600A',
    ariaFull:  '#002D72',
    ariaCore:  '#5B9BD5',
    selfRAG:   '#7B2D8E',
    baseline:  '#9E9E9E',
    naiveKG:   '#E53935',
    t1Blue:    '#1565C0',
    t2Amber:   '#F9A825',
    t3Grey:    '#9E9E9E',
    bg:        '#FAFAFA',
    gridLine:  '#E0E0E0',
    text:      '#333333',
    labelGrey: '#666666',
  };

  /* ── default benchmark data ──────────────────────────────────────── */
  const DEFAULT_DATA = {
    methods: ['Baseline', 'Naive KG', 'Self-RAG', 'ARIA-CORE', 'ARIA-FULL'],
    scores: {
      forward_prediction:  [0.44, 0.50, 0.56, 0.72, 0.83],
      inverse_design:      [0.40, 0.45, 0.52, 0.68, 0.81],
      overall:             [0.42, 0.475, 0.54, 0.70, 0.82],
    },
    tier_distribution: {
      forward_prediction: { T1: 0.625, T2: 0.125, T3: 0.25 },
      inverse_design:     { T1: 0.0,  T2: 0.20,  T3: 0.80 },
    },
    physical_consistency: [
      { method: 'ARIA-FULL', value: 0.81 },
      { method: 'ARIA-CORE', value: 0.72 },
      { method: 'Self-RAG',  value: 0.56 },
      { method: 'Baseline',  value: 0.44 },
      { method: 'Naive KG',  value: 0.45 },
    ],
  };

  const METHOD_COLORS = {
    'Baseline':  COLORS.baseline,
    'Naive KG':  COLORS.naiveKG,
    'Self-RAG':  COLORS.selfRAG,
    'ARIA-CORE': COLORS.ariaCore,
    'ARIA-FULL': COLORS.ariaFull,
  };

  /* ── ResultsChart class ──────────────────────────────────────────── */
  class ResultsChart {
    /**
     * @param {string|d3.Selection} selector  Container for all charts
     * @param {Object} [opts]
     * @param {string} [opts.dataPath]  Path to JSON data file
     */
    constructor(selector, opts = {}) {
      this.container = d3.select(selector);
      this.dataPath = opts.dataPath || '../data/benchmark_results.json';
      this.data = null;
      this.activeMetric = 'overall';

      this._loadData().then(() => {
        this._build();
      });
    }

    async _loadData() {
      try {
        const response = await fetch(this.dataPath);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const json = await response.json();
        /* Merge: prefer JSON fields, fall back to defaults */
        this.data = {
          methods:             json.methods             || DEFAULT_DATA.methods,
          scores:             json.scores             || DEFAULT_DATA.scores,
          tier_distribution:  json.tier_distribution  || DEFAULT_DATA.tier_distribution,
          physical_consistency: json.physical_consistency || DEFAULT_DATA.physical_consistency,
        };
      } catch {
        this.data = DEFAULT_DATA;
      }
    }

    _build() {
      this.container.selectAll('*').remove();

      this.root = this.container.append('div')
        .attr('class', 'results-chart-root')
        .style('font-family', "'Inter', 'Helvetica Neue', Arial, sans-serif")
        .style('max-width', '960px')
        .style('margin', '0 auto');

      this._buildGroupedBar();
      this._buildTierCharts();
      this._buildConsistencyBar();
    }

    /* ══════════════════════════════════════════════════════════════════
       GROUPED BAR CHART
       ══════════════════════════════════════════════════════════════════ */
    _buildGroupedBar() {
      const data = this.data;
      const margin = { top: 30, right: 30, bottom: 60, left: 50 };
      const width  = 620 - margin.left - margin.right;
      const height = 340 - margin.top - margin.bottom;

      const section = this.root.append('div')
        .style('margin-bottom', '32px');

      section.append('h3')
        .style('font-size', '18px')
        .style('font-weight', 700)
        .style('color', COLORS.jhuBlue)
        .style('margin', '0 0 4px 0')
        .text('Benchmark Scores');

      /* Toggle buttons */
      const btnRow = section.append('div')
        .style('display', 'flex')
        .style('gap', '8px')
        .style('margin-bottom', '12px')
        .style('flex-wrap', 'wrap');

      const metrics = [
        { key: 'forward_prediction', label: 'Forward Prediction' },
        { key: 'inverse_design',     label: 'Inverse Design' },
        { key: 'overall',            label: 'Overall' },
      ];

      this._barButtons = [];
      metrics.forEach(m => {
        const btn = btnRow.append('button')
          .style('padding', '5px 14px')
          .style('font-size', '12px')
          .style('font-weight', 600)
          .style('border-radius', '5px')
          .style('cursor', 'pointer')
          .style('border', `2px solid ${m.key === this.activeMetric ? COLORS.jhuBlue : COLORS.gridLine}`)
          .style('background', m.key === this.activeMetric ? COLORS.jhuBlue : '#fff')
          .style('color', m.key === this.activeMetric ? '#fff' : COLORS.jhuBlue)
          .style('transition', 'all 0.2s ease')
          .text(m.label)
          .on('click', () => this._switchMetric(m.key));
        this._barButtons.push({ el: btn, key: m.key });
      });

      const svgEl = section.append('svg')
        .attr('viewBox', `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
        .style('width', '100%')
        .style('max-width', '620px')
        .style('height', 'auto');

      this._barSvg = svgEl.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      this._barW = width;
      this._barH = height;

      /* Scales */
      this._xScale = d3.scaleBand()
        .domain(data.methods)
        .range([0, width])
        .padding(0.25);

      this._yScale = d3.scaleLinear()
        .domain([0, 1])
        .range([height, 0]);

      this._drawGroupedBar();
    }

    _drawGroupedBar() {
      const data = this.data;
      const svg = this._barSvg;
      const x = this._xScale;
      const y = this._yScale;
      const W = this._barW;
      const H = this._barH;

      svg.selectAll('*').remove();

      /* Grid lines */
      const ticks = y.ticks(5);
      ticks.forEach(t => {
        svg.append('line')
          .attr('x1', 0).attr('x2', W)
          .attr('y1', y(t)).attr('y2', y(t))
          .attr('stroke', COLORS.gridLine)
          .attr('stroke-dasharray', '3 3')
          .attr('stroke-width', 0.5);
      });

      /* Y axis */
      svg.append('g')
        .attr('class', 'y-axis')
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('.0%')))
        .call(g => g.select('.domain').remove())
        .call(g => g.selectAll('text').attr('fill', COLORS.labelGrey).attr('font-size', 11));

      /* X axis */
      svg.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${H})`)
        .call(d3.axisBottom(x))
        .call(g => g.select('.domain').attr('stroke', COLORS.gridLine))
        .call(g => g.selectAll('text')
          .attr('fill', COLORS.labelGrey)
          .attr('font-size', 11)
          .attr('font-weight', d => d === 'ARIA-FULL' ? 700 : 400));

      /* Bars */
      const scores = data.scores[this.activeMetric];

      svg.selectAll('.bar')
        .data(data.methods.map((m, i) => ({ method: m, value: scores[i], idx: i })))
        .join('rect')
        .attr('class', 'bar')
        .attr('x', d => x(d.method))
        .attr('y', H)
        .attr('width', x.bandwidth())
        .attr('height', 0)
        .attr('rx', 4)
        .attr('fill', d => METHOD_COLORS[d.method] || COLORS.jhuBlue)
        .attr('opacity', d => d.method === 'ARIA-FULL' ? 1 : 0.85)
        .transition()
        .duration(800)
        .delay((d, i) => i * 80)
        .attr('y', d => y(d.value))
        .attr('height', d => H - y(d.value));

      /* ARIA-FULL glow */
      const fullIdx = data.methods.indexOf('ARIA-FULL');
      if (fullIdx >= 0) {
        const defs = this._barSvg.append('defs');
        const glow = defs.append('filter').attr('id', 'bar-glow');
        glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
        glow.append('feMerge').selectAll('feMergeNode')
          .data(['blur', 'SourceGraphic'])
          .join('feMergeNode')
          .attr('in', d => d);

        svg.selectAll('.bar')
          .filter(d => d.method === 'ARIA-FULL')
          .attr('filter', 'url(#bar-glow)');
      }

      /* Value labels */
      svg.selectAll('.bar-label')
        .data(data.methods.map((m, i) => ({ method: m, value: scores[i] })))
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', d => x(d.method) + x.bandwidth() / 2)
        .attr('y', d => y(d.value) - 6)
        .attr('text-anchor', 'middle')
        .attr('font-size', 12)
        .attr('font-weight', 700)
        .attr('fill', COLORS.text)
        .text(d => (d.value * 100).toFixed(0) + '%')
        .attr('opacity', 0)
        .transition()
        .duration(600)
        .delay((d, i) => 400 + i * 80)
        .attr('opacity', 1);

      /* Tooltip on hover */
      const tooltip = d3.select(this.container.node().parentNode).select('.results-tooltip').size()
        ? d3.select(this.container.node().parentNode).select('.results-tooltip')
        : d3.select(this.container.node().parentNode).append('div')
          .attr('class', 'results-tooltip')
          .style('position', 'absolute')
          .style('background', '#fff')
          .style('border', `1px solid ${COLORS.gridLine}`)
          .style('border-radius', '6px')
          .style('padding', '8px 12px')
          .style('font-size', '12px')
          .style('pointer-events', 'none')
          .style('opacity', 0)
          .style('box-shadow', '0 2px 8px rgba(0,0,0,0.12)')
          .style('z-index', '10');

      svg.selectAll('.bar')
        .on('mouseenter', function (event, d) {
          d3.select(this).attr('opacity', 1);
          tooltip
            .style('opacity', 1)
            .html(`<strong>${d.method}</strong><br/>${(d.value * 100).toFixed(1)}%`);
        })
        .on('mousemove', function (event) {
          const [mx, my] = d3.pointer(event, this.container ? this.container.node() : document.body);
          tooltip
            .style('left', (event.pageX + 12) + 'px')
            .style('top', (event.pageY - 30) + 'px');
        })
        .on('mouseleave', function (event, d) {
          d3.select(this).attr('opacity', d.method === 'ARIA-FULL' ? 1 : 0.85);
          tooltip.style('opacity', 0);
        });
    }

    _switchMetric(key) {
      this.activeMetric = key;
      this._barButtons.forEach(b => {
        b.el
          .style('border-color', b.key === key ? COLORS.jhuBlue : COLORS.gridLine)
          .style('background', b.key === key ? COLORS.jhuBlue : '#fff')
          .style('color', b.key === key ? '#fff' : COLORS.jhuBlue);
      });
      this._drawGroupedBar();
    }

    /* ══════════════════════════════════════════════════════════════════
       TIER ACTIVATION PIE CHARTS
       ══════════════════════════════════════════════════════════════════ */
    _buildTierCharts() {
      const data = this.data;
      const section = this.root.append('div')
        .style('margin-bottom', '32px');

      section.append('h3')
        .style('font-size', '18px')
        .style('font-weight', 700)
        .style('color', COLORS.jhuBlue)
        .style('margin', '0 0 4px 0')
        .text('Tier Activation Distribution');

      const row = section.append('div')
        .style('display', 'flex')
        .style('gap', '24px')
        .style('flex-wrap', 'wrap');

      const tierData = data.tier_distribution;
      const configs = [
        { key: 'forward_prediction', label: 'Forward Prediction' },
        { key: 'inverse_design',     label: 'Inverse Design' },
      ];

      const tierColors = { T1: COLORS.t1Blue, T2: COLORS.t2Amber, T3: COLORS.t3Grey };
      const tierLabels = { T1: 'T1 Direct', T2: 'T2 Analogical', T3: 'T3 Fallback' };

      configs.forEach(cfg => {
        const dist = tierData[cfg.key];
        const pieData = Object.entries(dist).map(([k, v]) => ({ key: k, value: v }));

        const wrapper = row.append('div')
          .style('text-align', 'center');

        wrapper.append('div')
          .style('font-size', '13px')
          .style('font-weight', 600)
          .style('color', COLORS.text)
          .style('margin-bottom', '8px')
          .text(cfg.label);

        const size = 160;
        const radius = size / 2;
        const innerR = radius * 0.55;

        const svg = wrapper.append('svg')
          .attr('viewBox', `0 0 ${size} ${size}`)
          .style('width', size + 'px')
          .style('height', size + 'px');

        const g = svg.append('g')
          .attr('transform', `translate(${radius},${radius})`);

        const pie = d3.pie().value(d => d.value).sort(null);
        const arc = d3.arc().innerRadius(innerR).outerRadius(radius - 4);
        const labelArc = d3.arc().innerRadius(innerR + (radius - innerR) * 0.35).outerRadius(innerR + (radius - innerR) * 0.35);

        g.selectAll('path')
          .data(pie(pieData))
          .join('path')
          .attr('d', arc)
          .attr('fill', d => tierColors[d.data.key])
          .attr('stroke', '#fff')
          .attr('stroke-width', 2)
          .attr('opacity', 0)
          .transition()
          .duration(600)
          .delay((d, i) => i * 120)
          .attr('opacity', 1);

        /* Labels inside segments */
        g.selectAll('.pie-label')
          .data(pie(pieData))
          .join('text')
          .attr('class', 'pie-label')
          .attr('transform', d => `translate(${labelArc.centroid(d)})`)
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .attr('font-size', d => d.data.value > 0.15 ? 11 : 9)
          .attr('font-weight', 600)
          .attr('fill', d => d.data.key === 'T3' ? '#fff' : '#fff')
          .text(d => d.data.value > 0 ? (d.data.value * 100).toFixed(d.data.value < 0.1 ? 0 : 0) + '%' : '')
          .attr('opacity', 0)
          .transition()
          .duration(400)
          .delay(500)
          .attr('opacity', 1);

        /* Center label */
        const centerText = cfg.key === 'forward_prediction' ? 'T1: 62.5%' : 'T3: 80%';
        g.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '-0.2em')
          .attr('font-size', 11)
          .attr('font-weight', 600)
          .attr('fill', COLORS.jhuBlue)
          .text(cfg.key === 'forward_prediction' ? 'Mostly' : 'Mostly')
          .attr('opacity', 0)
          .transition().duration(400).delay(600).attr('opacity', 1);
        g.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '1.2em')
          .attr('font-size', 10)
          .attr('fill', COLORS.labelGrey)
          .text(cfg.key === 'forward_prediction' ? 'Tier 1 (Direct)' : 'Tier 3 (Fallback)')
          .attr('opacity', 0)
          .transition().duration(400).delay(600).attr('opacity', 1);
      });

      /* Tier legend */
      const legend = section.append('div')
        .style('display', 'flex')
        .style('gap', '16px')
        .style('justify-content', 'center')
        .style('margin-top', '8px')
        .style('flex-wrap', 'wrap');

      Object.entries(tierLabels).forEach(([k, label]) => {
        const item = legend.append('div')
          .style('display', 'flex')
          .style('align-items', 'center')
          .style('gap', '4px');

        item.append('span')
          .style('width', '12px')
          .style('height', '12px')
          .style('border-radius', '2px')
          .style('background', tierColors[k])
          .style('display', 'inline-block');

        item.append('span')
          .style('font-size', '11px')
          .style('color', COLORS.labelGrey)
          .text(label);
      });
    }

    /* ══════════════════════════════════════════════════════════════════
       PHYSICAL CONSISTENCY HORIZONTAL BAR CHART
       ══════════════════════════════════════════════════════════════════ */
    _buildConsistencyBar() {
      const data = this.data.physical_consistency;
      const section = this.root.append('div');

      section.append('h3')
        .style('font-size', '18px')
        .style('font-weight', 700)
        .style('color', COLORS.jhuBlue)
        .style('margin', '0 0 4px 0')
        .text('Physical Consistency');

      section.append('p')
        .style('font-size', '12px')
        .style('color', COLORS.labelGrey)
        .style('margin', '0 0 12px 0')
        .text('Percentage of predictions consistent with known physical constraints.');

      const margin = { top: 8, right: 60, bottom: 8, left: 110 };
      const barH = 32;
      const gap = 10;
      const W = 500 - margin.left - margin.right;
      const H = data.length * (barH + gap) - gap;

      const svg = section.append('svg')
        .attr('viewBox', `0 0 ${W + margin.left + margin.right} ${H + margin.top + margin.bottom}`)
        .style('width', '100%')
        .style('max-width', '560px')
        .style('height', 'auto');

      const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      const x = d3.scaleLinear().domain([0, 1]).range([0, W]);

      data.forEach((d, i) => {
        const yOff = i * (barH + gap);
        const color = METHOD_COLORS[d.method] || COLORS.jhuBlue;
        const isFull = d.method === 'ARIA-FULL';

        /* Background track */
        g.append('rect')
          .attr('x', 0).attr('y', yOff)
          .attr('width', W).attr('height', barH)
          .attr('fill', '#EEEEEE')
          .attr('rx', 4);

        /* Bar */
        const bar = g.append('rect')
          .attr('x', 0).attr('y', yOff)
          .attr('width', 0).attr('height', barH)
          .attr('fill', color)
          .attr('rx', 4)
          .attr('opacity', isFull ? 1 : 0.8);

        bar.transition()
          .duration(800)
          .delay(i * 100)
          .attr('width', x(d.value));

        /* Glow for ARIA-FULL */
        if (isFull) {
          const defs = svg.append('defs');
          const glow = defs.append('filter').attr('id', 'consistency-glow');
          glow.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'blur');
          glow.append('feMerge').selectAll('feMergeNode')
            .data(['blur', 'SourceGraphic'])
            .join('feMergeNode')
            .attr('in', dd => dd);
          bar.attr('filter', 'url(#consistency-glow)');
        }

        /* Method label */
        g.append('text')
          .attr('x', -8)
          .attr('y', yOff + barH / 2)
          .attr('text-anchor', 'end')
          .attr('dy', '0.35em')
          .attr('font-size', 12)
          .attr('font-weight', isFull ? 700 : 400)
          .attr('fill', COLORS.text)
          .text(d.method);

        /* Value label */
        g.append('text')
          .attr('x', x(d.value) + 6)
          .attr('y', yOff + barH / 2)
          .attr('dy', '0.35em')
          .attr('font-size', 12)
          .attr('font-weight', 700)
          .attr('fill', color)
          .text((d.value * 100).toFixed(0) + '%')
          .attr('opacity', 0)
          .transition()
          .duration(400)
          .delay(600 + i * 100)
          .attr('opacity', 1);
      });
    }
  }

  window.ResultsChart = ResultsChart;
})();
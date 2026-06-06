/**
 * TunnelingDemo — Side-by-side comparison of Baseline LLM vs Naive KG+LLM,
 * illustrating contextual tunneling.
 *
 * Exposes global class: TunnelingDemo
 */
(function () {
  'use strict';

  const COLORS = {
    jhuBlue:   '#002D72',
    accent:    '#E8600A',
    green:     '#2E7D32',
    red:       '#C62828',
    grey:      '#757575',
    greenBg:   '#E8F5E9',
    redBg:     '#FFEBEE',
    greyBg:    '#F5F5F5',
    panelBg:   '#FAFAFA',
    border:    '#E0E0E0',
  };

  /* ── pre-computed comparison data ─────────────────────────────────── */
  const QUERIES = [
    {
      id: 'q1',
      query: 'What are the electrical properties of CVD-grown MoS₂?',
      baseline: {
        title: 'Baseline LLM',
        subtitle: 'No KG evidence — relies on general training knowledge',
        segments: [
          { text: 'CVD-grown MoS₂ typically exhibits', type: 'neutral' },
          { text: ' moderate carrier mobility in the range of 1–10 cm²/Vs', type: 'green' },
          { text: ' for as-grown monolayers on SiO₂ substrates.', type: 'neutral' },
          { text: ' The on/off ratio can exceed 10⁷ in good-quality samples.', type: 'green' },
          { text: ' However, electrical properties are highly sensitive to growth conditions — temperature, precursor ratios, and substrate choice all play significant roles.', type: 'grey' },
          { text: ' Sulfur vacancies are commonly observed in CVD MoS₂ and may degrade performance,', type: 'grey' },
          { text: ' though the exact impact depends on defect density and distribution.', type: 'grey' },
        ],
      },
      naiveKG: {
        title: 'Naive KG+LLM',
        subtitle: 'All KG edges injected equally — no causal gating',
        segments: [
          { text: 'CVD-grown MoS₂ at 750°C ', type: 'green' },
          { text: 'has carrier mobility exceeding 40 cm²/Vs', type: 'red' },
          { text: ' due to improved crystallinity.', type: 'green' },
          { text: ' Re doping at 0.1 at% increases carrier mobility', type: 'red' },
          { text: ' by suppressing sulfur vacancies.', type: 'green' },
          { text: ' Nb doping enables n-type conductivity', type: 'red' },
          { text: ' with carrier densities above 10¹² cm⁻².', type: 'green' },
          { text: ' The on/off ratio exceeds 10⁷.', type: 'green' },
          { text: ' Sulfur annealing reduces photoluminescence intensity', type: 'red' },
          { text: ' in MoS₂.', type: 'neutral' },
        ],
        tunnelingSegments: [1, 3, 5, 8],
        explanations: {
          1: 'The KG edge “CVD temperature 750°C → carrier mobility” is a Processing→Property shortcut. The real causal path is CVD temp → crystallinity → mobility. Over-anchoring on the shortcut skips the mediating structure (crystallinity), leading to an overly confident and imprecise claim.',
          3: 'The KG edge “Re doping 0.1 at% → carrier mobility” is another P→P shortcut. The true path is Re doping → sulfur vacancy formation energy → drain current. Mobility is conflated with drain current — a related but distinct property.',
          5: 'The edge “Nb doping 1 at% → n-type conductivity” skips the mediating structure “electron carrier concentration.” This P→P shortcut leads the model to conflate doping directly with conductivity, ignoring the structural intermediary that governs the relationship.',
          8: 'The edge “Sulfur annealing → PL intensity” is a P→P shortcut with low confidence (0.50). The actual causal chain is: sulfur annealing → stoichiometry (S/Mo ratio) → reduced trap states → PL intensity. The shortcut also states PL intensity “decreases,” which contradicts the well-grounded S-to-P path showing that improved stoichiometry should increase PL.',
        },
      },
    },
    {
      id: 'q2',
      query: 'How does CVD temperature affect the on/off ratio of MoS₂ transistors?',
      baseline: {
        title: 'Baseline LLM',
        subtitle: 'No KG evidence — general knowledge',
        segments: [
          { text: 'Higher CVD growth temperatures generally produce larger MoS₂ grains', type: 'green' },
          { text: ' and fewer grain boundaries,', type: 'neutral' },
          { text: ' which can improve the on/off ratio.', type: 'grey' },
          { text: ' However, the relationship is not straightforward — higher temperatures also increase sulfur vacancy concentration,', type: 'grey' },
          { text: ' which may introduce trap states and degrade switching performance.', type: 'grey' },
          { text: ' Reported on/off ratios for monolayer MoS₂ FETs range from 10⁶ to 10⁸ depending on conditions.', type: 'green' },
        ],
      },
      naiveKG: {
        title: 'Naive KG+LLM',
        subtitle: 'All KG edges injected equally — no causal gating',
        segments: [
          { text: 'CVD temperature at 750°C directly increases the on/off ratio', type: 'red' },
          { text: ' of MoS₂ FETs.', type: 'neutral' },
          { text: ' The on/off ratio exceeds 10⁷', type: 'green' },
          { text: ' thanks to grain sizes exceeding 10 μm.', type: 'green' },
          { text: ' Higher CVD temperature also increases carrier mobility directly,', type: 'red' },
          { text: ' further boosting device performance.', type: 'neutral' },
        ],
        tunnelingSegments: [0, 4],
        explanations: {
          0: 'The KG has a P→P shortcut “CVD temp 750°C → carrier mobility” but no direct edge from CVD temp to on/off ratio. The actual causal path is: CVD temp → grain size → on/off ratio. The naive system incorrectly infers a direct Processing→Property link, treating temperature as a single-cause explanation.',
          4: 'The same P→P shortcut (“CVD temp → mobility”) is used again. In reality, the causal chain passes through crystallinity. The naive system conflates multiple distinct structural mediators.',
        },
      },
    },
    {
      id: 'q3',
      query: 'What happens to MoS₂ drain current when Re is added during growth?',
      baseline: {
        title: 'Baseline LLM',
        subtitle: 'No KG evidence — general knowledge only',
        segments: [
          { text: 'Re doping in MoS₂ is reported to reduce defect density', type: 'green' },
          { text: ' and improve field-effect device characteristics.', type: 'green' },
          { text: ' Some studies report drain current improvements,', type: 'green' },
          { text: ' though the mechanism — whether via vacancy suppression, carrier concentration changes, or reduced trap states — is debated.', type: 'grey' },
          { text: ' Quantitative estimates vary significantly across experiments.', type: 'grey' },
        ],
      },
      naiveKG: {
        title: 'Naive KG+LLM',
        subtitle: 'All KG edges injected equally — no causal gating',
        segments: [
          { text: 'Re doping at 0.1 at% increases drain current by approximately 10×', type: 'green' },
          { text: ' by directly increasing carrier mobility.', type: 'red' },
          { text: ' The mechanism is that Re directly suppresses sulfur vacancies', type: 'red' },
          { text: ' which reduces trap states.', type: 'green' },
          { text: ' Nb doping at 1 at% also directly increases n-type conductivity', type: 'red' },
          { text: ' in a similar manner.', type: 'neutral' },
        ],
        tunnelingSegments: [1, 2, 4],
        explanations: {
          1: 'The KG has a P→P shortcut “Re doping → carrier mobility” with moderate confidence (0.70). The actual causal chain is: Re doping → sulfur vacancy formation energy → drain current. Mobility and drain current are related but distinct properties — conflating them via the shortcut over-simplifies the mechanism.',
          2: 'The system states that Re “directly” suppresses sulfur vacancies. However, the KG actually records that Re increases sulfur vacancy formation energy (a Structure-level mediator). Skipping this mediator and going straight from Re doping to a Property-level conclusion is the hallmark of contextual tunneling.',
          4: 'The KG has a P→P shortcut “Nb doping → n-type conductivity” with low confidence (0.60). The true path is: Nb doping → electron carrier concentration → n-type conductivity. Naive injection treats this shortcut as equally authoritative as the complete chain, leading to overconfident claims.',
        },
      },
    },
  ];

  /* ── TunnelingDemo class ─────────────────────────────────────────── */
  class TunnelingDemo {
    /**
     * @param {string|Element} selector  Container element or selector
     * @param {Object} [opts]
     * @param {string[]} [opts.queries]  Which query indices to include (default: all)
     */
    constructor(selector, opts = {}) {
      this.container = d3.select(selector);
      this.queries = opts.queries || [0, 1, 2];
      this.currentIdx = 0;
      this.activeSegment = null;
      this._build();
    }

    _build() {
      this.container.selectAll('*').remove();

      this.root = this.container.append('div')
        .attr('class', 'tunneling-demo')
        .style('font-family', "'Inter', 'Helvetica Neue', Arial, sans-serif")
        .style('max-width', '960px')
        .style('margin', '0 auto');

      this._buildQuerySelector();
      this._buildQueryBanner();
      this._buildPanels();
      this._buildExplainer();
      this._render(0);
    }

    /* ── query toggle buttons ───────────────────────────────────────── */
    _buildQuerySelector() {
      const bar = this.root.append('div')
        .style('display', 'flex')
        .style('gap', '8px')
        .style('margin-bottom', '16px')
        .style('flex-wrap', 'wrap');

      this.buttons = [];
      this.queries.forEach((qi, i) => {
        const btn = bar.append('button')
          .style('padding', '6px 14px')
          .style('border', `2px solid ${i === 0 ? COLORS.jhuBlue : COLORS.border}`)
          .style('border-radius', '6px')
          .style('background', i === 0 ? COLORS.jhuBlue : '#fff')
          .style('color', i === 0 ? '#fff' : COLORS.jhuBlue)
          .style('font-size', '13px')
          .style('font-weight', 600)
          .style('cursor', 'pointer')
          .style('transition', 'all 0.2s ease')
          .text(`Example ${i + 1}`)
          .on('click', () => this._switchQuery(i));
        this.buttons.push(btn);
      });
    }

    _switchQuery(idx) {
      this.currentIdx = idx;
      this.activeSegment = null;
      this.buttons.forEach((btn, i) => {
        btn
          .style('border-color', i === idx ? COLORS.jhuBlue : COLORS.border)
          .style('background', i === idx ? COLORS.jhuBlue : '#fff')
          .style('color', i === idx ? '#fff' : COLORS.jhuBlue);
      });
      this._render(idx);
    }

    /* ── query banner ────────────────────────────────────────────────── */
    _buildQueryBanner() {
      this.queryBanner = this.root.append('div')
        .style('background', COLORS.panelBg)
        .style('border', `1px solid ${COLORS.border}`)
        .style('border-radius', '8px')
        .style('padding', '14px 18px')
        .style('margin-bottom', '16px')
        .style('text-align', 'center');
    }

    /* ── two panels ──────────────────────────────────────────────────── */
    _buildPanels() {
      this.panelsRow = this.root.append('div')
        .style('display', 'flex')
        .style('gap', '16px')
        .style('flex-wrap', 'wrap');

      this.leftPanel = this.panelsRow.append('div')
        .style('flex', '1 1 400px')
        .style('min-width', '280px');

      this.rightPanel = this.panelsRow.append('div')
        .style('flex', '1 1 400px')
        .style('min-width', '280px');
    }

    /* ── explainer area ─────────────────────────────────────────────── */
    _buildExplainer() {
      this.explainer = this.root.append('div')
        .style('margin-top', '12px')
        .style('padding', '0')
        .style('overflow', 'hidden')
        .style('max-height', '0px')
        .style('transition', 'max-height 0.4s ease, padding 0.4s ease');
    }

    /* ── render a specific query ─────────────────────────────────────── */
    _render(qi) {
      const q = QUERIES[qi];

      /* Query banner */
      this.queryBanner.html('');
      this.queryBanner.append('div')
        .style('font-size', '11px')
        .style('color', COLORS.grey)
        .style('text-transform', 'uppercase')
        .style('letter-spacing', '0.08em')
        .style('margin-bottom', '4px')
        .text('Shared Query');
      this.queryBanner.append('div')
        .style('font-size', '16px')
        .style('font-weight', 600)
        .style('color', COLORS.jhuBlue)
        .text(q.query);

      /* Left panel */
      this._renderPanel(this.leftPanel, q.baseline, 'baseline', qi);

      /* Right panel */
      this._renderPanel(this.rightPanel, q.naiveKG, 'naiveKG', qi);

      /* Clear explainer */
      this.explainer
        .style('max-height', '0px')
        .style('padding', '0')
        .html('');
    }

    _renderPanel(panelEl, data, type, qi) {
      panelEl.html('');

      const card = panelEl.append('div')
        .style('background', '#fff')
        .style('border', `1px solid ${COLORS.border}`)
        .style('border-radius', '10px')
        .style('padding', '16px')
        .style('box-shadow', '0 1px 4px rgba(0,0,0,0.06)');

      /* Header */
      const header = card.append('div')
        .style('margin-bottom', '10px');

      header.append('div')
        .style('font-size', '15px')
        .style('font-weight', 700)
        .style('color', type === 'baseline' ? COLORS.jhuBlue : COLORS.red)
        .text(data.title);

      header.append('div')
        .style('font-size', '11px')
        .style('color', COLORS.grey)
        .style('margin-top', '2px')
        .text(data.subtitle);

      /* Segments */
      const body = card.append('div')
        .style('font-size', '14px')
        .style('line-height', '1.7')
        .style('color', '#333');

      const segments = data.segments;
      const tunnelingSet = data.tunnelingSegments
        ? new Set(data.tunnelingSegments)
        : new Set();

      segments.forEach((seg, si) => {
        const span = body.append('span')
          .text(seg.text);

        if (seg.type === 'green') {
          span
            .style('background', COLORS.greenBg)
            .style('padding', '1px 3px')
            .style('border-radius', '3px')
            .style('color', COLORS.green)
            .style('font-weight', 600);
        } else if (seg.type === 'red') {
          span
            .style('background', COLORS.redBg)
            .style('padding', '1px 3px')
            .style('border-radius', '3px')
            .style('color', COLORS.red)
            .style('font-weight', 600)
            .style('cursor', 'pointer')
            .style('border-bottom', '2px wavy ' + COLORS.red)
            .on('mouseenter', function () {
              d3.select(this).style('background', '#FCA5A5');
            })
            .on('mouseleave', function () {
              d3.select(this).style('background', COLORS.redBg);
            })
            .on('click', () => {
              this._showExplainer(qi, si);
            });
        } else if (seg.type === 'grey') {
          span
            .style('background', COLORS.greyBg)
            .style('padding', '1px 3px')
            .style('border-radius', '3px')
            .style('color', COLORS.grey)
            .style('font-style', 'italic');
        }
      });

      /* Legend for this panel */
      const legend = card.append('div')
        .style('margin-top', '12px')
        .style('display', 'flex')
        .style('gap', '12px')
        .style('flex-wrap', 'wrap');

      const legendItems = [
        { color: COLORS.green, bg: COLORS.greenBg, label: 'Well-grounded' },
        { color: COLORS.red, bg: COLORS.redBg, label: 'Contextual tunneling' },
        { color: COLORS.grey, bg: COLORS.greyBg, label: 'Uncertain' },
      ];

      legendItems.forEach(item => {
        const row = legend.append('div')
          .style('display', 'flex')
          .style('align-items', 'center')
          .style('gap', '4px');

        row.append('span')
          .style('width', '10px')
          .style('height', '10px')
          .style('border-radius', '2px')
          .style('background', item.bg)
          .style('border', `1.5px solid ${item.color}`)
          .style('display', 'inline-block');

        row.append('span')
          .style('font-size', '10px')
          .style('color', COLORS.grey)
          .text(item.label);
      });
    }

    /* ── explainer for clicked red span ──────────────────────────────── */
    _showExplainer(qi, segIdx) {
      const q = QUERIES[qi];
      if (!q.naiveKG.explanations || !q.naiveKG.explanations[segIdx]) return;

      const text = q.naiveKG.explanations[segIdx];

      this.explainer.html('');
      this.explainer
        .style('max-height', '300px')
        .style('padding', '14px 18px');

      this.explainer.append('div')
        .style('display', 'flex')
        .style('align-items', 'flex-start')
        .style('gap', '10px')
        .call(div => {
          div.append('div')
            .style('font-size', '18px')
            .style('line-height', '1')
            .text('⚠️');

          div.append('div')
            .style('flex', '1')
            .call(inner => {
              inner.append('div')
                .style('font-size', '13px')
                .style('font-weight', 700)
                .style('color', COLORS.red)
                .style('margin-bottom', '4px')
                .text('What went wrong? — Contextual Tunneling Detected');

              inner.append('div')
                .style('font-size', '13px')
                .style('line-height', '1.6')
                .style('color', '#333')
                .text(text);
            });
        });
    }
  }

  window.TunnelingDemo = TunnelingDemo;
})();
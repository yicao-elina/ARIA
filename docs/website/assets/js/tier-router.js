/**
 * ARIA Tier Router — Interactive 3-Tier Cascade Routing Demo
 *
 * Simulates how ARIA routes a materials query through its three-tier
 * reasoning cascade with step-by-step animation. Uses D3.js v7 for
 * the mini knowledge-graph visualization.
 *
 * Depends on: D3.js v7, ../data/example_queries.json
 * Exposes: global TierRouter class
 */

/* global d3 */

class TierRouter {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`TierRouter: container "#${containerId}" not found`);
    }

    this.queries = [];
    this.currentQuery = null;
    this.currentStep = -1; // -1 = not started
    this.animationTimers = [];
    this.isRunning = false;

    // Color palette (JHU-inspired)
    this.colors = {
      tier1: '#1E88E5',
      tier2: '#FFC107',
      tier3: '#9E9E9E',
      processing: '#1565C0',
      structure: '#E65100',
      property: '#2E7D32',
      successGreen: '#43A047',
      warningAmber: '#FFA000',
      insufficientGrey: '#9E9E9E',
      bgDark: '#0A1929',
      bgCard: '#112240',
      bgCardHover: '#1A3050',
      border: '#1D3557',
      textPrimary: '#E6F1FF',
      textSecondary: '#8892B0',
      textMuted: '#5A6A8A',
      accentBlue: '#64FFDA',
    };

    this.stepDefs = [
      { num: 1, label: 'Entity Extraction', icon: 'search' },
      { num: 2, label: 'KG Matching', icon: 'share' },
      { num: 3, label: 'PSP Completeness', icon: 'verified' },
      { num: 4, label: 'Tier Activation', icon: 'bolt' },
    ];

    this._loadData();
  }

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async _loadData() {
    try {
      const resp = await fetch('../data/example_queries.json');
      const data = await resp.json();
      this.queries = data.queries || [];
    } catch (err) {
      console.warn('TierRouter: could not load example_queries.json, using built-in fallbacks', err);
      this.queries = this._fallbackQueries();
    }
    this._render();
  }

  _fallbackQueries() {
    return [
      {
        id: 'tier1_example',
        query: 'What is the carrier mobility of CVD-grown MoS₂ at 750°C?',
        tier: 1,
        tier_name: 'Direct Causal Path Reasoning',
        tier_color: '#1E88E5',
        confidence: 0.90,
        confidence_label: 'HIGH',
        explanation: 'Complete PSP chain found in the knowledge graph: CVD temperature 750°C → crystallinity → carrier mobility. All evidence is verified and causally connected.',
        entities: ['CVD temperature 750°C', 'MoS₂', 'carrier mobility'],
        kg_paths: [
          {
            source: 'CVD temperature 750°C',
            intermediate: 'crystallinity',
            target: 'carrier mobility',
            path_type: 'P→S→P',
            edge1_confidence: 0.90,
            edge2_confidence: 0.92,
            path_confidence: 0.90,
            evidence1: 'CVD growth at 750°C on SiO₂ substrate yields large-grain MoS₂ with improved crystallinity.',
            evidence2: 'Improved crystallinity reduces charged impurity scattering, leading to carrier mobility exceeding 40 cm²/Vs.',
          },
        ],
        naive_kg_result: {
          confidence: 0.76,
          issue: 'Naive KG retrieves all MoS₂ edges (including P→P shortcuts like “CVD 750°C increases carrier mobility”), over-anchoring on partial evidence without mechanistic explanation.',
        },
        baseline_result: {
          confidence: 0.65,
          answer: 'CVD-grown MoS₂ typically achieves carrier mobility of 10-40 cm²/Vs depending on growth conditions.',
        },
      },
      {
        id: 'tier2_example',
        query: 'Predict the bandgap of MoSe₂ synthesized by CVD.',
        tier: 2,
        tier_name: 'Analogical Mechanism Transfer',
        tier_color: '#FFC107',
        confidence: 0.72,
        confidence_label: 'MEDIUM',
        explanation: 'No complete PSP chain for MoSe₂ in the KG. ARIA finds MoS₂ as a structural analog (same 2H hexagonal phase) and transfers the mechanistic reasoning with physical constraint validation.',
        entities: ['MoSe₂', 'CVD synthesis', 'bandgap'],
        kg_paths: [
          {
            source: 'CVD temperature 750°C (MoS₂ analog)',
            intermediate: 'crystallinity (transferred)',
            target: 'direct band gap (estimated ~1.5 eV)',
            path_type: 'P→S→P (analogical)',
            edge1_confidence: 0.85,
            edge2_confidence: 0.78,
            path_confidence: 0.72,
            evidence1: 'MoS₂ analog: CVD at 750°C improves crystallinity. Structural class preserved: MoSe₂ shares 2H hexagonal phase.',
            evidence2: 'Chalcogen substitution rule: S→Se reduces bandgap by ~15%. MoS₂ direct bandgap ~1.8 eV → MoSe₂ estimated ~1.5 eV.',
          },
        ],
        constraints_checked: [
          { name: 'Structural class preservation', result: '✓ MoSe₂ shares 2H hexagonal phase with MoS₂' },
          { name: 'Elemental substitution rule', result: '✓ S→Se substitution reduces bandgap by ~15%' },
          { name: 'Thermal stability window', result: '✓ CVD temperature range overlaps for both materials' },
        ],
        naive_kg_result: {
          confidence: 0.78,
          issue: 'Naive KG retrieves MoS₂ edges and concatenates them with the query, but cannot explain the S→Se substitution effect. Error: 12.9%.',
        },
        baseline_result: {
          confidence: 0.60,
          answer: 'MoSe₂ has a direct bandgap of approximately 1.5 eV in its monolayer form.',
        },
      },
      {
        id: 'tier3_example',
        query: 'Design a transparent conductor better than ITO for flexible electronics.',
        tier: 3,
        tier_name: 'Parametric Fallback',
        tier_color: '#9E9E9E',
        confidence: 0.52,
        confidence_label: 'LOW',
        explanation: 'The KG contains no complete PSP paths, analogical materials, or sufficient evidence for this inverse design task. ARIA honestly flags the output as speculative and relies solely on parametric knowledge.',
        entities: ['transparent conductor', 'ITO alternative', 'flexible electronics'],
        kg_paths: [],
        naive_kg_result: {
          confidence: 0.76,
          issue: 'Naive KG overconfidently retrieves partial ITO edges (processing conditions, some conductivity data) and presents them as evidence, despite the absence of a complete causal chain. Overconfidence: 0.76 vs. ARIA’s honest 0.52.',
        },
        baseline_result: {
          confidence: 0.55,
          answer: 'Candidates include doped ZnO, Ag nanowires, and graphene-based films, but specific synthesis conditions remain uncertain.',
        },
      },
    ];
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /** Reset the demo to its initial state. */
  reset() {
    this._cancelTimers();
    this.currentQuery = null;
    this.currentStep = -1;
    this.isRunning = false;
    this._render();
  }

  /** Run the routing animation for the given query index (0-based). */
  runQuery(index) {
    if (index < 0 || index >= this.queries.length) return;
    this._cancelTimers();
    this.currentQuery = this.queries[index];
    this.currentStep = -1;
    this.isRunning = true;

    // Populate input
    const input = this.container.querySelector('.tr-input-field');
    if (input) input.value = this.currentQuery.query;

    // Reset steps
    this._updateStepIndicators();

    // Animate through steps with delays
    const stepDelay = 1500; // ms between steps
    const startDelay = 600;

    this._scheduleTimeout(() => this._animateStep(1), startDelay);
    this._scheduleTimeout(() => this._animateStep(2), startDelay + stepDelay);
    this._scheduleTimeout(() => this._animateStep(3), startDelay + stepDelay * 2);
    this._scheduleTimeout(() => this._animateStep(4), startDelay + stepDelay * 3);
    this._scheduleTimeout(() => {
      this.isRunning = false;
      this._showResultPanel();
    }, startDelay + stepDelay * 3 + 800);
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  _render() {
    this.container.innerHTML = '';
    this.container.classList.add('tr-root');

    // Inject scoped styles
    this._injectStyles();

    const wrapper = this._el('div', 'tr-wrapper');

    // Left: step indicators
    wrapper.appendChild(this._buildStepIndicators());

    // Right: main content
    const main = this._el('div', 'tr-main');
    main.appendChild(this._buildInputArea());
    main.appendChild(this._buildStepContent());
    wrapper.appendChild(main);

    this.container.appendChild(wrapper);
  }

  // -- Styles (scoped under .tr-root) -----------------------------------------

  _injectStyles() {
    if (document.getElementById('tr-styles')) return;
    const style = document.createElement('style');
    style.id = 'tr-styles';
    style.textContent = `
.tr-root {
  --tr-tier1: #1E88E5;
  --tr-tier2: #FFC107;
  --tr-tier3: #9E9E9E;
  --tr-bg-dark: #0A1929;
  --tr-bg-card: #112240;
  --tr-bg-card-hover: #1A3050;
  --tr-border: #1D3557;
  --tr-text-primary: #E6F1FF;
  --tr-text-secondary: #8892B0;
  --tr-text-muted: #5A6A8A;
  --tr-accent: #64FFDA;
  --tr-success: #43A047;
  --tr-warning: #FFA000;
  --tr-processing: #1565C0;
  --tr-structure: #E65100;
  --tr-property: #2E7D32;

  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: var(--tr-text-primary);
  background: var(--tr-bg-dark);
  border-radius: 12px;
  overflow: hidden;
}

.tr-wrapper {
  display: flex;
  min-height: 520px;
}

/* ---- Step Indicators ---- */
.tr-steps {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px 32px 20px;
  min-width: 72px;
  gap: 0;
  position: relative;
}

.tr-step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
  z-index: 2;
}

.tr-step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  border: 2px solid var(--tr-border);
  background: var(--tr-bg-card);
  color: var(--tr-text-muted);
  transition: all 0.5s ease;
  position: relative;
}

.tr-step-circle.active {
  border-color: var(--tr-accent);
  color: var(--tr-accent);
  box-shadow: 0 0 12px rgba(100, 255, 218, 0.3);
  animation: tr-pulse 1.5s ease-in-out infinite;
}

.tr-step-circle.completed {
  border-color: var(--tr-success);
  background: var(--tr-success);
  color: #fff;
}

.tr-step-circle.completed::after {
  content: '\\2713';
  font-size: 16px;
}

.tr-step-label {
  font-size: 10px;
  color: var(--tr-text-muted);
  text-align: center;
  max-width: 56px;
  line-height: 1.2;
  transition: color 0.5s ease;
}

.tr-step-label.active {
  color: var(--tr-accent);
}

.tr-step-label.completed {
  color: var(--tr-success);
}

.tr-step-connector {
  width: 2px;
  height: 32px;
  background: var(--tr-border);
  transition: background 0.5s ease;
}

.tr-step-connector.completed {
  background: var(--tr-success);
}

@keyframes tr-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(100, 255, 218, 0.3); }
  50% { box-shadow: 0 0 24px rgba(100, 255, 218, 0.6); }
}

/* ---- Main Content ---- */
.tr-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px 28px 24px 12px;
  gap: 16px;
  min-width: 0;
}

/* ---- Input Area ---- */
.tr-input-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tr-input-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.tr-input-field {
  flex: 1;
  padding: 12px 16px;
  background: var(--tr-bg-card);
  border: 1px solid var(--tr-border);
  border-radius: 8px;
  color: var(--tr-text-primary);
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.tr-input-field:focus {
  border-color: var(--tr-accent);
  box-shadow: 0 0 0 3px rgba(100, 255, 218, 0.1);
}

.tr-input-field::placeholder {
  color: var(--tr-text-muted);
}

.tr-run-btn {
  padding: 12px 20px;
  background: linear-gradient(135deg, #1565C0, #1E88E5);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  white-space: nowrap;
}

.tr-run-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(30, 136, 229, 0.4);
}

.tr-run-btn:active {
  transform: translateY(0);
}

.tr-run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.tr-example-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tr-example-btn {
  padding: 6px 14px;
  background: var(--tr-bg-card);
  border: 1px solid var(--tr-border);
  border-radius: 20px;
  color: var(--tr-text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.tr-example-btn:hover {
  background: var(--tr-bg-card-hover);
  border-color: var(--tr-accent);
  color: var(--tr-text-primary);
}

.tr-example-btn.t1 { border-left: 3px solid var(--tr-tier1); }
.tr-example-btn.t2 { border-left: 3px solid var(--tr-tier2); }
.tr-example-btn.t3 { border-left: 3px solid var(--tr-tier3); }

/* ---- Step Content ---- */
.tr-step-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 280px;
}

.tr-step-panel {
  background: var(--tr-bg-card);
  border: 1px solid var(--tr-border);
  border-radius: 10px;
  padding: 16px 20px;
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.5s ease, transform 0.5s ease;
  pointer-events: none;
}

.tr-step-panel.visible {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.tr-step-panel-title {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--tr-accent);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tr-step-panel-title .tr-step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(100, 255, 218, 0.15);
  color: var(--tr-accent);
  font-size: 11px;
  font-weight: 700;
}

/* ---- Entity Highlights ---- */
.tr-entity-highlight {
  color: var(--tr-accent);
  font-weight: 700;
  border-bottom: 2px solid rgba(100, 255, 218, 0.4);
  padding: 0 2px;
}

/* ---- Mini Graph ---- */
.tr-graph-container {
  width: 300px;
  height: 200px;
  border-radius: 8px;
  overflow: hidden;
  margin-top: 6px;
}

.tr-graph-container svg {
  width: 100%;
  height: 100%;
}

.tr-node-label {
  font-size: 10px;
  fill: var(--tr-text-primary);
  pointer-events: none;
}

.tr-node-circle {
  stroke-width: 2;
}

.tr-edge-label {
  font-size: 9px;
  fill: var(--tr-text-secondary);
  pointer-events: none;
}

.tr-edge-line {
  stroke-width: 1.5;
}

.tr-edge-line.dashed {
  stroke-dasharray: 6 3;
}

.tr-analog-label {
  font-size: 9px;
  font-style: italic;
  fill: var(--tr-tier2);
}

/* ---- Completeness Bar ---- */
.tr-completeness-wrapper {
  margin-top: 6px;
}

.tr-completeness-bar-bg {
  width: 100%;
  height: 24px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.tr-completeness-bar-fill {
  height: 100%;
  border-radius: 12px;
  transition: width 1s ease-out;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  min-width: 40px;
}

.tr-completeness-bar-fill.green {
  background: linear-gradient(90deg, #2E7D32, #43A047);
}
.tr-completeness-bar-fill.amber {
  background: linear-gradient(90deg, #E65100, #FFA000);
}
.tr-completeness-bar-fill.grey {
  background: linear-gradient(90deg, #424242, #757575);
}

.tr-completeness-label {
  font-size: 12px;
  color: var(--tr-text-secondary);
  margin-top: 6px;
}

/* ---- Tier Badge ---- */
.tr-tier-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.tr-tier-badge.t1 {
  background: rgba(30, 136, 229, 0.15);
  border: 2px solid var(--tr-tier1);
  color: var(--tr-tier1);
  animation: tr-badge-pulse-t1 1.2s ease-in-out 3;
}

.tr-tier-badge.t2 {
  background: rgba(255, 193, 7, 0.15);
  border: 2px solid var(--tr-tier2);
  color: var(--tr-tier2);
  animation: tr-badge-pulse-t2 1.2s ease-in-out 3;
}

.tr-tier-badge.t3 {
  background: rgba(158, 158, 158, 0.15);
  border: 2px solid var(--tr-tier3);
  color: var(--tr-text-secondary);
  animation: tr-badge-pulse-t3 1.2s ease-in-out 3;
}

@keyframes tr-badge-pulse-t1 {
  0%, 100% { box-shadow: 0 0 0 0 rgba(30, 136, 229, 0.4); }
  50% { box-shadow: 0 0 20px 4px rgba(30, 136, 229, 0.3); }
}
@keyframes tr-badge-pulse-t2 {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.4); }
  50% { box-shadow: 0 0 20px 4px rgba(255, 193, 7, 0.3); }
}
@keyframes tr-badge-pulse-t3 {
  0%, 100% { box-shadow: 0 0 0 0 rgba(158, 158, 158, 0.4); }
  50% { box-shadow: 0 0 20px 4px rgba(158, 158, 158, 0.3); }
}

.tr-confidence-score {
  font-size: 28px;
  font-weight: 800;
}

.tr-confidence-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ---- Result Panel ---- */
.tr-result-panel {
  background: var(--tr-bg-card);
  border: 1px solid var(--tr-border);
  border-radius: 10px;
  padding: 20px;
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.tr-result-panel.visible {
  opacity: 1;
  transform: translateY(0);
}

.tr-result-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.tr-result-explanation {
  font-size: 14px;
  color: var(--tr-text-secondary);
  line-height: 1.65;
  margin-bottom: 16px;
}

.tr-result-section {
  margin-bottom: 14px;
}

.tr-result-section-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--tr-text-muted);
  margin-bottom: 8px;
}

/* PSP path */
.tr-psp-path {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.tr-psp-node {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.tr-psp-node.processing {
  background: rgba(21, 101, 192, 0.2);
  border: 1px solid var(--tr-processing);
  color: #90CAF9;
}

.tr-psp-node.structure {
  background: rgba(230, 81, 0, 0.2);
  border: 1px solid var(--tr-structure);
  color: #FFCC80;
}

.tr-psp-node.property {
  background: rgba(46, 125, 50, 0.2);
  border: 1px solid var(--tr-property);
  color: #A5D6A7;
}

.tr-psp-edge {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 4px;
  min-width: 50px;
}

.tr-psp-arrow {
  font-size: 14px;
  color: var(--tr-text-muted);
}

.tr-psp-edge-conf {
  font-size: 10px;
  color: var(--tr-text-muted);
}

.tr-psp-evidence {
  font-size: 11px;
  color: var(--tr-text-muted);
  margin-top: 2px;
  line-height: 1.4;
  max-width: 400px;
}

/* Constraints */
.tr-constraint-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tr-constraint-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: var(--tr-text-secondary);
}

.tr-constraint-icon.pass {
  color: var(--tr-success);
  font-weight: 700;
}

.tr-constraint-icon.fail {
  color: #EF5350;
  font-weight: 700;
}

.tr-disclaimer {
  font-size: 12px;
  color: var(--tr-tier2);
  background: rgba(255, 193, 7, 0.08);
  border: 1px solid rgba(255, 193, 7, 0.25);
  border-radius: 6px;
  padding: 8px 12px;
  margin-top: 10px;
}

.tr-speculative-notice {
  font-size: 12px;
  color: var(--tr-text-secondary);
  background: rgba(158, 158, 158, 0.08);
  border: 1px solid rgba(158, 158, 158, 0.25);
  border-radius: 6px;
  padding: 8px 12px;
  margin-top: 10px;
}

/* Comparison */
.tr-comparison {
  display: flex;
  gap: 16px;
  margin-top: 6px;
}

.tr-comparison-card {
  flex: 1;
  background: var(--tr-bg-dark);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--tr-border);
}

.tr-comparison-card.overconfident {
  border-top: 3px solid #EF5350;
}

.tr-comparison-card.calibrated {
  border-top: 3px solid var(--tr-success);
}

.tr-comparison-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}

.tr-comparison-card.overconfident .tr-comparison-label {
  color: #EF5350;
}

.tr-comparison-card.calibrated .tr-comparison-label {
  color: var(--tr-success);
}

.tr-comparison-conf {
  font-size: 22px;
  font-weight: 800;
}

.tr-comparison-issue {
  font-size: 11px;
  color: var(--tr-text-muted);
  line-height: 1.5;
  margin-top: 4px;
}

/* ---- Animations ---- */
.tr-fade-in {
  animation: trFadeIn 0.5s ease forwards;
}

@keyframes trFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.tr-typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--tr-accent);
  margin-left: 2px;
  animation: trBlink 1s step-end infinite;
}

@keyframes trBlink {
  50% { opacity: 0; }
}
    `;
    document.head.appendChild(style);
  }

  // -- Step Indicators --------------------------------------------------------

  _buildStepIndicators() {
    const col = this._el('div', 'tr-steps');
    this.stepDefs.forEach((s, i) => {
      if (i > 0) {
        const conn = this._el('div', 'tr-step-connector');
        conn.dataset.step = i;
        col.appendChild(conn);
      }
      const ind = this._el('div', 'tr-step-indicator');
      const circle = this._el('div', 'tr-step-circle');
      circle.textContent = s.num;
      circle.dataset.step = s.num;
      const label = this._el('div', 'tr-step-label');
      label.textContent = s.label;
      label.dataset.step = s.num;
      ind.appendChild(circle);
      ind.appendChild(label);
      col.appendChild(ind);
    });
    return col;
  }

  _updateStepIndicators() {
    const circles = this.container.querySelectorAll('.tr-step-circle');
    const labels = this.container.querySelectorAll('.tr-step-label');
    const connectors = this.container.querySelectorAll('.tr-step-connector');

    circles.forEach((c) => {
      const step = parseInt(c.dataset.step, 10);
      c.classList.remove('active', 'completed');
      if (step < this.currentStep) c.classList.add('completed');
      else if (step === this.currentStep) c.classList.add('active');
    });

    labels.forEach((l) => {
      const step = parseInt(l.dataset.step, 10);
      l.classList.remove('active', 'completed');
      if (step < this.currentStep) l.classList.add('completed');
      else if (step === this.currentStep) l.classList.add('active');
    });

    connectors.forEach((c) => {
      const step = parseInt(c.dataset.step, 10);
      c.classList.remove('completed');
      if (step < this.currentStep) c.classList.add('completed');
    });
  }

  // -- Input Area -------------------------------------------------------------

  _buildInputArea() {
    const area = this._el('div', 'tr-input-area');

    const row = this._el('div', 'tr-input-row');
    const input = this._el('input', 'tr-input-field');
    input.type = 'text';
    input.placeholder = 'Enter a materials science query…';
    input.setAttribute('aria-label', 'Materials science query input');
    row.appendChild(input);

    const btn = this._el('button', 'tr-run-btn');
    btn.textContent = 'Route Query';
    btn.addEventListener('click', () => {
      const val = input.value.trim();
      if (!val) return;
      // Find matching example
      const idx = this.queries.findIndex((q) => q.query === val);
      if (idx >= 0) {
        this.runQuery(idx);
      } else {
        // Default to tier 3 for unknown queries
        this._runCustomQuery(val);
      }
    });
    row.appendChild(btn);
    area.appendChild(row);

    const btns = this._el('div', 'tr-example-btns');
    const labels = [
      { text: 'MoS₂ conductivity (Tier 1)', cls: 't1', idx: 0 },
      { text: 'MoSe₂ bandgap (Tier 2)', cls: 't2', idx: 1 },
      { text: 'ITO alternative (Tier 3)', cls: 't3', idx: 2 },
    ];
    labels.forEach(({ text, cls, idx }) => {
      const b = this._el('button', `tr-example-btn ${cls}`);
      b.textContent = text;
      b.addEventListener('click', () => this.runQuery(idx));
      btns.appendChild(b);
    });
    area.appendChild(btns);

    return area;
  }

  // -- Step Content -----------------------------------------------------------

  _buildStepContent() {
    const content = this._el('div', 'tr-step-content');
    // 4 placeholder panels
    for (let i = 1; i <= 4; i++) {
      const panel = this._el('div', 'tr-step-panel');
      panel.dataset.step = i;
      content.appendChild(panel);
    }
    // Result panel
    const result = this._el('div', 'tr-result-panel');
    result.dataset.step = 'result';
    content.appendChild(result);
    return content;
  }

  // ---------------------------------------------------------------------------
  // Step Animations
  // ---------------------------------------------------------------------------

  _animateStep(step) {
    this.currentStep = step;
    this._updateStepIndicators();

    const panel = this.container.querySelector(`.tr-step-panel[data-step="${step}"]`);
    if (!panel) return;

    panel.innerHTML = '';
    panel.classList.add('visible');

    switch (step) {
      case 1: this._renderStep1(panel); break;
      case 2: this._renderStep2(panel); break;
      case 3: this._renderStep3(panel); break;
      case 4: this._renderStep4(panel); break;
    }
  }

  // -- Step 1: Entity Extraction ----------------------------------------------

  _renderStep1(panel) {
    const q = this.currentQuery;
    const title = this._el('div', 'tr-step-panel-title');
    title.innerHTML = '<span class="tr-step-num">1</span> Entity Extraction';
    panel.appendChild(title);

    const body = this._el('div');
    let html = q.query;

    // Highlight entities in reverse length order to avoid overlapping spans
    const sortedEntities = [...q.entities].sort((a, b) => b.length - a.length);
    sortedEntities.forEach((entity) => {
      const escaped = entity.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      html = html.replace(
        new RegExp(escaped, 'g'),
        `<span class="tr-entity-highlight">${entity}</span>`,
      );
    });

    const queryDisplay = this._el('div');
    queryDisplay.style.cssText =
      'font-size:15px;line-height:1.7;padding:12px 16px;background:rgba(100,255,218,0.04);border-radius:8px;border:1px solid rgba(100,255,218,0.12);';
    queryDisplay.innerHTML = html;
    body.appendChild(queryDisplay);

    const extractedLabel = this._el('div');
    extractedLabel.style.cssText = 'margin-top:8px;font-size:12px;color:var(--tr-text-muted);';
    extractedLabel.textContent = `Extracted ${q.entities.length} entities: ${q.entities.join(', ')}`;
    body.appendChild(extractedLabel);

    panel.appendChild(body);
  }

  // -- Step 2: KG Matching ----------------------------------------------------

  _renderStep2(panel) {
    const q = this.currentQuery;
    const title = this._el('div', 'tr-step-panel-title');
    title.innerHTML = '<span class="tr-step-num">2</span> KG Matching';
    panel.appendChild(title);

    if (q.kg_paths.length === 0) {
      const noPath = this._el('div');
      noPath.style.cssText = 'font-size:14px;color:var(--tr-text-muted);padding:8px 0;';
      noPath.textContent = 'No matching PSP paths found in the knowledge graph.';
      panel.appendChild(noPath);
      return;
    }

    const path = q.kg_paths[0];
    const graphContainer = this._el('div', 'tr-graph-container');
    panel.appendChild(graphContainer);

    // Build mini graph after paint
    this._scheduleTimeout(() => this._drawMiniGraph(graphContainer, q), 50);
  }

  _drawMiniGraph(container, query) {
    const width = 300;
    const height = 200;
    const path = query.kg_paths[0];
    const isAnalogical = path.path_type && path.path_type.includes('analogical');

    const svg = d3
      .select(container)
      .append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

    // Background
    svg
      .append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', '#0A1929')
      .attr('rx', 8);

    // Node data
    const nodes = [
      { id: 'source', label: this._shortenLabel(path.source), layer: 'P', x: 40, y: 100 },
      { id: 'intermediate', label: this._shortenLabel(path.intermediate), layer: 'S', x: 150, y: 100 },
      { id: 'target', label: this._shortenLabel(path.target), layer: 'P', x: 260, y: 100 },
    ];

    const layerColors = { P: '#1565C0', S: '#E65100', X: '#2E7D32' };
    // Property nodes also get green
    if (path.path_type && path.path_type.includes('S→P')) {
      nodes[2].layer = 'X'; // Property output node
    }

    // Analogical source (dashed)
    if (isAnalogical) {
      nodes.push({
        id: 'analog',
        label: 'MoS₂ (analog)',
        layer: 'P',
        x: 150,
        y: 30,
      });
    }

    // Edges
    const edges = [
      {
        source: 'source',
        target: 'intermediate',
        confidence: path.edge1_confidence,
        evidence: path.evidence1,
      },
      {
        source: 'intermediate',
        target: 'target',
        confidence: path.edge2_confidence,
        evidence: path.evidence2,
      },
    ];

    if (isAnalogical) {
      edges.push({
        source: 'analog',
        target: 'source',
        confidence: null,
        dashed: true,
      });
    }

    // Draw edges
    const nodeMap = {};
    nodes.forEach((n) => (nodeMap[n.id] = n));

    edges.forEach((e) => {
      const s = nodeMap[e.source];
      const t = nodeMap[e.target];
      const line = svg
        .append('line')
        .attr('class', e.dashed ? 'tr-edge-line dashed' : 'tr-edge-line')
        .attr('x1', s.x)
        .attr('y1', s.y)
        .attr('x2', t.x)
        .attr('y2', t.y)
        .attr('stroke', e.dashed ? '#FFC107' : '#5A6A8A')
        .attr('stroke-opacity', 0);

      // Animate edge
      line
        .transition()
        .duration(500)
        .attr('stroke-opacity', 0.8);

      // Confidence label
      if (e.confidence !== null) {
        const midX = (s.x + t.x) / 2;
        const midY = (s.y + t.y) / 2 + 14;
        svg
          .append('text')
          .attr('class', 'tr-edge-label')
          .attr('x', midX)
          .attr('y', midY)
          .attr('text-anchor', 'middle')
          .attr('opacity', 0)
          .text(`${(e.confidence * 100).toFixed(0)}%`)
          .transition()
          .delay(400)
          .duration(300)
          .attr('opacity', 1);
      }
    });

    // Draw nodes (on top of edges)
    nodes.forEach((n, i) => {
      const color = layerColors[n.layer] || '#1565C0';
      const g = svg.append('g');

      // Circle
      g.append('circle')
        .attr('cx', n.x)
        .attr('cy', n.y)
        .attr('r', 0)
        .attr('fill', color)
        .attr('fill-opacity', 0.25)
        .attr('stroke', color)
        .attr('stroke-width', 2)
        .attr('class', 'tr-node-circle')
        .transition()
        .delay(i * 200)
        .duration(400)
        .attr('r', 16);

      // Label
      g.append('text')
        .attr('class', 'tr-node-label')
        .attr('x', n.x)
        .attr('y', n.y + 28)
        .attr('text-anchor', 'middle')
        .attr('opacity', 0)
        .text(n.label)
        .transition()
        .delay(i * 200 + 300)
        .duration(300)
        .attr('opacity', 1);
    });

    // Analogical label
    if (isAnalogical) {
      svg
        .append('text')
        .attr('class', 'tr-analog-label')
        .attr('x', 150)
        .attr('y', 16)
        .attr('text-anchor', 'middle')
        .attr('opacity', 0)
        .text('Analogical transfer')
        .transition()
        .delay(800)
        .duration(300)
        .attr('opacity', 1);
    }

    // Path type label
    svg
      .append('text')
      .attr('x', width / 2)
      .attr('y', height - 12)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#5A6A8A')
      .attr('opacity', 0)
      .text(`Path type: ${path.path_type}`)
      .transition()
      .delay(800)
      .duration(300)
      .attr('opacity', 1);
  }

  _shortenLabel(label) {
    if (!label) return '?';
    if (label.length > 22) return label.slice(0, 20) + '…';
    return label;
  }

  // -- Step 3: PSP Completeness -----------------------------------------------

  _renderStep3(panel) {
    const q = this.currentQuery;
    const title = this._el('div', 'tr-step-panel-title');
    title.innerHTML = '<span class="tr-step-num">3</span> PSP Completeness Check';
    panel.appendChild(title);

    const wrapper = this._el('div', 'tr-completeness-wrapper');

    // Calculate completeness
    let completeness = 0;
    let barClass = 'grey';
    let statusText = 'Insufficient';

    if (q.tier === 1) {
      completeness = q.confidence;
      barClass = 'green';
      statusText = 'Complete PSP chain found';
    } else if (q.tier === 2) {
      completeness = q.confidence;
      barClass = 'amber';
      statusText = 'Partial — analogical transfer applied';
    } else {
      completeness = q.confidence;
      barClass = 'grey';
      statusText = 'Insufficient — no causal chain available';
    }

    // Bar background
    const barBg = this._el('div', 'tr-completeness-bar-bg');
    const barFill = this._el('div', `tr-completeness-bar-fill ${barClass}`);
    barFill.style.width = '0%';
    barFill.textContent = `${(completeness * 100).toFixed(0)}%`;
    barBg.appendChild(barFill);
    wrapper.appendChild(barBg);

    const label = this._el('div', 'tr-completeness-label');
    label.textContent = statusText;
    wrapper.appendChild(label);

    // Detailed info
    if (q.tier === 1 || q.tier === 2) {
      const detail = this._el('div');
      detail.style.cssText = 'margin-top:8px;font-size:12px;color:var(--tr-text-muted);';
      detail.innerHTML = `Completeness score: <strong style="color:var(--tr-text-primary)">${(completeness * 100).toFixed(0)}%</strong> &mdash; ${q.confidence_label} confidence`;
      wrapper.appendChild(detail);
    }

    panel.appendChild(wrapper);

    // Animate bar fill after paint
    this._scheduleTimeout(() => {
      barFill.style.width = `${completeness * 100}%`;
    }, 100);
  }

  // -- Step 4: Tier Activation -------------------------------------------------

  _renderStep4(panel) {
    const q = this.currentQuery;
    const tierClass = `t${q.tier}`;
    const tierColors = { 1: this.colors.tier1, 2: this.colors.tier2, 3: this.colors.tier3 };

    const title = this._el('div', 'tr-step-panel-title');
    title.innerHTML = '<span class="tr-step-num">4</span> Tier Activation';
    panel.appendChild(title);

    const row = this._el('div');
    row.style.cssText = 'display:flex;align-items:center;gap:20px;flex-wrap:wrap;';

    // Tier badge
    const badge = this._el('span', `tr-tier-badge ${tierClass}`);
    badge.innerHTML = `Tier ${q.tier}: ${q.tier_name}`;
    row.appendChild(badge);

    // Confidence score
    const confWrap = this._el('div');
    confWrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;';

    const confScore = this._el('div', 'tr-confidence-score');
    confScore.style.color = tierColors[q.tier];
    confScore.textContent = `${(q.confidence * 100).toFixed(0)}%`;
    confWrap.appendChild(confScore);

    const confLabel = this._el('div', 'tr-confidence-label');
    confLabel.style.color = tierColors[q.tier];
    confLabel.textContent = q.confidence_label;
    confWrap.appendChild(confLabel);

    row.appendChild(confWrap);

    panel.appendChild(row);

    // Explanation
    const explanation = this._el('div');
    explanation.style.cssText = 'margin-top:10px;font-size:13px;color:var(--tr-text-secondary);line-height:1.6;';
    explanation.textContent = q.explanation;
    panel.appendChild(explanation);
  }

  // -- Result Panel -----------------------------------------------------------

  _showResultPanel() {
    const panel = this.container.querySelector('.tr-result-panel[data-step="result"]');
    if (!panel) return;

    const q = this.currentQuery;
    const tierClass = `t${q.tier}`;
    const tierColors = { 1: this.colors.tier1, 2: this.colors.tier2, 3: this.colors.tier3 };

    panel.innerHTML = '';

    // Header
    const header = this._el('div', 'tr-result-header');

    const badge = this._el('span', `tr-tier-badge ${tierClass}`);
    badge.innerHTML = `Tier ${q.tier}`;
    header.appendChild(badge);

    const confWrap = this._el('div');
    confWrap.style.cssText = 'display:flex;flex-direction:column;';
    const confScore = this._el('span', 'tr-confidence-score');
    confScore.style.color = tierColors[q.tier];
    confScore.style.fontSize = '20px';
    confScore.textContent = `${(q.confidence * 100).toFixed(0)}%`;
    confWrap.appendChild(confScore);
    const confLabel = this._el('span', 'tr-confidence-label');
    confLabel.style.color = tierColors[q.tier];
    confLabel.textContent = q.confidence_label;
    confWrap.appendChild(confLabel);
    header.appendChild(confWrap);

    panel.appendChild(header);

    // Explanation
    const explanation = this._el('div', 'tr-result-explanation');
    explanation.textContent = q.explanation;
    panel.appendChild(explanation);

    // Tier-specific content
    if (q.tier === 1) {
      panel.appendChild(this._buildTier1Details(q));
    } else if (q.tier === 2) {
      panel.appendChild(this._buildTier2Details(q));
    } else {
      panel.appendChild(this._buildTier3Details(q));
    }

    // Comparison
    panel.appendChild(this._buildComparison(q));

    panel.classList.add('visible');
  }

  // -- Tier 1 Details: PSP Path -----------------------------------------------

  _buildTier1Details(q) {
    const section = this._el('div', 'tr-result-section');
    const title = this._el('div', 'tr-result-section-title');
    title.textContent = 'Causal PSP Path';
    section.appendChild(title);

    const path = q.kg_paths[0];
    if (!path) return section;

    const pathEl = this._el('div', 'tr-psp-path');

    // Source node (Processing)
    pathEl.appendChild(this._buildPSPNode(path.source, 'processing'));

    // Edge 1
    pathEl.appendChild(this._buildPSPEdge(path.edge1_confidence, path.evidence1));
    pathEl.appendChild(this._buildPSPEdgeArrow());

    // Intermediate node (Structure)
    pathEl.appendChild(this._buildPSPNode(path.intermediate, 'structure'));

    // Edge 2
    pathEl.appendChild(this._buildPSPEdge(path.edge2_confidence, path.evidence2));
    pathEl.appendChild(this._buildPSPEdgeArrow());

    // Target node (Property)
    pathEl.appendChild(this._buildPSPNode(path.target, 'property'));

    section.appendChild(pathEl);
    return section;
  }

  _buildPSPNode(label, type) {
    const node = this._el('span', `tr-psp-node ${type}`);
    node.textContent = label;
    return node;
  }

  _buildPSPEdge(confidence, evidence) {
    const edge = this._el('div', 'tr-psp-edge');
    const conf = this._el('div', 'tr-psp-edge-conf');
    conf.textContent = confidence ? `${(confidence * 100).toFixed(0)}%` : '';
    edge.appendChild(conf);
    if (evidence) {
      const ev = this._el('div', 'tr-psp-evidence');
      ev.textContent = evidence;
      edge.appendChild(ev);
    }
    return edge;
  }

  _buildPSPEdgeArrow() {
    const arrow = this._el('span', 'tr-psp-arrow');
    arrow.textContent = '→';
    return arrow;
  }

  // -- Tier 2 Details: Analogical Transfer ------------------------------------

  _buildTier2Details(q) {
    const section = this._el('div', 'tr-result-section');
    const title = this._el('div', 'tr-result-section-title');
    title.textContent = 'Analogical Transfer & Constraint Checks';
    section.appendChild(title);

    // Constraints
    if (q.constraints_checked && q.constraints_checked.length > 0) {
      const list = this._el('ul', 'tr-constraint-list');
      q.constraints_checked.forEach((c) => {
        const item = this._el('li', 'tr-constraint-item');
        const isPass = c.result.startsWith('✓') || c.result.startsWith('✔');
        const icon = this._el('span', `tr-constraint-icon ${isPass ? 'pass' : 'fail'}`);
        icon.textContent = isPass ? '✓' : '✗';
        item.appendChild(icon);
        const text = this._el('span');
        text.textContent = `${c.name}: ${c.result}`;
        item.appendChild(text);
        list.appendChild(item);
      });
      section.appendChild(list);
    }

    // Disclaimer
    const disclaimer = this._el('div', 'tr-disclaimer');
    disclaimer.innerHTML =
      '<strong>Analogical Disclaimer:</strong> This prediction is derived by transferring mechanistic reasoning from a structurally similar material (MoS₂). Results should be validated experimentally.';
    section.appendChild(disclaimer);

    // Analogical path
    if (q.kg_paths.length > 0) {
      const path = q.kg_paths[0];
      const pathSection = this._el('div', 'tr-result-section');
      const pathTitle = this._el('div', 'tr-result-section-title');
      pathTitle.textContent = 'Transferred PSP Path';
      pathSection.appendChild(pathTitle);

      const pathEl = this._el('div', 'tr-psp-path');
      pathEl.appendChild(this._buildPSPNode(path.source, 'processing'));
      pathEl.appendChild(this._buildPSPEdge(path.edge1_confidence, path.evidence1));
      pathEl.appendChild(this._buildPSPEdgeArrow());
      pathEl.appendChild(this._buildPSPNode(path.intermediate, 'structure'));
      pathEl.appendChild(this._buildPSPEdge(path.edge2_confidence, path.evidence2));
      pathEl.appendChild(this._buildPSPEdgeArrow());
      pathEl.appendChild(this._buildPSPNode(path.target, 'property'));

      pathSection.appendChild(pathEl);
      section.appendChild(pathSection);
    }

    return section;
  }

  // -- Tier 3 Details: Speculative Notice --------------------------------------

  _buildTier3Details(q) {
    const section = this._el('div', 'tr-result-section');

    const title = this._el('div', 'tr-result-section-title');
    title.textContent = 'Uncertainty Assessment';
    section.appendChild(title);

    const flag = this._el('div');
    flag.style.cssText =
      'display:flex;align-items:center;gap:8px;font-size:14px;color:#EF5350;margin-bottom:8px;';
    flag.innerHTML = '<span style="font-size:18px">⚠</span> <strong>High Uncertainty</strong> — No causal evidence available';
    section.appendChild(flag);

    const notice = this._el('div', 'tr-speculative-notice');
    notice.innerHTML =
      '<strong>Speculative Output Notice:</strong> This answer is produced without knowledge-graph support. The reasoning relies entirely on parametric knowledge with no causal chain to anchor the prediction. Treat all outputs as hypotheses requiring experimental validation.';
    section.appendChild(notice);

    return section;
  }

  // -- Comparison (Naive KG vs ARIA) ------------------------------------------

  _buildComparison(q) {
    const section = this._el('div', 'tr-result-section');
    const title = this._el('div', 'tr-result-section-title');
    title.textContent = 'Confidence Calibration: Naive KG vs. ARIA';
    section.appendChild(title);

    const comp = this._el('div', 'tr-comparison');

    // Naive KG card
    const naive = this._el('div', 'tr-comparison-card overconfident');
    const naiveLabel = this._el('div', 'tr-comparison-label');
    naiveLabel.textContent = 'Naive KG (Overconfident)';
    naive.appendChild(naiveLabel);
    const naiveConf = this._el('div', 'tr-comparison-conf');
    naiveConf.style.color = '#EF5350';
    naiveConf.textContent = `${(q.naive_kg_result.confidence * 100).toFixed(0)}%`;
    naive.appendChild(naiveConf);
    const naiveIssue = this._el('div', 'tr-comparison-issue');
    naiveIssue.textContent = q.naive_kg_result.issue;
    naive.appendChild(naiveIssue);
    comp.appendChild(naive);

    // ARIA card
    const aria = this._el('div', 'tr-comparison-card calibrated');
    const ariaLabel = this._el('div', 'tr-comparison-label');
    ariaLabel.textContent = 'ARIA (Calibrated)';
    aria.appendChild(ariaLabel);
    const ariaConf = this._el('div', 'tr-comparison-conf');
    ariaConf.style.color = '#43A047';
    ariaConf.textContent = `${(q.confidence * 100).toFixed(0)}%`;
    aria.appendChild(ariaConf);
    const ariaIssue = this._el('div', 'tr-comparison-issue');
    if (q.tier === 1) {
      ariaIssue.textContent = 'Complete causal chain with mechanistic explanation. Confidence grounded in verified evidence.';
    } else if (q.tier === 2) {
      ariaIssue.textContent = 'Analogical transfer with constraint validation. Confidence reflects structural similarity and physical plausibility.';
    } else {
      ariaIssue.textContent = 'Honest assessment: no causal evidence. Confidence reflects true uncertainty rather than false precision.';
    }
    aria.appendChild(ariaIssue);
    comp.appendChild(aria);

    section.appendChild(comp);
    return section;
  }

  // -- Custom query handler (falls back to Tier 3 behavior) -------------------

  _runCustomQuery(queryText) {
    this._cancelTimers();
    this.currentQuery = {
      id: 'custom',
      query: queryText,
      tier: 3,
      tier_name: 'Parametric Fallback',
      tier_color: '#9E9E9E',
      confidence: 0.45,
      confidence_label: 'LOW',
      explanation: `No complete PSP paths, analogical materials, or sufficient evidence found for this query. ARIA honestly flags the output as speculative.`,
      entities: this._extractEntities(queryText),
      kg_paths: [],
      naive_kg_result: {
        confidence: 0.72,
        issue: 'Naive KG would retrieve loosely related edges and present them as supporting evidence, despite lacking a coherent causal chain.',
      },
      baseline_result: {
        confidence: 0.50,
        answer: 'Insufficient evidence for a reliable prediction.',
      },
    };
    this.currentStep = -1;
    this.isRunning = true;

    const input = this.container.querySelector('.tr-input-field');
    if (input) input.value = queryText;

    this._updateStepIndicators();

    const stepDelay = 1500;
    const startDelay = 600;
    this._scheduleTimeout(() => this._animateStep(1), startDelay);
    this._scheduleTimeout(() => this._animateStep(2), startDelay + stepDelay);
    this._scheduleTimeout(() => this._animateStep(3), startDelay + stepDelay * 2);
    this._scheduleTimeout(() => this._animateStep(4), startDelay + stepDelay * 3);
    this._scheduleTimeout(() => {
      this.isRunning = false;
      this._showResultPanel();
    }, startDelay + stepDelay * 3 + 800);
  }

  _extractEntities(text) {
    // Simple heuristic entity extraction for custom queries
    const entities = [];
    const patterns = [
      new RegExp('\\b(MoS[\\u2082\\u00B2]|MoSe[\\u2082\\u00B2]|WS[\\u2082\\u00B2]|WSe[\\u2082\\u00B2]|graphene|h-BN|ITO)\\b', 'gi'),
      new RegExp('\\b(CVD|MBE|PLD|sputtering|annealing|doping|synthesis|growth)\\b', 'gi'),
      new RegExp('\\b(mobility|conductivity|bandgap|band gap|on/off ratio|carrier density|thermal conductivity)\\b', 'gi'),
    ];
    patterns.forEach((p) => {
      let m;
      while ((m = p.exec(text)) !== null) {
        if (!entities.includes(m[0])) entities.push(m[0]);
      }
    });
    if (entities.length === 0) {
      // Fallback: use first 3 words
      entities.push(text.split(/\s+/).slice(0, 3).join(' '));
    }
    return entities.slice(0, 4);
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  _el(tag, cls) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    return el;
  }

  _scheduleTimeout(fn, delay) {
    const id = setTimeout(fn, delay);
    this.animationTimers.push(id);
  }

  _cancelTimers() {
    this.animationTimers.forEach((id) => clearTimeout(id));
    this.animationTimers = [];
  }
}

// Make globally available
if (typeof window !== 'undefined') {
  window.TierRouter = TierRouter;
}
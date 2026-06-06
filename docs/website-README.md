# ARIA Interactive Website

This is the Distill.pub-style interactive website for the ARIA paper (KDD 2026).

## Local Development

```bash
# Serve locally with Python
python3 -m http.server 8000

# Or with Node.js
npx serve .
```

Then open http://localhost:8000 in your browser.

## Structure

```
index.html                  ← Main single-page article
assets/
├── css/
│   └── aria.css            ← Custom ARIA theme (colors, fonts, layout)
├── js/
│   ├── main.js             ← Init, scroll observers, navigation
│   ├── kg-explorer.js      ← D3 force-directed KG visualization
│   ├── tier-router.js      ← Interactive 3-tier cascade demo
│   ├── psp-cascade.js      ← Animated PSP hierarchy
│   ├── tunneling-demo.js   ← Side-by-side contextual tunneling comparison
│   ├── results-chart.js    ← D3 comparative results charts
│   └── robustness-slider.js ← Edge-deletion robustness interactive
├── data/
│   ├── aria_2d_kg_demo.json ← Demo KG data (28 relationships)
│   ├── benchmark_results.json ← Pre-computed results for charts
│   └── example_queries.json  ← Pre-loaded example queries for tier router
└── figures/
    ├── ARIA-logo.svg
    ├── KDD-Fig1.svg
    ├── KDD_Fig3-KG-workflow.svg
    └── KDD_Fig4.svg
```

## Interactive Features

1. **Contextual Tunneling Demo** (§1) — Side-by-side comparison of Baseline LLM vs Naive KG+LLM
2. **PSP Hierarchy** (§2) — Animated Processing-Structure-Property cascade visualization
3. **Tier Router** (§3) — Interactive query routing through the 3-tier cascade
4. **KG Explorer** (§4) — D3 force-directed graph of the demo knowledge graph
5. **Results Charts** (§6) — D3 bar charts with toggle between forward/inverse/overall
6. **Robustness Slider** (§7) — Interactive edge-deletion robustness visualization

## Technology

- Pure HTML/CSS/JS — no build step required
- D3.js v7 for interactive visualizations
- KaTeX for math rendering
- IntersectionObserver for scroll-triggered animations
- Responsive design for mobile/tablet/desktop

## Deployment

This site is deployed via GitHub Pages from the `gh-pages` branch.
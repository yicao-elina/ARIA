/**
 * ARIA Knowledge Graph Explorer
 * D3.js v7 interactive force-directed graph for PSP (Processing-Structure-Property) relationships.
 *
 * Usage:
 *   const explorer = new KGExplorer('#graph-container');
 *   explorer.init();
 *
 * Data format expected from ../data/aria_2d_kg_demo.json:
 *   { nodes: [...], edges: [...] }
 *   Each edge: { source, target, relation, psp_type, material, confidence, evidence_text, relationship_id }
 *   psp_type: "Processing_to_Structure" | "Structure_to_Property" | "Processing_to_Property"
 */

;(function (global) {
  'use strict';

  // ─── Constants ────────────────────────────────────────────────────────────
  const PSP_LAYERS = {
    Processing: { color: '#1E88E5', label: 'Processing (P)' },
    Structure:  { color: '#FFC107', label: 'Structure (S)' },
    Property:   { color: '#4CAF50', label: 'Property (P\')' }
  };

  const EDGE_TYPES = {
    Processing_to_Structure: { color: '#1E88E5', dash: 'none',   label: 'P → S' },
    Structure_to_Property:   { color: '#4CAF50', dash: 'none',   label: 'S → P\'' },
    Processing_to_Property:  { color: '#E53935', dash: '6,3',    label: 'P → P\' shortcut' }
  };

  const MIN_NODE_RADIUS = 8;
  const MAX_NODE_RADIUS = 28;
  const DEFAULT_CONFIDENCE = 0.5;

  // ─── Helper: classify a node name into a PSP layer ────────────────────────
  // Heuristic: if the node only appears as a source in Processing_to_* edges
  // it is "Processing"; if it only appears as a target in Structure_to_Property
  // edges it is "Property"; otherwise it is "Structure".
  function classifyNode(nodeId, edges) {
    var types = new Set();
    edges.forEach(function (e) {
      if (e.source === nodeId || e.source === nodeId) {
        // nodeId is the source
        if (e.psp_type === 'Processing_to_Structure' || e.psp_type === 'Processing_to_Property') {
          if (e.source === nodeId) types.add('Processing');
        }
      }
      if (e.target === nodeId || e.target === nodeId) {
        if (e.psp_type === 'Structure_to_Property') {
          if (e.target === nodeId) types.add('Property');
        }
        if (e.psp_type === 'Processing_to_Structure') {
          if (e.target === nodeId) types.add('Structure');
        }
      }
    });
    // If still ambiguous, use keyword heuristics
    if (types.size === 0) {
      var id = nodeId.toLowerCase();
      if (/\btemp\b|\bheat\b|\bcvd\b|\bsynth|\bgrowth|\bdeposit|\bsputter|\bann(eal)/.test(id)) return 'Processing';
      if (/\bhardness|\bstiff|\bmodul|\bconduct|\bfrict|\bwear|\byoung|\bstrain|\bstress|\bcof\b|\bthick/.test(id)) return 'Property';
      return 'Structure';
    }
    if (types.size === 1) return types.values().next().value;
    // Prefer Structure if ambiguous between Processing and Structure
    if (types.has('Structure')) return 'Structure';
    return types.values().next().value;
  }

  // ─── KGExplorer Class ─────────────────────────────────────────────────────
  function KGExplorer(containerSelector) {
    this.containerSelector = containerSelector || '#kg-explorer';
    this.container = null;
    this.svg = null;
    this.simulation = null;
    this.rawData = null;
    this.nodes = [];
    this.edges = [];
    this.filteredNodes = [];
    this.filteredEdges = [];

    // Filter state
    this.filters = {
      material: 'all',
      layers: { Processing: true, Structure: true, Property: true },
      edgeTypes: { Processing_to_Structure: true, Structure_to_Property: true, Processing_to_Property: true },
      confidenceThreshold: 0.0
    };

    // Interaction state
    this.selectedNode = null;
    this.hoveredNode = null;
    this.hoveredEdge = null;

    // Dimensions
    this.width = 0;
    this.height = 0;

    // D3 selections (set during init)
    this.g = null;
    this.linkGroup = null;
    this.nodeGroup = null;
    this.labelGroup = null;
    this.zoomBehavior = null;
  }

  // ─── Initialization ────────────────────────────────────────────────────────
  KGExplorer.prototype.init = function () {
    this.container = d3.select(this.containerSelector);
    if (this.container.empty()) {
      console.error('[KGExplorer] Container not found:', this.containerSelector);
      return;
    }

    this._buildControls();
    this._buildDetailPanel();
    this._buildSVG();
    this._setupZoom();
    this._loadData();
    this._buildLegend();

    // Responsive resize
    var self = this;
    window.addEventListener('resize', function () {
      self._handleResize();
    });
  };

  // ─── Build filter controls above the graph ───────────────────────────────
  KGExplorer.prototype._buildControls = function () {
    var self = this;

    var controls = this.container.append('div')
      .attr('class', 'kg-controls')
      .style('display', 'flex')
      .style('flex-wrap', 'wrap')
      .style('gap', '16px')
      .style('padding', '10px 0')
      .style('align-items', 'flex-end')
      .style('font-family', '"Inter", "Segoe UI", system-ui, sans-serif')
      .style('font-size', '13px');

    // Material filter
    var matGroup = controls.append('div').style('display', 'flex').style('flex-direction', 'column').style('gap', '4px');
    matGroup.append('label').attr('class', 'kg-control-label').style('font-weight', '600').style('color', '#555').text('Material');
    var matSelect = matGroup.append('select')
      .attr('class', 'kg-filter-material')
      .style('padding', '4px 8px')
      .style('border-radius', '4px')
      .style('border', '1px solid #ccc')
      .style('font-size', '13px')
      .style('cursor', 'pointer');
    matSelect.append('option').attr('value', 'all').text('All Materials');
    matSelect.append('option').attr('value', 'MoS2').text('MoS₂');
    matSelect.append('option').attr('value', 'WS2').text('WS₂');
    matSelect.on('change', function () {
      self.filters.material = this.value;
      self._applyFilters();
    });

    // Layer filter (checkboxes)
    var layerGroup = controls.append('div').style('display', 'flex').style('flex-direction', 'column').style('gap', '4px');
    layerGroup.append('label').attr('class', 'kg-control-label').style('font-weight', '600').style('color', '#555').text('PSP Layers');
    var layerRow = layerGroup.append('div').style('display', 'flex').style('gap', '10px');

    Object.keys(PSP_LAYERS).forEach(function (layer) {
      var lbl = layerRow.append('label').style('display', 'flex').style('align-items', 'center').style('gap', '3px').style('cursor', 'pointer');
      lbl.append('input')
        .attr('type', 'checkbox')
        .attr('checked', true)
        .attr('class', 'kg-filter-layer')
        .attr('data-layer', layer)
        .style('cursor', 'pointer')
        .on('change', function () {
          self.filters.layers[layer] = this.checked;
          self._applyFilters();
        });
      lbl.append('span').style('color', PSP_LAYERS[layer].color).style('font-weight', '500').text(layer.charAt(0));
    });

    // Edge type filter (checkboxes)
    var edgeGroup = controls.append('div').style('display', 'flex').style('flex-direction', 'column').style('gap', '4px');
    edgeGroup.append('label').attr('class', 'kg-control-label').style('font-weight', '600').style('color', '#555').text('Edge Types');
    var edgeRow = edgeGroup.append('div').style('display', 'flex').style('gap', '10px');

    Object.keys(EDGE_TYPES).forEach(function (et) {
      var lbl = edgeRow.append('label').style('display', 'flex').style('align-items', 'center').style('gap', '3px').style('cursor', 'pointer');
      lbl.append('input')
        .attr('type', 'checkbox')
        .attr('checked', true)
        .attr('class', 'kg-filter-edge')
        .attr('data-edge-type', et)
        .style('cursor', 'pointer')
        .on('change', function () {
          self.filters.edgeTypes[et] = this.checked;
          self._applyFilters();
        });
      lbl.append('span').style('color', EDGE_TYPES[et].color).style('font-size', '12px').text(EDGE_TYPES[et].label);
    });

    // Confidence threshold slider
    var confGroup = controls.append('div').style('display', 'flex').style('flex-direction', 'column').style('gap', '4px');
    confGroup.append('label').attr('class', 'kg-control-label').style('font-weight', '600').style('color', '#555').text('Confidence ≥ ');
    var confRow = confGroup.append('div').style('display', 'flex').style('align-items', 'center').style('gap', '6px');
    var confSlider = confRow.append('input')
      .attr('type', 'range')
      .attr('min', 0)
      .attr('max', 1)
      .attr('step', 0.05)
      .attr('value', 0)
      .style('width', '100px')
      .style('cursor', 'pointer');
    var confLabel = confRow.append('span').attr('class', 'kg-conf-value').style('min-width', '30px').text('0.00');
    confSlider.on('input', function () {
      var val = parseFloat(this.value);
      self.filters.confidenceThreshold = val;
      confLabel.text(val.toFixed(2));
      self._applyFilters();
    });
  };

  // ─── Build detail panel (right side or below) ────────────────────────────
  KGExplorer.prototype._buildDetailPanel = function () {
    this.detailPanel = this.container.append('div')
      .attr('class', 'kg-detail-panel')
      .style('display', 'none')
      .style('position', 'absolute')
      .style('top', '10px')
      .style('right', '10px')
      .style('width', '280px')
      .style('max-height', '80%')
      .style('overflow-y', 'auto')
      .style('background', 'rgba(255,255,255,0.95)')
      .style('border-radius', '8px')
      .style('box-shadow', '0 2px 12px rgba(0,0,0,0.15)')
      .style('padding', '14px')
      .style('font-family', '"Inter", "Segoe UI", system-ui, sans-serif')
      .style('font-size', '13px')
      .style('z-index', '10');
  };

  // ─── Build the SVG canvas ────────────────────────────────────────────────
  KGExplorer.prototype._buildSVG = function () {
    var rect = this.container.node().getBoundingClientRect();
    this.width = rect.width;
    this.height = Math.max(rect.height - 60, 400); // leave room for controls + legend

    this.container.style('position', 'relative');

    this.svg = this.container.append('svg')
      .attr('class', 'kg-svg')
      .attr('width', this.width)
      .attr('height', this.height)
      .style('display', 'block')
      .style('border', '1px solid #e0e0e0')
      .style('border-radius', '6px')
      .style('background', '#fafbfc');

    // Arrow marker definitions
    var defs = this.svg.append('defs');

    Object.keys(EDGE_TYPES).forEach(function (key) {
      var et = EDGE_TYPES[key];
      defs.append('marker')
        .attr('id', 'arrow-' + key)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', et.color);
    });

    // Glow filter for PSP chain highlighting
    var glowFilter = defs.append('filter')
      .attr('id', 'kg-glow')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'coloredBlur');
    var feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Warning glow filter for P->P shortcuts
    var warnFilter = defs.append('filter')
      .attr('id', 'kg-warning-glow')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');
    warnFilter.append('feGaussianBlur')
      .attr('stdDeviation', '4')
      .attr('result', 'coloredBlur');
    var feMerge2 = warnFilter.append('feMerge');
    feMerge2.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge2.append('feMergeNode').attr('in', 'SourceGraphic');

    // Zoom group
    this.g = this.svg.append('g').attr('class', 'kg-zoom-group');

    // Link, node, label groups (rendered in order for z-index)
    this.linkGroup = this.g.append('g').attr('class', 'kg-links');
    this.nodeGroup = this.g.append('g').attr('class', 'kg-nodes');
    this.labelGroup = this.g.append('g').attr('class', 'kg-labels');

    // Tooltip div
    this.tooltip = this.container.append('div')
      .attr('class', 'kg-tooltip')
      .style('position', 'absolute')
      .style('display', 'none')
      .style('padding', '8px 12px')
      .style('background', 'rgba(33,33,33,0.92)')
      .style('color', '#fff')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('line-height', '1.5')
      .style('max-width', '300px')
      .style('pointer-events', 'none')
      .style('z-index', '20')
      .style('box-shadow', '0 2px 8px rgba(0,0,0,0.25)');
  };

  // ─── Zoom / pan ──────────────────────────────────────────────────────────
  KGExplorer.prototype._setupZoom = function () {
    var self = this;
    this.zoomBehavior = d3.zoom()
      .scaleExtent([0.2, 5])
      .on('zoom', function (event) {
        self.g.attr('transform', event.transform);
      });
    this.svg.call(this.zoomBehavior);
  };

  // ─── Load data ───────────────────────────────────────────────────────────
  KGExplorer.prototype._loadData = function () {
    var self = this;
    d3.json('../data/aria_2d_kg_demo.json').then(function (data) {
      self._processData(data);
      self._applyFilters();
    }).catch(function (err) {
      console.error('[KGExplorer] Failed to load data:', err);
      self.container.select('.kg-svg').append('text')
        .attr('x', '50%').attr('y', '50%')
        .attr('text-anchor', 'middle')
        .attr('fill', '#999')
        .style('font-size', '16px')
        .text('Failed to load knowledge graph data.');
    });
  };

  // ─── Process raw data into nodes/edges ────────────────────────────────────
  KGExplorer.prototype._processData = function (data) {
    var self = this;

    // Handle both { nodes, edges } and flat edge-list formats
    var rawEdges = data.edges || data.relationships || (Array.isArray(data) ? data : []);

    // Build node set from edges
    var nodeIdSet = new Set();
    rawEdges.forEach(function (e) {
      nodeIdSet.add(e.source);
      nodeIdSet.add(e.target);
    });

    // Create node objects
    this.nodes = Array.from(nodeIdSet).map(function (id) {
      var layer = classifyNode(id, rawEdges);
      return {
        id: id,
        layer: layer,
        // Degree will be computed after filtering
        degree: 0
      };
    });

    // Create node lookup
    var nodeMap = {};
    this.nodes.forEach(function (n) { nodeMap[n.id] = n; });

    // Create edge objects (store source/target as string IDs for D3 linking)
    this.edges = rawEdges.map(function (e, i) {
      return {
        id: e.relationship_id || ('edge-' + i),
        source: e.source,
        target: e.target,
        relation: e.relation || '',
        psp_type: e.psp_type,
        material: e.material || '',
        confidence: e.confidence != null ? e.confidence : DEFAULT_CONFIDENCE,
        evidence_text: e.evidence_text || '',
        original_source: e.source,
        original_target: e.target
      };
    });

    this.rawData = data;

    // Compute degree for each node
    this.nodes.forEach(function (n) {
      n.degree = self.edges.filter(function (e) {
        return e.source === n.id || e.target === n.id;
      }).length;
    });
  };

  // ─── Apply filters and re-render ────────────────────────────────────────
  KGExplorer.prototype._applyFilters = function () {
    var self = this;
    var f = this.filters;

    // Filter edges
    this.filteredEdges = this.edges.filter(function (e) {
      if (f.material !== 'all' && e.material !== f.material) return false;
      if (!f.edgeTypes[e.psp_type]) return false;
      if (e.confidence < f.confidenceThreshold) return false;
      return true;
    });

    // Build active node set from filtered edges
    var activeNodeIds = new Set();
    this.filteredEdges.forEach(function (e) {
      activeNodeIds.add(e.source);
      activeNodeIds.add(e.target);
    });

    // Filter nodes by layer and active participation
    this.filteredNodes = this.nodes.filter(function (n) {
      if (!f.layers[n.layer]) return false;
      if (!activeNodeIds.has(n.id)) return false;
      return true;
    });

    // Re-compute degree based on filtered edges
    this.filteredNodes.forEach(function (n) {
      n.filteredDegree = self.filteredEdges.filter(function (e) {
        return e.source === n.id || e.target === n.id;
      }).length;
    });

    this._render();
  };

  // ─── Render the graph ────────────────────────────────────────────────────
  KGExplorer.prototype._render = function () {
    this._buildSimulation();
    this._drawEdges();
    this._drawNodes();
    this._drawLabels();
    this._highlightPSPChains();
  };

  // ─── Force simulation ────────────────────────────────────────────────────
  KGExplorer.prototype._buildSimulation = function () {
    var self = this;
    var nodes = this.filteredNodes;
    var edges = this.filteredEdges;

    // Map string IDs to node objects for D3 links
    var nodeMap = {};
    nodes.forEach(function (n) { nodeMap[n.id] = n; });

    // Build link objects with node references for simulation
    var links = edges.map(function (e) {
      return {
        source: nodeMap[e.source] || e.source,
        target: nodeMap[e.target] || e.target,
        psp_type: e.psp_type,
        confidence: e.confidence,
        id: e.id,
        relation: e.relation,
        material: e.material,
        evidence_text: e.evidence_text,
        original_source: e.original_source,
        original_target: e.original_target
      };
    });

    // Store links for rendering
    this._simLinks = links;

    // Layer-based y positioning hints
    var layerY = { Processing: this.height * 0.2, Structure: this.height * 0.5, Property: this.height * 0.8 };
    nodes.forEach(function (n) {
      // Initialize positions if new
      if (n.x == null) {
        n.x = self.width / 2 + (Math.random() - 0.5) * 200;
        n.y = layerY[n.layer] + (Math.random() - 0.5) * 60;
      }
    });

    if (this.simulation) this.simulation.stop();

    this.simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(function (d) { return d.id; }).distance(80).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(this.width / 2, this.height / 2))
      .force('y', d3.forceY(function (d) { return layerY[d.layer] || self.height / 2; }).strength(0.15))
      .force('collision', d3.forceCollide().radius(function (d) { return self._nodeRadius(d) + 4; }))
      .on('tick', function () {
        self._tickEdges();
        self._tickNodes();
        self._tickLabels();
      });

    // Let simulation warm up for initial positions then cool down
    this.simulation.alpha(1).alphaDecay(0.02).alphaMin(0.005);
  };

  // ─── Node radius helper ──────────────────────────────────────────────────
  KGExplorer.prototype._nodeRadius = function (d) {
    var deg = d.filteredDegree != null ? d.filteredDegree : d.degree || 1;
    var r = MIN_NODE_RADIUS + Math.sqrt(deg) * 5;
    return Math.min(r, MAX_NODE_RADIUS);
  };

  // ─── Draw edges ──────────────────────────────────────────────────────────
  KGExplorer.prototype._drawEdges = function () {
    var self = this;

    var linkSel = this.linkGroup.selectAll('.kg-link')
      .data(this._simLinks, function (d) { return d.id; });

    // Exit
    linkSel.exit()
      .transition().duration(300)
      .attr('opacity', 0)
      .remove();

    // Enter
    var linkEnter = linkSel.enter()
      .append('line')
      .attr('class', 'kg-link')
      .attr('opacity', 0);

    linkEnter
      .attr('marker-end', function (d) { return 'url(#arrow-' + d.psp_type + ')'; })
      .style('stroke', function (d) { return EDGE_TYPES[d.psp_type] ? EDGE_TYPES[d.psp_type].color : '#999'; })
      .style('stroke-width', function (d) { return 1 + (d.confidence || 0.5) * 3; })
      .style('stroke-dasharray', function (d) {
        return EDGE_TYPES[d.psp_type] && EDGE_TYPES[d.psp_type].dash !== 'none' ? EDGE_TYPES[d.psp_type].dash : null;
      });

    // Interactive hover
    linkEnter
      .on('mouseenter', function (event, d) {
        self._onEdgeHover(event, d);
      })
      .on('mouseleave', function () {
        self._onEdgeLeave();
      });

    // Update
    linkSel.merge(linkEnter)
      .transition().duration(300)
      .attr('opacity', 1)
      .attr('marker-end', function (d) { return 'url(#arrow-' + d.psp_type + ')'; })
      .style('stroke', function (d) { return EDGE_TYPES[d.psp_type] ? EDGE_TYPES[d.psp_type].color : '#999'; })
      .style('stroke-width', function (d) { return 1 + (d.confidence || 0.5) * 3; })
      .style('stroke-dasharray', function (d) {
        return EDGE_TYPES[d.psp_type] && EDGE_TYPES[d.psp_type].dash !== 'none' ? EDGE_TYPES[d.psp_type].dash : null;
      });
  };

  // ─── Draw nodes ──────────────────────────────────────────────────────────
  KGExplorer.prototype._drawNodes = function () {
    var self = this;

    var nodeSel = this.nodeGroup.selectAll('.kg-node')
      .data(this.filteredNodes, function (d) { return d.id; });

    // Exit
    nodeSel.exit()
      .transition().duration(300)
      .attr('r', 0)
      .attr('opacity', 0)
      .remove();

    // Enter
    var nodeEnter = nodeSel.enter()
      .append('circle')
      .attr('class', 'kg-node')
      .attr('r', 0)
      .attr('opacity', 0)
      .attr('fill', function (d) { return PSP_LAYERS[d.layer] ? PSP_LAYERS[d.layer].color : '#999'; })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer');

    nodeEnter
      .transition().duration(400)
      .attr('r', function (d) { return self._nodeRadius(d); })
      .attr('opacity', 1);

    // Merge
    var nodeMerge = nodeSel.merge(nodeEnter);

    nodeMerge
      .transition().duration(300)
      .attr('r', function (d) { return self._nodeRadius(d); })
      .attr('fill', function (d) { return PSP_LAYERS[d.layer] ? PSP_LAYERS[d.layer].color : '#999'; });

    // Drag behavior
    nodeMerge.call(d3.drag()
      .on('start', function (event, d) { self._dragStarted(event, d); })
      .on('drag', function (event, d) { self._dragged(event, d); })
      .on('end', function (event, d) { self._dragEnded(event, d); })
    );

    // Hover and click
    nodeMerge
      .on('mouseenter', function (event, d) { self._onNodeHover(event, d); })
      .on('mouseleave', function () { self._onNodeLeave(); })
      .on('click', function (event, d) { self._onNodeClick(event, d); });
  };

  // ─── Draw labels ─────────────────────────────────────────────────────────
  KGExplorer.prototype._drawLabels = function () {
    var self = this;

    var labelSel = this.labelGroup.selectAll('.kg-label')
      .data(this.filteredNodes, function (d) { return d.id; });

    // Exit
    labelSel.exit()
      .transition().duration(200)
      .attr('opacity', 0)
      .remove();

    // Enter
    var labelEnter = labelSel.enter()
      .append('text')
      .attr('class', 'kg-label')
      .attr('text-anchor', 'middle')
      .attr('dy', function (d) { return self._nodeRadius(d) + 14; })
      .attr('fill', '#333')
      .attr('font-size', '11px')
      .attr('font-family', '"Inter", "Segoe UI", system-ui, sans-serif')
      .attr('pointer-events', 'none')
      .attr('opacity', 0)
      .text(function (d) { return self._truncateLabel(d.id); });

    labelEnter
      .transition().duration(400)
      .attr('opacity', 1);

    // Update
    labelSel.merge(labelEnter)
      .transition().duration(300)
      .attr('dy', function (d) { return self._nodeRadius(d) + 14; })
      .text(function (d) { return self._truncateLabel(d.id); });
  };

  // ─── Truncate label ─────────────────────────────────────────────────────
  KGExplorer.prototype._truncateLabel = function (text) {
    if (!text) return '';
    return text.length > 20 ? text.substring(0, 18) + '…' : text;
  };

  // ─── Tick handlers ───────────────────────────────────────────────────────
  KGExplorer.prototype._tickEdges = function () {
    this.linkGroup.selectAll('.kg-link')
      .attr('x1', function (d) { return d.source.x; })
      .attr('y1', function (d) { return d.source.y; })
      .attr('x2', function (d) { return d.target.x; })
      .attr('y2', function (d) { return d.target.y; });
  };

  KGExplorer.prototype._tickNodes = function () {
    this.nodeGroup.selectAll('.kg-node')
      .attr('cx', function (d) { return d.x; })
      .attr('cy', function (d) { return d.y; });
  };

  KGExplorer.prototype._tickLabels = function () {
    this.labelGroup.selectAll('.kg-label')
      .attr('x', function (d) { return d.x; })
      .attr('y', function (d) { return d.y; });
  };

  // ─── Drag handlers ───────────────────────────────────────────────────────
  KGExplorer.prototype._dragStarted = function (event, d) {
    if (!event.active) this.simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  };

  KGExplorer.prototype._dragged = function (event, d) {
    d.fx = event.x;
    d.fy = event.y;
  };

  KGExplorer.prototype._dragEnded = function (event, d) {
    if (!event.active) this.simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  };

  // ─── Node hover ──────────────────────────────────────────────────────────
  KGExplorer.prototype._onNodeHover = function (event, d) {
    this.hoveredNode = d;

    // Highlight connected edges
    var connectedIds = new Set();
    connectedIds.add(d.id);

    this.linkGroup.selectAll('.kg-link')
      .transition().duration(150)
      .style('opacity', function (l) {
        return (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.15;
      });

    // Highlight connected nodes
    var neighborIds = new Set();
    neighborIds.add(d.id);
    this._simLinks.forEach(function (l) {
      if (l.source.id === d.id) neighborIds.add(l.target.id);
      if (l.target.id === d.id) neighborIds.add(l.source.id);
    });

    this.nodeGroup.selectAll('.kg-node')
      .transition().duration(150)
      .style('opacity', function (n) { return neighborIds.has(n.id) ? 1 : 0.2; });

    this.labelGroup.selectAll('.kg-label')
      .transition().duration(150)
      .style('opacity', function (n) { return neighborIds.has(n.id) ? 1 : 0.2; });

    // Show tooltip
    this._showTooltip(event, this._nodeTooltipHTML(d));
  };

  KGExplorer.prototype._onNodeLeave = function () {
    this.hoveredNode = null;

    // Reset opacity
    this.linkGroup.selectAll('.kg-link').transition().duration(200).style('opacity', 1);
    this.nodeGroup.selectAll('.kg-node').transition().duration(200).style('opacity', 1);
    this.labelGroup.selectAll('.kg-label').transition().duration(200).style('opacity', 1);

    this._hideTooltip();
  };

  // ─── Edge hover ───────────────────────────────────────────────────────────
  KGExplorer.prototype._onEdgeHover = function (event, d) {
    this.hoveredEdge = d;

    // Highlight this edge
    this.linkGroup.selectAll('.kg-link')
      .transition().duration(150)
      .style('opacity', function (l) { return l.id === d.id ? 1 : 0.2; })
      .style('stroke-width', function (l) {
        var base = 1 + (l.confidence || 0.5) * 3;
        return l.id === d.id ? base + 2 : base;
      });

    this._showTooltip(event, this._edgeTooltipHTML(d));
  };

  KGExplorer.prototype._onEdgeLeave = function () {
    this.hoveredEdge = null;

    this.linkGroup.selectAll('.kg-link')
      .transition().duration(200)
      .style('opacity', 1)
      .style('stroke-width', function (l) { return 1 + (l.confidence || 0.5) * 3; });

    this._hideTooltip();
  };

  // ─── Node click - show PSP paths ─────────────────────────────────────────
  KGExplorer.prototype._onNodeClick = function (event, d) {
    this.selectedNode = d;
    this._showDetailPanel(d);
  };

  // ─── Tooltip HTML ───────────────────────────────────────────────────────
  KGExplorer.prototype._nodeTooltipHTML = function (d) {
    var layerColor = PSP_LAYERS[d.layer] ? PSP_LAYERS[d.layer].color : '#999';
    var deg = d.filteredDegree != null ? d.filteredDegree : d.degree;
    var html = '<div style="font-weight:600;margin-bottom:4px;color:' + layerColor + '">' + d.id + '</div>';
    html += '<div>Layer: ' + d.layer + '</div>';
    html += '<div>Connections: ' + deg + '</div>';
    return html;
  };

  KGExplorer.prototype._edgeTooltipHTML = function (d) {
    var et = EDGE_TYPES[d.psp_type] || {};
    var html = '<div style="font-weight:600;margin-bottom:4px;">' + (d.relation || 'relates to') + '</div>';
    html += '<div style="color:' + (et.color || '#999') + '">' + (et.label || d.psp_type) + '</div>';
    html += '<div>Confidence: ' + (d.confidence != null ? d.confidence.toFixed(2) : 'N/A') + '</div>';
    if (d.material) html += '<div>Material: ' + d.material + '</div>';
    if (d.evidence_text) html += '<div style="margin-top:4px;font-style:italic;opacity:0.85">“' + d.evidence_text + '”</div>';
    return html;
  };

  // ─── Show/hide tooltip ───────────────────────────────────────────────────
  KGExplorer.prototype._showTooltip = function (event, html) {
    var containerRect = this.container.node().getBoundingClientRect();
    var x = event.clientX - containerRect.left + 12;
    var y = event.clientY - containerRect.top + 12;

    // Keep tooltip in bounds
    if (x + 300 > containerRect.width) x = containerRect.width - 310;
    if (y + 200 > containerRect.height) y = containerRect.height - 210;

    this.tooltip
      .style('display', 'block')
      .style('left', x + 'px')
      .style('top', y + 'px')
      .html(html);
  };

  KGExplorer.prototype._hideTooltip = function () {
    this.tooltip.style('display', 'none');
  };

  // ─── Detail panel: show all PSP paths through a node ─────────────────────
  KGExplorer.prototype._showDetailPanel = function (d) {
    var panel = this.detailPanel;
    panel.style('display', 'block');

    var layerColor = PSP_LAYERS[d.layer] ? PSP_LAYERS[d.layer].color : '#999';

    var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">';
    html += '<div style="font-weight:700;font-size:15px;color:' + layerColor + '">' + d.id + '</div>';
    html += '<button class="kg-detail-close" style="background:none;border:none;font-size:18px;cursor:pointer;color:#999">&times;</button>';
    html += '</div>';
    html += '<div style="font-size:12px;color:#777;margin-bottom:8px">Layer: <strong style="color:' + layerColor + '">' + d.layer + '</strong> &middot; ' + (d.filteredDegree || d.degree || 0) + ' connections</div>';

    // Find all PSP paths through this node
    var self = this;
    var links = this._simLinks || [];
    var incomingP = links.filter(function (l) { return l.target.id === d.id && l.psp_type === 'Processing_to_Structure'; });
    var incomingS = links.filter(function (l) { return l.target.id === d.id && l.psp_type === 'Structure_to_Property'; });
    var outgoingS = links.filter(function (l) { return l.source.id === d.id && l.psp_type === 'Processing_to_Structure'; });
    var outgoingP = links.filter(function (l) { return l.source.id === d.id && l.psp_type === 'Structure_to_Property'; });
    var shortcuts = links.filter(function (l) {
      return (l.source.id === d.id || l.target.id === d.id) && l.psp_type === 'Processing_to_Property';
    });

    // Build P->S->P chains
    var chains = [];
    if (d.layer === 'Structure') {
      // P -> this -> P'
      incomingP.forEach(function (ip) {
        outgoingP.forEach(function (op) {
          chains.push({
            steps: [ip.source.id, d.id, op.target.id],
            edges: [ip, op],
            confidence: Math.min(ip.confidence, op.confidence)
          });
        });
      });
    }

    if (chains.length > 0) {
      html += '<div style="font-weight:600;font-size:13px;margin:8px 0 4px;color:#333">P→S→P\' Chains</div>';
      chains.forEach(function (chain) {
        html += '<div style="background:#f0f4ff;padding:6px 8px;border-radius:4px;margin-bottom:4px;font-size:12px;border-left:3px solid #1E88E5">';
        html += chain.steps.join(' → ');
        html += '<div style="color:#888;font-size:11px">Confidence: ' + chain.confidence.toFixed(2) + '</div>';
        html += '</div>';
      });
    }

    // Show all connections
    html += '<div style="font-weight:600;font-size:13px;margin:8px 0 4px;color:#333">Direct Connections</div>';

    var allConnected = links.filter(function (l) {
      return l.source.id === d.id || l.target.id === d.id;
    });

    if (allConnected.length === 0) {
      html += '<div style="color:#999;font-size:12px">No connections visible with current filters.</div>';
    } else {
      allConnected.forEach(function (l) {
        var et = EDGE_TYPES[l.psp_type] || {};
        var otherNode = l.source.id === d.id ? l.target.id : l.source.id;
        var direction = l.source.id === d.id ? '→' : '←';
        html += '<div style="padding:4px 0;font-size:12px;border-bottom:1px solid #f0f0f0">';
        html += '<span style="color:' + (et.color || '#999') + '">●</span> ';
        html += direction + ' ' + otherNode;
        html += ' <span style="color:#999">(' + (et.label || l.psp_type) + ', conf: ' + (l.confidence != null ? l.confidence.toFixed(2) : 'N/A') + ')</span>';
        if (l.material) html += ' <span style="color:#888">[' + l.material + ']</span>';
        html += '</div>';
      });
    }

    // Warning for P->P shortcuts
    if (shortcuts.length > 0) {
      html += '<div style="margin-top:8px;padding:8px;background:#fff3e0;border-radius:4px;border-left:3px solid #E53935;font-size:12px">';
      html += '<strong style="color:#E53935">⚠ Contextual Tunneling</strong><br>';
      html += '<span style="color:#666">P→P\' shortcuts bypass the structure layer:</span>';
      shortcuts.forEach(function (s) {
        var other = s.source.id === d.id ? s.target.id : s.source.id;
        html += '<div style="margin-top:3px;color:#555">' + s.source.id + ' → ' + s.target.id + ' (conf: ' + (s.confidence != null ? s.confidence.toFixed(2) : 'N/A') + ')</div>';
      });
      html += '</div>';
    }

    panel.html(html);

    // Close button
    panel.select('.kg-detail-close').on('click', function () {
      panel.style('display', 'none');
      self.selectedNode = null;
    });
  };

  // ─── Highlight PSP chains ────────────────────────────────────────────────
  KGExplorer.prototype._highlightPSPChains = function () {
    var links = this._simLinks || [];

    // Find complete P -> S -> P' chains
    var processingToStructure = links.filter(function (l) { return l.psp_type === 'Processing_to_Structure'; });
    var structureToProperty = links.filter(function (l) { return l.psp_type === 'Structure_to_Property'; });
    var shortcuts = links.filter(function (l) { return l.psp_type === 'Processing_to_Property'; });

    // Build chain set: P -> S -> P'
    var chainLinks = new Set();
    processingToStructure.forEach(function (ps) {
      structureToProperty.forEach(function (sp) {
        if (ps.target.id === sp.source.id) {
          chainLinks.add(ps.id);
          chainLinks.add(sp.id);
        }
      });
    });

    // Apply glow to chain links
    this.linkGroup.selectAll('.kg-link')
      .style('filter', function (d) {
        if (chainLinks.has(d.id)) return 'url(#kg-glow)';
        return null;
      });

    // Apply warning glow to P->P shortcuts
    shortcuts.forEach(function (sc) {
      this.linkGroup.selectAll('.kg-link')
        .filter(function (d) { return d.id === sc.id; })
        .style('filter', 'url(#kg-warning-glow)');
    }.bind(this));

    // Add warning indicators for shortcuts (small diamond at midpoint)
    this.linkGroup.selectAll('.kg-shortcut-indicator').remove();
    shortcuts.forEach(function (sc) {
      var mx = (sc.source.x + sc.target.x) / 2;
      var my = (sc.source.y + sc.target.y) / 2;
      this.linkGroup.append('polygon')
        .attr('class', 'kg-shortcut-indicator')
        .attr('points', mx + ',' + (my - 6) + ' ' + (mx + 5) + ',' + my + ' ' + mx + ',' + (my + 6) + ' ' + (mx - 5) + ',' + my)
        .attr('fill', '#E53935')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .style('filter', 'url(#kg-warning-glow)');
    }.bind(this));
  };

  // ─── Build legend ────────────────────────────────────────────────────────
  KGExplorer.prototype._buildLegend = function () {
    var legend = this.container.append('div')
      .attr('class', 'kg-legend')
      .style('display', 'flex')
      .style('flex-wrap', 'wrap')
      .style('gap', '16px')
      .style('padding', '8px 0')
      .style('font-family', '"Inter", "Segoe UI", system-ui, sans-serif')
      .style('font-size', '12px')
      .style('color', '#555')
      .style('align-items', 'center');

    // Node legend
    var nodeLegend = legend.append('div').style('display', 'flex').style('gap', '10px').style('align-items', 'center');
    nodeLegend.append('span').style('font-weight', '600').text('Nodes:');
    Object.keys(PSP_LAYERS).forEach(function (layer) {
      var item = nodeLegend.append('span').style('display', 'flex').style('align-items', 'center').style('gap', '3px');
      item.append('span')
        .style('display', 'inline-block')
        .style('width', '12px').style('height', '12px')
        .style('border-radius', '50%')
        .style('background', PSP_LAYERS[layer].color);
      item.append('span').text(PSP_LAYERS[layer].label);
    });

    // Edge legend
    var edgeLegend = legend.append('div').style('display', 'flex').style('gap', '10px').style('align-items', 'center');
    edgeLegend.append('span').style('font-weight', '600').text('Edges:');
    Object.keys(EDGE_TYPES).forEach(function (key) {
      var et = EDGE_TYPES[key];
      var item = edgeLegend.append('span').style('display', 'flex').style('align-items', 'center').style('gap', '3px');
      item.append('span')
        .style('display', 'inline-block')
        .style('width', '24px').style('height', '0')
        .style('border-top', '2px ' + (et.dash === 'none' ? 'solid' : 'dashed') + ' ' + et.color);
      item.append('span').text(et.label);
    });

    // Glow legend
    var glowLegend = legend.append('div').style('display', 'flex').style('gap', '10px').style('align-items', 'center');
    glowLegend.append('span')
      .style('padding', '2px 6px')
      .style('background', 'rgba(30,136,229,0.15)')
      .style('border-radius', '3px')
      .text('P→S→P\' chain glow');
    glowLegend.append('span')
      .style('padding', '2px 6px')
      .style('background', 'rgba(229,57,53,0.15)')
      .style('border-radius', '3px')
      .html('⚠ P→P\' contextual tunneling');
  };

  // ─── Responsive resize ───────────────────────────────────────────────────
  KGExplorer.prototype._handleResize = function () {
    var rect = this.container.node().getBoundingClientRect();
    this.width = rect.width;
    this.height = Math.max(rect.height - 60, 400);

    this.svg
      .attr('width', this.width)
      .attr('height', this.height);

    if (this.simulation) {
      this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
      this.simulation.alpha(0.3).restart();
    }
  };

  // ─── Public API ──────────────────────────────────────────────────────────
  KGExplorer.prototype.updateFilters = function (newFilters) {
    Object.assign(this.filters, newFilters);
    this._applyFilters();
  };

  KGExplorer.prototype.resetFilters = function () {
    this.filters = {
      material: 'all',
      layers: { Processing: true, Structure: true, Property: true },
      edgeTypes: { Processing_to_Structure: true, Structure_to_Property: true, Processing_to_Property: true },
      confidenceThreshold: 0.0
    };
    // Reset DOM controls
    this.container.select('.kg-filter-material').property('value', 'all');
    this.container.selectAll('.kg-filter-layer').property('checked', true);
    this.container.selectAll('.kg-filter-edge').property('checked', true);
    this.container.select('input[type=range]').property('value', 0);
    this.container.select('.kg-conf-value').text('0.00');
    this._applyFilters();
  };

  KGExplorer.prototype.destroy = function () {
    if (this.simulation) this.simulation.stop();
    this.container.selectAll('*').remove();
    this.container.attr('class', null).style('position', null).style('width', null).style('height', null);
  };

  // ─── Expose to global ────────────────────────────────────────────────────
  global.KGExplorer = KGExplorer;

})(typeof window !== 'undefined' ? window : this);
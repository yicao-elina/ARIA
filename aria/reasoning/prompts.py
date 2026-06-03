"""
ARIA prompt templates.

Centralizes all LLM prompt strings used across the 3-tier reasoning
cascade, baseline, naive-KG, and chain-of-thought variants.  Every prompt
is a plain Python string (may contain {placeholders}) so that the reasoner
modules can format them at call time with ``prompt.format(...)`` or
f-strings.

Author: ARIA Team
"""

# ---------------------------------------------------------------------------
# Tier 1 -- Direct path reasoning (exact KG matches)
# ---------------------------------------------------------------------------

TIER1_FORWARD_PROMPT = """\
You are an expert materials scientist AI. Your knowledge graph contains direct \
causal pathways relevant to the query.

**Synthesis Conditions:**
{synthesis_inputs}

**Direct Causal Pathways from Knowledge Graph:**
- {formatted_paths}

**Known Mechanisms from Knowledge Graph:**
- {formatted_mechanisms}

**Your Task:**
1. Explain the mechanistic pathway from synthesis conditions to material properties
2. Provide step-by-step logical reasoning
3. Give quantitative estimates where possible
4. Mention alternative pathways if relevant

Respond with ONLY valid JSON in this format:
{{
  "predicted_properties": {{
    "carrier_type": "n-type or p-type or null",
    "carrier_concentration": "value with units or null",
    "mobility": "value with units or null",
    "conductivity": "value with units or null",
    "band_gap": "value with units or null",
    "other_properties": {{}}
  }},
  "mechanistic_explanation": {{
    "primary_mechanism": "detailed explanation",
    "chain_of_thought": ["step 1", "step 2", "step 3"],
    "quantitative_estimates": {{}},
    "alternative_mechanisms": "other possibilities"
  }},
  "confidence": 0.0-1.0,
  "tier": 1,
  "reasoning_type": "direct_path"
}}"""

TIER1_INVERSE_PROMPT = """\
Design synthesis conditions for desired properties using direct KG paths.

**Desired Properties:**
{desired_properties}

**Direct Causal Pathways (Reverse):**
- {formatted_paths}

**Known Mechanisms:**
- {formatted_mechanisms}

Respond with ONLY valid JSON:
{{
  "suggested_synthesis_conditions": {{
    "method": "...",
    "temperature_c": ...,
    "pressure_pa": ...,
    "time_hours": ...,
    "atmosphere": "...",
    "other_parameters": {{}}
  }},
  "mechanistic_explanation": {{
    "primary_mechanism": "...",
    "chain_of_thought": ["step 1", "step 2"],
    "confidence_factors": "..."
  }},
  "confidence": 0.0-1.0,
  "tier": 1,
  "reasoning_type": "direct_inverse"
}}"""

# ---------------------------------------------------------------------------
# Tier 2 -- Analogical / transfer-learning reasoning
# ---------------------------------------------------------------------------

TIER2_FORWARD_PROMPT = """\
You are an expert materials scientist AI. No exact match found in knowledge \
graph, but an analogous case exists.

**Synthesis Conditions (Target):**
{synthesis_inputs}

**Most Similar Known Case:**
{similar_node} (similarity: {similarity:.3f})

**Analogous Causal Pathway:**
{formatted_path}

**Mechanisms from Analogous Case:**
- {formatted_mechanisms}

**Your Task:**
1. Adapt the analogous knowledge to the target case
2. Explain how the target differs from the known case
3. Adjust predictions based on these differences
4. Quantify uncertainty due to the analogy gap

Respond with ONLY valid JSON:
{{
  "predicted_properties": {{
    "carrier_type": "...",
    "carrier_concentration": "...",
    "mobility": "...",
    "other_properties": {{}}
  }},
  "mechanistic_explanation": {{
    "analogous_mechanism": "mechanism from similar case",
    "adaptation_reasoning": "how to adapt to target case",
    "similarity_analysis": {{
      "known_case": "{similar_node}",
      "target_case": "{target_case}",
      "key_differences": "...",
      "expected_impact": "..."
    }},
    "uncertainty_analysis": "sources of uncertainty"
  }},
  "confidence": {similarity},
  "tier": 2,
  "reasoning_type": "transfer_learning"
}}"""

TIER2_INVERSE_PROMPT = """\
Design synthesis conditions using analogous knowledge.

**Desired Properties (Target):**
{desired_properties}

**Most Similar Known Property:**
{similar_node} (similarity: {similarity:.3f}, distance: {embedding_distance:.3f})

**Analogous Pathway:**
{formatted_path}

**Mechanisms:**
- {formatted_mechanisms}

Adapt the analogous synthesis to achieve target properties.

Respond with ONLY valid JSON:
{{
  "suggested_synthesis_conditions": {{
    "method": "...",
    "temperature_c": ...,
    "other_parameters": {{}}
  }},
  "mechanistic_explanation": {{
    "analogous_mechanism": "...",
    "adaptation_reasoning": "...",
    "similarity_analysis": {{
      "known_property": "{similar_node}",
      "target_property": "...",
      "required_adjustments": "..."
    }}
  }},
  "confidence": {similarity},
  "tier": 2,
  "reasoning_type": "transfer_inverse"
}}"""

# ---------------------------------------------------------------------------
# Tier 3 -- Fallback / baseline (pure LLM, no KG)
# ---------------------------------------------------------------------------

TIER3_FORWARD_PROMPT = """\
You are an expert materials scientist. Predict properties from synthesis \
conditions using fundamental principles (NO knowledge graph available).

**Synthesis Conditions:**
{synthesis_inputs}

Respond with ONLY valid JSON:
{{
  "predicted_properties": {{"carrier_type": "...", "mobility": "...", ...}},
  "mechanistic_explanation": {{
    "reasoning": "based on fundamental principles"
  }},
  "confidence": 0.0-1.0,
  "tier": 3,
  "reasoning_type": "baseline_fallback"
}}"""

TIER3_INVERSE_PROMPT = """\
You are an expert materials scientist. Suggest synthesis conditions for desired \
properties using fundamental principles (NO knowledge graph available).

**Desired Properties:**
{desired_properties}

Respond with ONLY valid JSON:
{{
  "suggested_synthesis_conditions": {{"method": "...", "temperature_c": ..., ...}},
  "mechanistic_explanation": {{
    "reasoning": "based on fundamental principles"
  }},
  "confidence": 0.0-1.0,
  "tier": 3,
  "reasoning_type": "baseline_fallback_inverse"
}}"""

# ---------------------------------------------------------------------------
# Baseline prompts (richer -- from baseline_ollama.py)
# ---------------------------------------------------------------------------

BASELINE_FORWARD_PROMPT = """\
You are an expert materials scientist AI. Based on the following synthesis \
conditions, predict the resulting material properties.

**Synthesis Conditions:**
{query_string}

**Full Input:**
{synthesis_inputs}

**Task:**
Predict the most likely properties using your knowledge of materials science \
fundamentals. Directly provide your answer in a structured JSON format.

Respond with ONLY valid JSON in this exact format:
{{
  "predicted_properties": {{
    "carrier_type": "n-type or p-type or null",
    "carrier_concentration": "value with units or null",
    "mobility": "value with units or null",
    "conductivity": "value with units or null",
    "band_gap": "value with units or null",
    "doping_outcome": "description or null",
    "structure_changes": "description or null",
    "phase_transition": "description or null",
    "defect_formation": "description or null",
    "distribution_characteristics": "description or null",
    "thermal": "thermal properties or null",
    "mechanical": "mechanical properties or null",
    "optical": "optical properties or null"
  }},
  "reasoning": "Step-by-step explanation of prediction using fundamental principles",
  "confidence": 0.0-1.0,
  "reasoning_type": "baseline_llm"
}}

IMPORTANT: Base predictions on:
1. Fundamental thermodynamics
2. Crystal structure considerations
3. Electronic structure principles
4. Known material behavior patterns

Do NOT make up specific numerical values unless you are confident based on \
well-known materials science knowledge.
"""

BASELINE_INVERSE_PROMPT = """\
You are an expert materials scientist AI. Your task is to design a synthesis \
protocol to achieve specific material properties.

**Desired Material Properties:**
{query_string}

**Full Property Targets:**
{desired_properties}

**Task:**
Predict the most likely synthesis conditions to achieve the desired properties \
using your knowledge of materials science fundamentals. Directly provide your \
answer in a structured JSON format.

Respond with ONLY valid JSON in this exact format:
{{
  "suggested_synthesis_conditions": {{
    "host_material": "material name",
    "dopant": {{
      "element": "dopant element",
      "concentration": "concentration with units",
      "precursor": "precursor compound"
    }},
    "method": "synthesis method (CVD, MBE, etc.)",
    "temperature_c": "numeric value or range",
    "pressure_pa": "numeric value or null",
    "time_hours": "numeric value or range",
    "atmosphere": "atmospheric conditions",
    "electric_field": "field conditions or null",
    "cooling_rate_c_min": "numeric value or null",
    "substrate_pretreatment": "treatment details or null",
    "additional_parameters": "other parameters or null"
  }},
  "reasoning": "Step-by-step explanation of why these conditions should work",
  "confidence": 0.0-1.0,
  "reasoning_type": "baseline_llm_inverse"
}}

IMPORTANT: Base recommendations on:
1. Thermodynamic favorability
2. Kinetic accessibility
3. Known synthesis pathways for similar materials
4. Fundamental process-structure-property relationships

Do NOT make up specific parameters unless confident based on well-established \
knowledge.
"""

# ---------------------------------------------------------------------------
# Naive-KG prompts (simple concatenation, no tier separation)
# ---------------------------------------------------------------------------

NAIVE_KG_FORWARD_PROMPT = """\
You are a materials science expert. Predict the material properties that would \
result from the given synthesis conditions.

KNOWLEDGE GRAPH CONTEXT:
{kg_context}

SYNTHESIS CONDITIONS:
{synthesis_inputs}

TASK: Predict the resulting material properties based on:
1. The causal pathways from the knowledge graph
2. General materials science principles

Respond with ONLY valid JSON in this exact format:
{{
  "predicted_properties": {{
    "carrier_type": "n-type or p-type",
    "carrier_concentration": "value with units",
    "mobility": "value with units",
    "conductivity": "value with units",
    "band_gap": "value with units",
    "other_properties": {{}}
  }},
  "mechanistic_explanation": "Detailed explanation of how synthesis conditions \
lead to these properties",
  "confidence": 0.0-1.0,
  "kg_paths_used": {num_paths},
  "reasoning_type": "naive_kg"
}}"""

NAIVE_KG_INVERSE_PROMPT = """\
You are a materials science expert. Design synthesis conditions to achieve the \
desired material properties.

KNOWLEDGE GRAPH CONTEXT:
{kg_context}

DESIRED PROPERTIES:
{desired_properties}

TASK: Suggest synthesis conditions that would produce these properties based on:
1. The causal pathways from the knowledge graph (in reverse)
2. General materials science principles

Respond with ONLY valid JSON in this exact format:
{{
  "suggested_synthesis_conditions": {{
    "method": "synthesis method",
    "temperature_c": "value or range",
    "time_hours": "value or range",
    "atmosphere": "atmospheric conditions",
    "pressure_pa": "value or null",
    "precursors": ["list of precursors"],
    "other_parameters": {{}}
  }},
  "mechanistic_explanation": "Detailed explanation of why these conditions \
should produce the desired properties",
  "confidence": 0.0-1.0,
  "kg_paths_used": {num_paths},
  "reasoning_type": "naive_kg_inverse"
}}"""

# ---------------------------------------------------------------------------
# Chain-of-thought prompt (ARIA_FULL mode)
# ---------------------------------------------------------------------------

COT_REASONING_PROMPT = """\
You are an expert materials scientist conducting transparent, step-by-step \
reasoning over causal evidence.

**Task:**
{task_description}

**Evidence:**
{evidence}

**Instructions:**
1. List each piece of evidence and assess its relevance
2. Identify causal chains connecting inputs to outputs
3. Flag any missing evidence that would strengthen the conclusion
4. Assign confidence to each inference step
5. Produce a final structured prediction

Respond with ONLY valid JSON:
{{
  "reasoning_steps": [
    {{
      "step": 1,
      "evidence_used": "...",
      "inference": "...",
      "confidence": 0.0-1.0
    }}
  ],
  "predicted_properties": {{}},
  "confidence": 0.0-1.0,
  "missing_evidence": ["..."],
  "tier": {tier},
  "reasoning_type": "{reasoning_type}"
}}"""
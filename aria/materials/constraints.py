"""
Physical validity checks for 2D materials synthesis.

Provides constraint validation for temperature ranges, composition
compatibility, and atmosphere-dopant interactions commonly encountered
in CVD, MOCVD, and sputtering processes for 2D materials.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference data tables
# ---------------------------------------------------------------------------

# Approximate decomposition / stability temperatures (Celsius) for common
# 2D materials and substrates.  Values are representative ranges from the
# literature and should be treated as sanity-check boundaries.

MATERIAL_TEMP_RANGES: Dict[str, Dict[str, float]] = {
    # material: {"min": ..., "max": ...}
    "MoS2": {"min": 300, "max": 1200},
    "WS2": {"min": 300, "max": 1100},
    "WSe2": {"min": 200, "max": 950},
    "MoSe2": {"min": 250, "max": 1000},
    "MoTe2": {"min": 200, "max": 900},
    "WTe2": {"min": 200, "max": 850},
    "graphene": {"min": 300, "max": 1500},
    "hBN": {"min": 400, "max": 1500},
    "black_phosphorus": {"min": 0, "max": 400},
    "BP": {"min": 0, "max": 400},
}

# Common substrate materials and their practical upper temperature limits.
SUBSTRATE_TEMP_LIMITS: Dict[str, float] = {
    "SiO2": 1200,
    "sapphire": 1800,
    "Si": 1414,   # melting point
    "SiC": 2700,
    "glass": 600,
    "quartz": 1200,
    "Al2O3": 1800,
    "mica": 600,
}

# Atmosphere compatibility: which atmospheres are compatible with which
# dopant types.  ``True`` means the combination is known to work.
ATMOSPHERE_DOPANT_COMPAT: Dict[str, Dict[str, bool]] = {
    # atmosphere -> dopant -> compatible?
    "H2/Ar": {
        "Nb": True, "Re": True, "Fe": True, "Co": True, "Mn": True,
        "Cr": True, "V": True, "W": True, "Ta": True,
    },
    "Ar": {
        "Nb": True, "Re": True, "Fe": True, "Co": True,
    },
    "H2": {
        "Nb": True, "Re": True, "Fe": True,
    },
    "N2": {
        "N": True,  # nitrogen doping
        "Nb": False, "Re": False,  # reducing atmosphere preferred
    },
    "vacuum": {
        "Nb": True, "Re": True, "Fe": True,
    },
    "forming_gas": {
        "Nb": True, "Re": True, "Fe": True, "Co": True,
    },
}

# Precursor-substrate compatibility matrix.
# Keys are (precursor_family, substrate) pairs that are known to work.
PRECURSOR_SUBSTRATE_COMPAT: Dict[str, set] = {
    "MoO3": {"SiO2", "sapphire", "SiC", "quartz"},
    "WO3": {"SiO2", "sapphire", "SiC"},
    "MoCl5": {"SiO2", "sapphire"},
    "WCl6": {"SiO2", "sapphire"},
    "S": {"SiO2", "sapphire", "SiC", "quartz", "mica"},
    "Se": {"SiO2", "sapphire", "SiC", "quartz"},
    "Te": {"SiO2", "sapphire"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_synthesis_conditions(conditions: Dict[str, Any]) -> Dict[str, bool]:
    """Validate a set of synthesis conditions for physical plausibility.

    Parameters
    ----------
    conditions :
        Dictionary that may contain the following keys:

        - ``material`` (str): Target 2D material (e.g. ``"MoS2"``).
        - ``temperature_C`` (float): Synthesis temperature in Celsius.
        - ``substrate`` (str): Substrate material.
        - ``atmosphere`` (str): Atmosphere composition (e.g. ``"H2/Ar"``).
        - ``dopant`` (str): Dopant element.
        - ``precursor`` (str): Precursor compound.
        - ``method`` (str): Synthesis method.

    Returns
    -------
    dict
        Boolean checks keyed by validation name:

        - ``temperature_in_range``: Temperature within material limits.
        - ``substrate_temperature_ok``: Substrate can tolerate the temperature.
        - ``atmosphere_dopant_compatible``: Atmosphere works with the dopant.
        - ``precursor_substrate_compatible``: Precursor works on substrate.
        - ``overall_valid``: All checks pass.
    """
    results: Dict[str, bool] = {}

    material = conditions.get("material", "")
    temperature = conditions.get("temperature_C", 0.0)
    substrate = conditions.get("substrate", "")
    atmosphere = conditions.get("atmosphere", "")
    dopant = conditions.get("dopant", "")
    precursor = conditions.get("precursor", "")

    # 1. Temperature in range for material
    if material in MATERIAL_TEMP_RANGES:
        rng = MATERIAL_TEMP_RANGES[material]
        results["temperature_in_range"] = rng["min"] <= temperature <= rng["max"]
    else:
        # Unknown material: accept but warn
        logger.info("Unknown material %r; skipping temperature range check", material)
        results["temperature_in_range"] = True

    # 2. Substrate temperature limit
    if substrate and substrate in SUBSTRATE_TEMP_LIMITS:
        results["substrate_temperature_ok"] = temperature <= SUBSTRATE_TEMP_LIMITS[substrate]
    else:
        results["substrate_temperature_ok"] = True  # unknown substrate

    # 3. Atmosphere-dopant compatibility
    if atmosphere and dopant:
        atm_compat = ATMOSPHERE_DOPANT_COMPAT.get(atmosphere, {})
        if dopant in atm_compat:
            results["atmosphere_dopant_compatible"] = atm_compat[dopant]
        else:
            # Unknown combination: accept with warning
            logger.info("Unknown atmosphere/dopant pair: %s / %s", atmosphere, dopant)
            results["atmosphere_dopant_compatible"] = True
    else:
        results["atmosphere_dopant_compatible"] = True

    # 4. Precursor-substrate compatibility
    if precursor and substrate:
        compat_set = PRECURSOR_SUBSTRATE_COMPAT.get(precursor, set())
        if compat_set:
            results["precursor_substrate_compatible"] = substrate in compat_set
        else:
            results["precursor_substrate_compatible"] = True
    else:
        results["precursor_substrate_compatible"] = True

    # Overall
    results["overall_valid"] = all(results.values())

    return results


def check_thermal_stability(material: str, temperature: float) -> bool:
    """Check whether *material* is thermally stable at *temperature* (Celsius).

    Parameters
    ----------
    material :
        2D material name (e.g. ``"MoS2"``).
    temperature :
        Temperature in Celsius.

    Returns
    -------
    bool
        ``True`` if the temperature is within the material's known stability
        range, ``False`` otherwise.
    """
    if material in MATERIAL_TEMP_RANGES:
        rng = MATERIAL_TEMP_RANGES[material]
        return rng["min"] <= temperature <= rng["max"]

    # Unknown material: accept with a warning
    logger.info("Unknown material %r; assuming thermally stable", material)
    return True


def check_composition_compatibility(precursor: str, substrate: str) -> bool:
    """Check whether *precursor* and *substrate* are compositionally compatible.

    Parameters
    ----------
    precursor :
        Precursor compound name (e.g. ``"MoO3"``).
    substrate :
        Substrate material name (e.g. ``"SiO2"``).

    Returns
    -------
    bool
        ``True`` if the precursor-substrate pair is known to be compatible
        or if the combination is not in the database (unknown pairs default
        to compatible).
    """
    compat_set = PRECURSOR_SUBSTRATE_COMPAT.get(precursor)
    if compat_set is None:
        logger.info("Unknown precursor %r; assuming compatible", precursor)
        return True
    return substrate in compat_set
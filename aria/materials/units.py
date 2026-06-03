"""
Unit normalization for materials science quantities.

Provides functions to normalise temperature, pressure, and time values
into canonical units (Celsius, Pascal, second) so that downstream
comparisons are consistent regardless of input units.
"""

from __future__ import annotations

from typing import Union

Number = Union[int, float]


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------

# Absolute zero in Celsius
_ABS_ZERO_C = -273.15

_TEMP_CONVERSIONS = {
    # (from_unit) -> factor to convert to Celsius
    "C": 1.0,
    "celsius": 1.0,
    "degC": 1.0,
    "K": None,        # requires offset
    "kelvin": None,
    "F": None,        # requires formula
    "fahrenheit": None,
}


def normalize_temperature(value: Number, unit: str) -> float:
    """Convert a temperature to Celsius.

    Parameters
    ----------
    value :
        Numeric temperature value.
    unit :
        Unit string: ``"C"``, ``"K"``, ``"F"`` (case-insensitive;
        also accepts ``"celsius"``, ``"kelvin"``, ``"fahrenheit"``).

    Returns
    -------
    float
        Temperature in Celsius.

    Raises
    ------
    ValueError
        If *unit* is not recognised.

    Examples
    --------
    >>> normalize_temperature(373.15, "K")
    100.0
    >>> normalize_temperature(212, "F")
    100.0
    """
    u = unit.strip().upper()

    if u in ("C", "CELSIUS", "DEGC"):
        return float(value)
    elif u in ("K", "KELVIN"):
        return float(value) + _ABS_ZERO_C
    elif u in ("F", "FAHRENHEIT"):
        return (float(value) - 32.0) * 5.0 / 9.0
    else:
        raise ValueError(
            f"Unknown temperature unit: {unit!r}. "
            f"Supported: C, K, F (and long forms)."
        )


# ---------------------------------------------------------------------------
# Pressure
# ---------------------------------------------------------------------------

_PRESSURE_CONVERSIONS = {
    # (from_unit) -> factor to convert to Pascal
    "Pa": 1.0,
    "pascal": 1.0,
    "kPa": 1e3,
    "kpa": 1e3,
    "MPa": 1e6,
    "mpa": 1e6,
    "GPa": 1e9,
    "gpa": 1e9,
    "atm": 101325.0,
    "bar": 1e5,
    "mbar": 1e2,
    "torr": 133.322,
    "mmHg": 133.322,
    "psi": 6894.76,
}


def normalize_pressure(value: Number, unit: str) -> float:
    """Convert a pressure to Pascal.

    Parameters
    ----------
    value :
        Numeric pressure value.
    unit :
        Unit string: ``"Pa"``, ``"kPa"``, ``"MPa"``, ``"GPa"``,
        ``"atm"``, ``"bar"``, ``"mbar"``, ``"torr"``, ``"mmHg"``,
        ``"psi"`` (case-insensitive).

    Returns
    -------
    float
        Pressure in Pascal.

    Raises
    ------
    ValueError
        If *unit* is not recognised.

    Examples
    --------
    >>> normalize_pressure(1, "atm")
    101325.0
    >>> normalize_pressure(1, "bar")
    100000.0
    """
    u = unit.strip()

    # Try case-sensitive first (for kPa, MPa, GPa)
    if u in _PRESSURE_CONVERSIONS:
        return float(value) * _PRESSURE_CONVERSIONS[u]

    # Try case-insensitive fallback
    u_lower = u.lower()
    for key, factor in _PRESSURE_CONVERSIONS.items():
        if key.lower() == u_lower:
            return float(value) * factor

    raise ValueError(
        f"Unknown pressure unit: {unit!r}. "
        f"Supported: {', '.join(sorted(set(_PRESSURE_CONVERSIONS)))}."
    )


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

_TIME_CONVERSIONS = {
    # (from_unit) -> factor to convert to seconds
    "s": 1.0,
    "sec": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "min": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
    "ms": 0.001,
    "millisecond": 0.001,
    "milliseconds": 0.001,
    "us": 1e-6,
    "microsecond": 1e-6,
    "microseconds": 1e-6,
}


def normalize_time(value: Number, unit: str) -> float:
    """Convert a time duration to seconds.

    Parameters
    ----------
    value :
        Numeric time value.
    unit :
        Unit string: ``"s"``, ``"min"``, ``"h"``, ``"ms"``, ``"us"``
        (case-insensitive; also accepts ``"seconds"``, ``"minutes"``,
        ``"hours"``, etc.).

    Returns
    -------
    float
        Time in seconds.

    Raises
    ------
    ValueError
        If *unit* is not recognised.

    Examples
    --------
    >>> normalize_time(1, "h")
    3600.0
    >>> normalize_time(30, "min")
    1800.0
    """
    u_lower = unit.strip().lower()

    for key, factor in _TIME_CONVERSIONS.items():
        if key.lower() == u_lower:
            return float(value) * factor

    raise ValueError(
        f"Unknown time unit: {unit!r}. "
        f"Supported: s, min, h, ms, us (and long forms)."
    )
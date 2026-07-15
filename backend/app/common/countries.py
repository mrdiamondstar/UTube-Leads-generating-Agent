"""ISO 3166-1 alpha-2 code -> human-readable country name.

Uses pycountry for full coverage, with a couple of friendlier short names.
"""
from __future__ import annotations

import pycountry

# Prefer these shorter/common names over pycountry's official long form.
_OVERRIDES = {
    "GB": "United Kingdom",
    "US": "United States",
    "KR": "South Korea",
    "RU": "Russia",
    "TW": "Taiwan",
    "VN": "Vietnam",
    "IR": "Iran",
    "BO": "Bolivia",
    "VE": "Venezuela",
}


def country_name(code: str | None) -> str | None:
    if not code:
        return None
    code = code.strip().upper()
    if code in _OVERRIDES:
        return _OVERRIDES[code]
    try:
        match = pycountry.countries.get(alpha_2=code)
        if match:
            return getattr(match, "common_name", None) or match.name
    except (KeyError, AttributeError):
        pass
    return code  # fall back to the raw code if unknown

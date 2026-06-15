from __future__ import annotations

from typing import Any


def _map_names_by_category(map_results: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in map_results:
        category = str(item.get("category") or "unknown")
        grouped.setdefault(category, []).append(str(item.get("name") or "Map"))
    return grouped


def _changed_percent(item: dict[str, Any]) -> float:
    diff = item.get("diff") or {}
    return float(diff.get("changed_percent") or 0.0)


def _confidence(category: str, grouped: dict[str, list[str]], has_modified: bool) -> str:
    supporting = 0
    for key in ("torque", "boost", "fuel", "air_fuel", "timing", "rail_pressure"):
        if grouped.get(key):
            supporting += 1

    if category == "torque" and grouped.get("fuel") and grouped.get("boost"):
        return "high" if supporting >= 4 else "medium"
    if category == "boost" and grouped.get("air_fuel") and grouped.get("fuel"):
        return "high" if has_modified else "medium"
    if supporting >= 3:
        return "medium"
    return "low"


def _risk(category: str, requested_percent: str, grouped: dict[str, list[str]]) -> str:
    if category in {"timing", "rail_pressure"}:
        return "high"
    if category == "boost" and not grouped.get("air_fuel"):
        return "medium-high"
    if category == "fuel" and not grouped.get("air_fuel"):
        return "medium-high"
    return "medium"


def generate_power_recommendations(
    map_results: list[dict[str, Any]],
    has_modified: bool,
) -> list[dict[str, Any]]:
    grouped = _map_names_by_category(map_results)
    recommendations: list[dict[str, Any]] = []

    templates = {
        "torque": {
            "title": "Torque request / limiter",
            "target_zone": "mid-high load, 2200-3800 rpm",
            "suggested_change": "+6% .. +12%",
            "reason": "Pentru un Stage 1 conservator, cuplul cerut si limiterele trebuie ridicate coerent in zona de sarcina mare.",
            "checks": [
                "verifica limita transmisiei",
                "coreleaza cu smoke limiter si boost target",
                "evita cresterea agresiva la rpm foarte jos",
            ],
        },
        "boost": {
            "title": "Boost target",
            "target_zone": "high load peste 2400 rpm",
            "suggested_change": "+3% .. +7%",
            "reason": "O crestere moderata de boost poate sustine combustibil suplimentar si reduce fum, daca turbo si limiterele permit.",
            "checks": [
                "verifica boost limiter si turbo duty",
                "urmareste EGT si presiune turbo reala",
                "nu creste boost fara aer/fuel coherence",
            ],
        },
        "fuel": {
            "title": "Fuel quantity / injection duration",
            "target_zone": "high load, zona de cuplu maxim",
            "suggested_change": "+4% .. +10%",
            "reason": "Puterea suplimentara cere combustibil suplimentar, dar cresterea trebuie limitata de aer disponibil si fum.",
            "checks": [
                "coreleaza cu boost si smoke/lambda",
                "verifica durata injectiei la rpm mare",
                "evita valori care cresc EGT excesiv",
            ],
        },
        "air_fuel": {
            "title": "Smoke / lambda limiter",
            "target_zone": "high load",
            "suggested_change": "ajustare pentru coerenta cu fuel si boost",
            "reason": "Limiterul aer/combustibil trebuie sa permita cererea noua fara fum excesiv sau amestec periculos.",
            "checks": [
                "verifica lambda/AFR tinta",
                "nu relaxa limiterul fara boost suficient",
                "valideaza cu loguri de fum/EGT",
            ],
        },
        "timing": {
            "title": "SOI / timing",
            "target_zone": "doar zone validate prin loguri",
            "suggested_change": "pas mic, de regula sub 1-2 grade",
            "reason": "Timing-ul poate imbunatati eficienta, dar riscul de zgomot, EGT si presiune cilindru este ridicat.",
            "checks": [
                "modifica doar dupa ce fuel/boost sunt coerente",
                "valideaza zgomot si EGT",
                "nu aplica offset global agresiv",
            ],
        },
        "rail_pressure": {
            "title": "Rail pressure",
            "target_zone": "high load",
            "suggested_change": "+2% .. +5%",
            "reason": "Rail pressure poate sustine atomizarea si durata injectiei, dar solicita pompa si injectoarele.",
            "checks": [
                "verifica limite pompa/injectoare",
                "nu depasi limiterele de siguranta",
                "urmareste rail actual vs target in loguri",
            ],
        },
    }

    for category, template in templates.items():
        category_maps = [
            item for item in map_results if str(item.get("category") or "unknown") == category
        ]
        if not category_maps:
            continue

        max_changed = max((_changed_percent(item) for item in category_maps), default=0.0)
        recommendations.append(
            {
                "category": category,
                "title": template["title"],
                "maps": [str(item.get("name") or "Map") for item in category_maps[:5]],
                "target_zone": template["target_zone"],
                "suggested_change": template["suggested_change"],
                "reason": template["reason"],
                "checks": template["checks"],
                "risk": _risk(category, template["suggested_change"], grouped),
                "confidence": _confidence(category, grouped, has_modified),
                "current_change_percent": round(max_changed, 2),
                "mode": "review_existing_change" if has_modified and max_changed > 0 else "suggest_next_change",
            }
        )

    if not recommendations:
        return [
            {
                "category": "definitions",
                "title": "Map definitions required",
                "maps": [],
                "target_zone": "-",
                "suggested_change": "incarca definitii pentru torque, boost, fuel, lambda/smoke, SOI sau rail pressure",
                "reason": "Fisierul binar brut nu spune sigur care bytes reprezinta harti de calibrare.",
                "checks": [
                    "exporta map list din WinOLS ca CSV/JSON",
                    "adauga address, rows, columns, data_type, factor si category",
                ],
                "risk": "unknown",
                "confidence": "low",
                "current_change_percent": 0.0,
                "mode": "missing_context",
            }
        ]

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        recommendations,
        key=lambda item: (order.get(item["confidence"], 3), item["risk"]),
    )

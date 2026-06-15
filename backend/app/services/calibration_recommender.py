from __future__ import annotations

from typing import Any


POWER_CATEGORIES = (
    "torque",
    "fuel",
    "boost",
    "air_fuel",
    "timing",
    "rail_pressure",
    "limiter",
)


CATEGORY_RULES: dict[str, dict[str, Any]] = {
    "torque": {
        "title": "Torque request / torque limiters",
        "target_zone": "mid-high load, zona de cuplu maxim",
        "suggested_change": "+6% .. +12% conservator, doar pe zonele de sarcina mare",
        "benefits": [
            "permite ECU-ului sa ceara mai mult cuplu acolo unde hardware-ul poate sustine",
            "ridica plafonul pentru fuel si boost fara sa elimine protectii global",
        ],
        "risks": [
            "daca este crescut peste limita transmisiei poate produce solicitare mecanica",
            "daca fuel/boost/lambda nu sunt coerente, cresterea poate avea beneficiu limitat",
        ],
        "actions": [
            "ridica gradual cererea/limiterele doar in zona de load ridicat",
            "pastreaza zona de rpm jos mai conservatoare",
            "coreleaza cu fuel quantity, boost target si smoke/lambda limiter",
        ],
        "dependencies": ["fuel", "boost", "air_fuel"],
        "checks": [
            "log torque requested vs torque actual/limit",
            "verifica limita transmisiei si protectiile termice",
            "valideaza ca boost si lambda sustin cresterea de cuplu",
        ],
        "benefit_level": "high",
        "base_risk": "medium",
    },
    "fuel": {
        "title": "Fuel quantity / injection duration",
        "target_zone": "high load, zona de cuplu maxim si putere mare",
        "suggested_change": "+4% .. +10% in pasi mici, limitat de aer disponibil",
        "benefits": [
            "poate creste cuplul si puterea cand exista suficient aer",
            "ajuta la sustinerea cererii de torque dupa ridicarea limiterelor",
        ],
        "risks": [
            "fuel fara boost/lambda coerente poate creste fum si EGT",
            "durata prea mare la rpm ridicat poate impinge injectia in zona ineficienta",
        ],
        "actions": [
            "creste fuel doar in celulele de load ridicat",
            "verifica smoke/lambda limiter in aceeasi zona",
            "controleaza durata injectiei la rpm mare",
        ],
        "dependencies": ["air_fuel", "boost"],
        "checks": [
            "log lambda/AFR, smoke si EGT",
            "verifica injection duration si rail actual vs target",
            "compara cresterea fuel cu cresterea boost",
        ],
        "benefit_level": "high",
        "base_risk": "medium-high",
    },
    "boost": {
        "title": "Boost target / boost limiters",
        "target_zone": "high load peste zona de spool stabil",
        "suggested_change": "+3% .. +7% daca turbo si limiterele permit",
        "benefits": [
            "sustine combustibil suplimentar cu mai mult aer",
            "poate reduce fum cand fuel este crescut corect",
        ],
        "risks": [
            "boost prea mare poate suprasolicita turbo si creste temperatura admisiei",
            "fara limitere si duty coerente poate produce overshoot",
        ],
        "actions": [
            "ajusteaza target si limiter impreuna, nu doar una dintre harti",
            "evita cresterea agresiva in spool si la rpm foarte jos",
            "coreleaza cu fuel si smoke/lambda limiter",
        ],
        "dependencies": ["air_fuel", "fuel"],
        "checks": [
            "log boost target vs boost actual",
            "urmareste turbo duty, IAT si EGT",
            "verifica sa nu existe overshoot in tranzient",
        ],
        "benefit_level": "medium-high",
        "base_risk": "medium-high",
    },
    "air_fuel": {
        "title": "Smoke / lambda / AFR limiter",
        "target_zone": "high load, aceeasi zona cu fuel si boost",
        "suggested_change": "ajustare pentru coerenta, nu relaxare globala",
        "benefits": [
            "permite fuel suplimentar doar unde exista aer suficient",
            "reduce riscul de fum si EGT cand boost/fuel sunt modificate",
        ],
        "risks": [
            "relaxarea excesiva poate permite fum si temperaturi mari",
            "o tinta prea agresiva poate afecta siguranta motorului",
        ],
        "actions": [
            "verifica daca limiterul blocheaza fuel in zonele tintite",
            "ajusteaza doar celulele afectate de fuel/boost",
            "pastreaza protectiile pentru zonele cu aer insuficient",
        ],
        "dependencies": ["fuel", "boost"],
        "checks": [
            "log lambda/AFR real sub sarcina",
            "verifica fum vizual si EGT",
            "compara zona modificata cu fuel si boost",
        ],
        "benefit_level": "medium-high",
        "base_risk": "medium",
    },
    "timing": {
        "title": "SOI / ignition or injection timing",
        "target_zone": "doar zone validate prin loguri",
        "suggested_change": "pasi mici, de regula sub 1-2 grade",
        "benefits": [
            "poate imbunatati eficienta si raspunsul daca fuel/air sunt deja coerente",
            "poate reduce EGT in anumite conditii, dar necesita validare",
        ],
        "risks": [
            "timing agresiv poate creste zgomot, knock sau presiune cilindru",
            "offset global fara loguri poate produce comportament instabil",
        ],
        "actions": [
            "modifica timing doar dupa stabilizarea fuel/boost/lambda",
            "aplica pasi mici in zonele tintite, nu offset global",
            "revino rapid daca apar zgomot, knock sau EGT nefavorabil",
        ],
        "dependencies": ["fuel", "air_fuel"],
        "checks": [
            "log knock/noise, EGT si presiune cilindru unde este posibil",
            "verifica SOI in raport cu durata injectiei",
            "testeaza incremental pe aceeasi zona RPM/load",
        ],
        "benefit_level": "medium",
        "base_risk": "high",
    },
    "rail_pressure": {
        "title": "Rail pressure",
        "target_zone": "high load, unde durata injectiei devine limitativa",
        "suggested_change": "+2% .. +5% daca pompa si injectoarele permit",
        "benefits": [
            "poate sustine atomizarea si reduce durata injectiei",
            "ajuta cand fuel suplimentar este limitat de durata",
        ],
        "risks": [
            "cresterea forteaza pompa, rampa si injectoarele",
            "poate introduce erori daca limiterele de presiune nu sunt coerente",
        ],
        "actions": [
            "ridica target si limiterele asociate coerent",
            "nu depasi protectiile hardware cunoscute",
            "foloseste doar daca fuel duration are nevoie de suport",
        ],
        "dependencies": ["fuel"],
        "checks": [
            "log rail target vs rail actual",
            "verifica duty pompa si erori de presiune",
            "urmareste EGT si comportamentul injectiei",
        ],
        "benefit_level": "medium",
        "base_risk": "high",
    },
    "limiter": {
        "title": "RPM / speed / protection limiters",
        "target_zone": "doar daca hardware-ul si transmisia permit",
        "suggested_change": "revizuire controlata, fara eliminare globala",
        "benefits": [
            "poate elimina un plafon care limiteaza strategia Stage 1",
            "poate extinde zona utila daca motorul inca produce putere sigur",
        ],
        "risks": [
            "nu creste singur puterea si poate elimina protectii importante",
            "cresterea rpm/speed poate solicita motorul si transmisia",
        ],
        "actions": [
            "identifica daca limiterul chiar blocheaza puterea sau doar protejeaza",
            "pastreaza protectiile termice si mecanice",
            "modifica incremental si valideaza prin loguri",
        ],
        "dependencies": ["torque", "fuel"],
        "checks": [
            "verifica limita mecanica motor/transmisie",
            "log temperaturi si protectii active",
            "confirma ca harta modificata este limiterul corect",
        ],
        "benefit_level": "low-medium",
        "base_risk": "medium-high",
    },
}


def _category(item: dict[str, Any]) -> str:
    return str(item.get("category") or "unknown")


def _unique_strings(values: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        if limit is not None and len(unique) >= limit:
            break
    return unique


def _map_names_by_category(map_results: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in map_results:
        category = _category(item)
        names = grouped.setdefault(category, [])
        name = str(item.get("name") or "Map")
        if name not in names:
            names.append(name)
    return grouped


def _maps_for_category(
    map_results: list[dict[str, Any]],
    category: str,
) -> list[dict[str, Any]]:
    return [item for item in map_results if _category(item) == category]


def _changed_percent(item: dict[str, Any]) -> float:
    diff = item.get("diff") or {}
    return float(diff.get("changed_percent") or 0.0)


def _max_abs_delta(item: dict[str, Any]) -> float:
    diff = item.get("diff") or {}
    return float(diff.get("max_abs_delta") or 0.0)


def _direction(item: dict[str, Any]) -> str:
    diff = item.get("diff") or {}
    return str(diff.get("direction") or "unchanged")


def _zone_text(item: dict[str, Any]) -> str:
    zones = item.get("affected_zone") or []
    if not isinstance(zones, list):
        return ""
    parts: list[str] = []
    for zone in zones[:3]:
        if not isinstance(zone, dict):
            continue
        label = zone.get("label") or "axis"
        minimum = zone.get("min")
        maximum = zone.get("max")
        if minimum is None or maximum is None:
            continue
        parts.append(f"{label} {minimum}-{maximum}")
    return ", ".join(parts)


def _dominant_zone(category_maps: list[dict[str, Any]]) -> str:
    changed = sorted(category_maps, key=_changed_percent, reverse=True)
    for item in changed:
        zone = _zone_text(item)
        if zone:
            return zone
    return ""


def _changed_maps(category_maps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in category_maps if _changed_percent(item) > 0.0]


def _missing_dependencies(
    category: str,
    grouped: dict[str, list[str]],
    is_turbo: bool | None,
) -> list[str]:
    rule = CATEGORY_RULES.get(category, {})
    missing: list[str] = []
    for dependency in rule.get("dependencies") or []:
        if dependency == "boost" and is_turbo is False:
            continue
        if not grouped.get(dependency):
            missing.append(dependency)
    return missing


def _unchanged_dependencies(
    category: str,
    grouped: dict[str, list[str]],
    changed_categories: set[str],
    is_turbo: bool | None,
) -> list[str]:
    rule = CATEGORY_RULES.get(category, {})
    unchanged: list[str] = []
    for dependency in rule.get("dependencies") or []:
        if dependency == "boost" and is_turbo is False:
            continue
        if grouped.get(dependency) and dependency not in changed_categories:
            unchanged.append(dependency)
    return unchanged


def _confidence(
    category: str,
    grouped: dict[str, list[str]],
    has_modified: bool,
    changed: bool,
    is_turbo: bool | None,
) -> str:
    missing = _missing_dependencies(category, grouped, is_turbo)
    if missing:
        return "low"
    supporting = sum(1 for key in POWER_CATEGORIES if grouped.get(key))
    if has_modified and changed and supporting >= 4:
        return "high"
    if supporting >= 3:
        return "medium"
    return "low"


def _risk(
    category: str,
    grouped: dict[str, list[str]],
    max_changed: float,
    max_delta: float,
    is_turbo: bool | None,
) -> str:
    base = str(CATEGORY_RULES.get(category, {}).get("base_risk") or "medium")
    missing = _missing_dependencies(category, grouped, is_turbo)
    if category in {"timing", "rail_pressure"}:
        return "high"
    if missing and base == "medium":
        return "medium-high"
    if max_changed >= 35 or max_delta >= 20:
        return "high"
    if max_changed >= 15 and base == "medium":
        return "medium-high"
    return base


def _priority_score(
    category: str,
    risk: str,
    confidence: str,
    changed: bool,
    missing_dependencies: list[str],
) -> int:
    score = 0
    if changed:
        score += 40
    if category in {"torque", "fuel", "boost", "air_fuel"}:
        score += 20
    if risk in {"high", "medium-high"}:
        score += 15
    if confidence == "high":
        score += 10
    if missing_dependencies:
        score += 8
    return score


def _mode_label(has_modified: bool, changed: bool) -> tuple[str, str]:
    if not has_modified:
        return "suggest_next_change", "Original-only planning"
    if changed:
        return "review_existing_change", "Review tuned change"
    return "review_supporting_map", "Supporting map check"


def _observation_lines(
    category: str,
    category_maps: list[dict[str, Any]],
    has_modified: bool,
    changed_maps: list[dict[str, Any]],
    zone: str,
    max_changed: float,
    max_delta: float,
    unchanged_dependencies: list[str],
) -> list[str]:
    observations = [
        f"Am identificat {len(category_maps)} harti in categoria {category}.",
    ]
    if has_modified:
        if changed_maps:
            direction = _direction(changed_maps[0])
            observations.append(
                f"In tuned/current, {len(changed_maps)} harti au modificari; maxim {round(max_changed, 2)}% celule schimbate, directie {direction}."
            )
            if max_delta:
                observations.append(f"Delta maxim observat: {round(max_delta, 4)}.")
            if zone:
                observations.append(f"Zona dominanta afectata: {zone}.")
        else:
            observations.append(
                "Categoria exista in map pack, dar nu pare modificata in fisierul tuned/current."
            )
        if unchanged_dependencies:
            observations.append(
                "Harti suport prezente, dar nemodificate: "
                + ", ".join(unchanged_dependencies)
                + "."
            )
    else:
        observations.append(
            "Nu exista fisier tuned/current; recomandarea este orientativa si porneste din hartile disponibile in original."
        )
    return observations


def _reason(
    title: str,
    has_modified: bool,
    changed: bool,
    missing_dependencies: list[str],
    unchanged_dependencies: list[str],
) -> str:
    if not has_modified:
        reason = (
            f"{title} este o zona candidata pentru Stage 1, dar fara fisier tuned "
            "nu pot confirma ce a fost modificat deja."
        )
    elif changed:
        reason = (
            f"{title} a fost modificata in tuned/current; recomandarea este un review "
            "de coerenta, risc si validare."
        )
    else:
        reason = (
            f"{title} nu pare modificata, dar poate fi necesara ca harta suport "
            "pentru modificarile din celelalte categorii."
        )

    if missing_dependencies:
        reason += " Lipsesc harti suport din definitii: " + ", ".join(missing_dependencies) + "."
    elif unchanged_dependencies and has_modified:
        reason += " Verifica daca hartile suport nemodificate limiteaza rezultatul."
    return reason


def _context_note(
    category: str,
    fuel_type: str | None,
    is_turbo: bool | None,
) -> str:
    fuel = (fuel_type or "").lower()
    if category == "boost" and is_turbo is False:
        return "Motorul este marcat aspirat, deci boost nu este tratat ca dependinta principala."
    if category == "air_fuel" and fuel == "petrol":
        return "Pentru benzina aspirata, categoria air/fuel trebuie interpretata ca model aer/lambda/AFR, nu smoke limiter diesel."
    return ""


def _title_for_context(category: str, fuel_type: str | None) -> str:
    title = str(CATEGORY_RULES[category]["title"])
    if category == "air_fuel" and (fuel_type or "").lower() == "petrol":
        return "Airflow / lambda / AFR model"
    return title


def _recommendation_for_category(
    category: str,
    category_maps: list[dict[str, Any]],
    grouped: dict[str, list[str]],
    changed_categories: set[str],
    has_modified: bool,
    fuel_type: str | None,
    is_turbo: bool | None,
) -> dict[str, Any]:
    rule = CATEGORY_RULES[category]
    changed = _changed_maps(category_maps)
    changed_or_planning = bool(changed) or not has_modified
    max_changed = max((_changed_percent(item) for item in category_maps), default=0.0)
    max_delta = max((_max_abs_delta(item) for item in category_maps), default=0.0)
    zone = _dominant_zone(category_maps)
    missing = _missing_dependencies(category, grouped, is_turbo)
    unchanged = _unchanged_dependencies(category, grouped, changed_categories, is_turbo)
    confidence = _confidence(category, grouped, has_modified, bool(changed), is_turbo)
    risk = _risk(category, grouped, max_changed, max_delta, is_turbo)
    mode, mode_label = _mode_label(has_modified, bool(changed))
    title = _title_for_context(category, fuel_type)

    observations = _observation_lines(
        category=category,
        category_maps=category_maps,
        has_modified=has_modified,
        changed_maps=changed,
        zone=zone,
        max_changed=max_changed,
        max_delta=max_delta,
        unchanged_dependencies=unchanged if changed_or_planning else [],
    )
    context_note = _context_note(category, fuel_type, is_turbo)
    if context_note:
        observations.append(context_note)
    risks = list(rule["risks"])
    if missing:
        risks.append("definitiile nu contin harti suport: " + ", ".join(missing))
    if unchanged and has_modified and changed:
        risks.append(
            "harti suport prezente, dar nemodificate, pot limita beneficiul: "
            + ", ".join(unchanged)
        )

    actions = list(rule["actions"])
    if not has_modified:
        actions.insert(
            0,
            "foloseste recomandarea ca plan de investigatie si confirma adresele in WinOLS",
        )
    elif changed:
        actions.insert(0, "compara zona modificata cu logurile reale inainte de crestere suplimentara")

    priority = _priority_score(category, risk, confidence, bool(changed), missing)

    return {
        "category": category,
        "title": title,
        "maps": _unique_strings(
            [str(item.get("name") or "Map") for item in category_maps],
            limit=6,
        ),
        "target_zone": zone or rule["target_zone"],
        "suggested_change": rule["suggested_change"],
        "reason": _reason(title, has_modified, bool(changed), missing, unchanged),
        "observations": observations,
        "benefits": list(rule["benefits"]),
        "risks": risks,
        "actions": actions,
        "checks": list(rule["checks"]),
        "missing_dependencies": missing,
        "supporting_maps_to_review": unchanged if has_modified and bool(changed) else [],
        "risk": risk,
        "confidence": confidence,
        "benefit_level": rule["benefit_level"],
        "priority": "high" if priority >= 70 else "medium" if priority >= 35 else "low",
        "priority_score": priority,
        "current_change_percent": round(max_changed, 2),
        "current_max_delta": round(max_delta, 4),
        "affected_zone": zone,
        "mode": mode,
        "mode_label": mode_label,
    }


def _supporting_recommendations(
    map_results: list[dict[str, Any]],
    grouped: dict[str, list[str]],
    changed_categories: set[str],
    fuel_type: str | None,
    is_turbo: bool | None,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    triggers = {
        "fuel": ["air_fuel", "boost"],
        "boost": ["air_fuel", "fuel"],
        "torque": ["fuel", "boost", "air_fuel"],
    }
    for changed_category, dependencies in triggers.items():
        if changed_category not in changed_categories:
            continue
        for dependency in dependencies:
            if dependency == "boost" and is_turbo is False:
                continue
            if dependency in changed_categories or not grouped.get(dependency):
                continue
            category_maps = _maps_for_category(map_results, dependency)
            if not category_maps:
                continue
            recommendation = _recommendation_for_category(
                category=dependency,
                category_maps=category_maps,
                grouped=grouped,
                changed_categories=changed_categories,
                has_modified=True,
                fuel_type=fuel_type,
                is_turbo=is_turbo,
            )
            recommendation["reason"] = (
                f"{recommendation['title']} nu pare modificata, dar {changed_category} "
                "a fost modificata. Verifica daca aceasta harta suport limiteaza sau face nesigura schimbarea."
            )
            recommendations.append(recommendation)
    return recommendations


def generate_power_recommendations(
    map_results: list[dict[str, Any]],
    has_modified: bool,
    fuel_type: str | None = None,
    is_turbo: bool | None = None,
) -> list[dict[str, Any]]:
    grouped = _map_names_by_category(map_results)
    changed_categories = {
        _category(item)
        for item in map_results
        if _category(item) in POWER_CATEGORIES and _changed_percent(item) > 0.0
    }
    recommendations: list[dict[str, Any]] = []

    for category in POWER_CATEGORIES:
        category_maps = _maps_for_category(map_results, category)
        if not category_maps:
            continue
        if has_modified and category not in changed_categories:
            continue
        recommendations.append(
            _recommendation_for_category(
                category=category,
                category_maps=category_maps,
                grouped=grouped,
                changed_categories=changed_categories,
                has_modified=has_modified,
                fuel_type=fuel_type,
                is_turbo=is_turbo,
            )
        )

    if has_modified:
        existing_keys = {(item["category"], item["mode"]) for item in recommendations}
        for recommendation in _supporting_recommendations(
            map_results,
            grouped,
            changed_categories,
            fuel_type,
            is_turbo,
        ):
            key = (recommendation["category"], recommendation["mode"])
            if key not in existing_keys:
                recommendations.append(recommendation)
                existing_keys.add(key)

    if not recommendations:
        return [
            {
                "category": "definitions",
                "title": "Map definitions required",
                "maps": [],
                "target_zone": "-",
                "suggested_change": "incarca definitii pentru torque, boost, fuel, lambda/smoke, SOI sau rail pressure",
                "reason": "Fisierul binar brut nu spune sigur care bytes reprezinta harti de calibrare.",
                "observations": [
                    "Nu exista suficiente definitii categorizate pentru recomandari tehnice.",
                ],
                "benefits": [
                    "cu map pack corect, aplicatia poate lega recomandarile de harti reale",
                ],
                "risks": [
                    "fara definitii, orice recomandare pe bytes brut ar fi nesigura",
                ],
                "actions": [
                    "exporta map pack din WinOLS",
                    "adauga address, rows, columns, data_type, factor si category",
                ],
                "checks": [
                    "verifica daca map pack-ul contine torque, boost, fuel, lambda/smoke, timing sau rail pressure",
                ],
                "missing_dependencies": [],
                "supporting_maps_to_review": [],
                "risk": "unknown",
                "confidence": "low",
                "benefit_level": "unknown",
                "priority": "high",
                "priority_score": 100,
                "current_change_percent": 0.0,
                "current_max_delta": 0.0,
                "affected_zone": "",
                "mode": "missing_context",
                "mode_label": "Missing context",
            }
        ]

    confidence_order = {"high": 0, "medium": 1, "low": 2}
    risk_order = {"high": 0, "medium-high": 1, "medium": 2, "low": 3, "unknown": 4}
    return sorted(
        recommendations,
        key=lambda item: (
            -int(item.get("priority_score") or 0),
            confidence_order.get(str(item.get("confidence")), 9),
            risk_order.get(str(item.get("risk")), 9),
        ),
    )

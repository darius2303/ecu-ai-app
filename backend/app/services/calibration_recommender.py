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
        "target_zone": "mid-high load, peak torque area",
        "suggested_change": "+6% .. +12% conservative increase in high-load cells only",
        "benefits": [
            "allows the ECU to request more torque where the hardware can support it",
            "raises the operating ceiling for fuel and air control without globally removing protections",
        ],
        "risks": [
            "excessive torque requests can overstress the drivetrain",
            "if fuel, air and lambda strategy are not coherent, the gain can be limited or unsafe",
        ],
        "actions": [
            "raise torque request and limiters gradually only in high-load areas",
            "keep low-rpm areas more conservative",
            "cross-check fuel quantity, air model/boost target and lambda/smoke limits",
        ],
        "dependencies": ["fuel", "boost", "air_fuel"],
        "checks": [
            "log torque requested vs torque actual/limit",
            "check drivetrain limits and thermal protections",
            "validate that air/boost and lambda support the torque increase",
        ],
        "benefit_level": "high",
        "base_risk": "medium",
    },
    "fuel": {
        "title": "Fuel quantity / injection duration",
        "target_zone": "high load, peak torque and high-power area",
        "suggested_change": "+4% .. +10% in small steps, limited by available air",
        "benefits": [
            "can increase torque and power when enough air is available",
            "supports the increased torque request after limiter changes",
        ],
        "risks": [
            "extra fuel without coherent air/lambda control can increase smoke and EGT",
            "excessive duration at high rpm can push injection into an inefficient window",
        ],
        "actions": [
            "increase fuel only in high-load cells",
            "check lambda/smoke limits in the same operating area",
            "watch injection duration at high rpm",
        ],
        "dependencies": ["air_fuel", "boost"],
        "checks": [
            "log lambda/AFR, smoke and EGT",
            "check injection duration and rail actual vs target",
            "compare fuel increase against the air/boost increase",
        ],
        "benefit_level": "high",
        "base_risk": "medium-high",
    },
    "boost": {
        "title": "Boost target / boost limiters",
        "target_zone": "high load above the stable spool area",
        "suggested_change": "+3% .. +7% if turbocharger and limiters allow it",
        "benefits": [
            "supports additional fuel with more air",
            "can reduce smoke when fuel is increased correctly",
        ],
        "risks": [
            "too much boost can overstress the turbocharger and raise intake temperature",
            "without coherent limiters and duty control, overshoot can occur",
        ],
        "actions": [
            "adjust target and limiters together, not only one map",
            "avoid aggressive increases during spool and very low rpm",
            "cross-check against fuel and lambda/smoke limits",
        ],
        "dependencies": ["air_fuel", "fuel"],
        "checks": [
            "log boost target vs boost actual",
            "watch turbo duty, IAT and EGT",
            "check for transient overshoot",
        ],
        "benefit_level": "medium-high",
        "base_risk": "medium-high",
    },
    "air_fuel": {
        "title": "Smoke / lambda / AFR limiter",
        "target_zone": "high load, same area as fuel and air/boost changes",
        "suggested_change": "coherence adjustment, not a global relaxation",
        "benefits": [
            "allows additional fuel only where enough air is available",
            "reduces smoke and EGT risk when fuel/air are modified",
        ],
        "risks": [
            "excessive relaxation can allow smoke and high temperatures",
            "an overly aggressive target can affect engine safety",
        ],
        "actions": [
            "check whether the limiter blocks fuel in the target zones",
            "adjust only cells affected by fuel/air changes",
            "keep protections active where air is insufficient",
        ],
        "dependencies": ["fuel", "boost"],
        "checks": [
            "log actual lambda/AFR under load",
            "check visible smoke and EGT",
            "compare the modified area with fuel and air/boost changes",
        ],
        "benefit_level": "medium-high",
        "base_risk": "medium",
    },
    "timing": {
        "title": "SOI / ignition or injection timing",
        "target_zone": "only zones validated by logs",
        "suggested_change": "small steps, usually below 1-2 degrees",
        "benefits": [
            "can improve efficiency and response if fuel/air are already coherent",
            "can reduce EGT in some conditions, but requires validation",
        ],
        "risks": [
            "aggressive timing can increase noise, knock or cylinder pressure",
            "global offsets without logs can create unstable behavior",
        ],
        "actions": [
            "change timing only after fuel/air/lambda strategy is stable",
            "apply small steps in target areas, not global offsets",
            "revert quickly if noise, knock or unfavorable EGT appears",
        ],
        "dependencies": ["fuel", "air_fuel"],
        "checks": [
            "log knock/noise, EGT and cylinder pressure where possible",
            "check SOI against injection duration",
            "test incrementally in the same RPM/load area",
        ],
        "benefit_level": "medium",
        "base_risk": "high",
    },
    "rail_pressure": {
        "title": "Rail pressure",
        "target_zone": "high load, where injection duration becomes limiting",
        "suggested_change": "+2% .. +5% if pump and injectors allow it",
        "benefits": [
            "can support atomization and reduce injection duration",
            "helps when additional fuel is limited by duration",
        ],
        "risks": [
            "higher pressure stresses the pump, rail and injectors",
            "can introduce faults if pressure limiters are not coherent",
        ],
        "actions": [
            "raise target and related limiters coherently",
            "do not exceed known hardware protections",
            "use only when fuel duration needs support",
        ],
        "dependencies": ["fuel"],
        "checks": [
            "log rail target vs rail actual",
            "check pump duty and pressure faults",
            "watch EGT and injection behavior",
        ],
        "benefit_level": "medium",
        "base_risk": "high",
    },
    "limiter": {
        "title": "RPM / speed / protection limiters",
        "target_zone": "only if hardware and drivetrain allow it",
        "suggested_change": "controlled revision, no global removal",
        "benefits": [
            "can remove a cap that limits the calibration strategy",
            "can extend the useful range if the engine still makes power safely",
        ],
        "risks": [
            "does not increase power by itself and can remove important protections",
            "higher rpm/speed can stress the engine and drivetrain",
        ],
        "actions": [
            "identify whether the limiter blocks power or only protects the system",
            "keep thermal and mechanical protections",
            "change incrementally and validate with logs",
        ],
        "dependencies": ["torque", "fuel"],
        "checks": [
            "check engine/drivetrain mechanical limits",
            "log temperatures and active protections",
            "confirm that the changed map is the intended limiter",
        ],
        "benefit_level": "low-medium",
        "base_risk": "medium-high",
    },
}


def _category(item: dict[str, Any]) -> str:
    """Returneaza categoria tehnica a hartii sau unknown."""
    return str(item.get("category") or "unknown")


def _unique_strings(values: list[str], limit: int | None = None) -> list[str]:
    """Pastreaza valori unice in ordinea in care apar."""
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
    """Grupeaza numele hartilor dupa categorie pentru verificarea dependentelor."""
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
    """Filtreaza hartile care apartin unei categorii."""
    return [item for item in map_results if _category(item) == category]


def _changed_percent(item: dict[str, Any]) -> float:
    """Citeste procentul de celule modificate pentru o harta."""
    diff = item.get("diff") or {}
    return float(diff.get("changed_percent") or 0.0)


def _max_abs_delta(item: dict[str, Any]) -> float:
    diff = item.get("diff") or {}
    return float(diff.get("max_abs_delta") or 0.0)


def _direction(item: dict[str, Any]) -> str:
    diff = item.get("diff") or {}
    return str(diff.get("direction") or "unchanged")


def _zone_text(item: dict[str, Any]) -> str:
    """Formateaza zona afectata a unei harti pentru textul recomandarii."""
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
    """Alege zona cea mai relevanta din categoria analizata."""
    changed = sorted(category_maps, key=_changed_percent, reverse=True)
    for item in changed:
        zone = _zone_text(item)
        if zone:
            return zone
    return ""


def _changed_maps(category_maps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Returneaza doar hartile care chiar s-au schimbat."""
    return [item for item in category_maps if _changed_percent(item) > 0.0]


def _missing_dependencies(
    category: str,
    grouped: dict[str, list[str]],
    is_turbo: bool | None,
) -> list[str]:
    """Identifica hartile suport care lipsesc din map pack."""
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
    """Identifica hartile suport prezente, dar nemodificate."""
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
    """Acorda increderea recomandarii in functie de contextul disponibil."""
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
    """Stabileste nivelul de risc tehnic pentru categoria analizata."""
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
    """Calculeaza prioritatea folosita pentru ordonarea recomandarilor."""
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
    """Alege modul recomandarii: planificare, review sau harta suport."""
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
    """Construieste observatiile scurte care explica recomandarea."""
    observations = [
        f"Found {len(category_maps)} maps in the {category} category.",
    ]
    if has_modified:
        if changed_maps:
            direction = _direction(changed_maps[0])
            observations.append(
                f"In tuned/current, {len(changed_maps)} maps changed; maximum {round(max_changed, 2)}% changed cells, direction {direction}."
            )
            if max_delta:
                observations.append(f"Maximum observed delta: {round(max_delta, 4)}.")
            if zone:
                observations.append(f"Dominant affected zone: {zone}.")
        else:
            observations.append(
                "This category exists in the map pack, but it does not appear changed in tuned/current."
            )
        if unchanged_dependencies:
            observations.append(
                "Supporting maps are present but unchanged: "
                + ", ".join(unchanged_dependencies)
                + "."
            )
    else:
        observations.append(
            "No tuned/current file was provided; this recommendation is a planning hint based on the original maps."
        )
    return observations


def _reason(
    title: str,
    has_modified: bool,
    changed: bool,
    missing_dependencies: list[str],
    unchanged_dependencies: list[str],
) -> str:
    """Construieste motivatia principala a recomandarii."""
    if not has_modified:
        reason = (
            f"{title} is a candidate tuning area, but without a tuned file "
            "the app cannot confirm what has already been changed."
        )
    elif changed:
        reason = (
            f"{title} changed in tuned/current; this is a coherence, risk and validation review."
        )
    else:
        reason = (
            f"{title} does not appear changed, but it may be needed as a supporting map "
            "for changes in other categories."
        )

    if missing_dependencies:
        reason += " Supporting maps are missing from definitions: " + ", ".join(missing_dependencies) + "."
    elif unchanged_dependencies and has_modified:
        reason += " Check whether unchanged supporting maps are limiting the result."
    return reason


def _context_note(
    category: str,
    fuel_type: str | None,
    is_turbo: bool | None,
) -> str:
    """Adauga note speciale in functie de combustibil si tipul de motor."""
    fuel = (fuel_type or "").lower()
    if category == "boost" and is_turbo is False:
        return "The engine is marked naturally aspirated, so boost is not treated as a primary dependency."
    if category == "air_fuel" and fuel == "petrol":
        return "For petrol engines, air/fuel should be interpreted as airflow/lambda/AFR modeling rather than a diesel smoke limiter."
    return ""


def _title_for_context(category: str, fuel_type: str | None) -> str:
    """Ajusteaza titlul pentru cazuri unde aceeasi categorie are interpretari diferite."""
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
    """Construieste recomandarea completa pentru o categorie de harti."""
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
        risks.append("definitions do not include supporting maps: " + ", ".join(missing))
    if unchanged and has_modified and changed:
        risks.append(
            "supporting maps are present but unchanged and may limit the benefit: "
            + ", ".join(unchanged)
        )

    actions = list(rule["actions"])
    if not has_modified:
        actions.insert(
            0,
            "use this recommendation as an investigation plan and confirm addresses in WinOLS",
        )
    elif changed:
        actions.insert(0, "compare the modified zone with real logs before increasing further")

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
    """Adauga recomandari pentru harti suport care pot limita o modificare."""
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
                f"{recommendation['title']} does not appear changed, but {changed_category} "
                "was changed. Check whether this supporting map limits or makes the change unsafe."
            )
            recommendations.append(recommendation)
    return recommendations


def generate_power_recommendations(
    map_results: list[dict[str, Any]],
    has_modified: bool,
    fuel_type: str | None = None,
    is_turbo: bool | None = None,
) -> list[dict[str, Any]]:
    """Genereaza recomandarile tehnice finale pentru hartile de putere."""
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
                "suggested_change": "load definitions for torque, boost, fuel, lambda/smoke, SOI or rail pressure",
                "reason": "A raw binary file cannot reliably identify which bytes represent calibration maps.",
                "observations": [
                    "There are not enough categorized definitions for technical recommendations.",
                ],
                "benefits": [
                    "with a correct map pack, the app can link recommendations to real maps",
                ],
                "risks": [
                    "without definitions, recommendations on raw bytes would be unsafe",
                ],
                "actions": [
                    "export a map pack from WinOLS",
                    "add address, rows, columns, data_type, factor and category",
                ],
                "checks": [
                    "check whether the map pack contains torque, boost, fuel, lambda/smoke, timing or rail pressure",
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

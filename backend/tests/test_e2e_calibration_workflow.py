import base64
import json
import struct
from datetime import datetime
from html import escape
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
E2E_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "generated" / "e2e" / "e2e_01_complete_analysis"


def _uploaded(file_name: str, content: bytes) -> dict:
    return {
        "file_name": file_name,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


def _original_bytes() -> bytes:
    return struct.pack(
        ">HHHHHHHHHHHH",
        100,
        200,
        300,
        400,
        120,
        180,
        260,
        320,
        900,
        950,
        1000,
        1050,
    )


def _stage1_bytes() -> bytes:
    return struct.pack(
        ">HHHHHHHHHHHH",
        100,
        240,
        330,
        460,
        140,
        210,
        300,
        360,
        920,
        980,
        1060,
        1120,
    )


def _definitions_csv() -> bytes:
    return (
        "name,address,rows,columns,data_type,byte_order,factor,offset,unit,category\n"
        "Torque request,0,2,2,u16,big,0.1,0,Nm,torque\n"
        "Injection base map,8,2,2,u16,big,0.1,0,mg,fuel\n"
        "Airflow mass through throttle valve,16,2,2,u16,big,0.1,0,kg/h,air_fuel\n"
    ).encode()


def _complete_stage1_payload() -> dict:
    return {
        "original_file": _uploaded("original.bin", _original_bytes()),
        "modified_file": _uploaded("stage1.bin", _stage1_bytes()),
        "definitions_file": _uploaded("maps.csv", _definitions_csv()),
        "engine_displacement": 1.0,
        "fuel_type": "petrol",
        "is_turbo": False,
        "stock_hp": 101,
    }


def _original_only_payload() -> dict:
    return {
        "original_file": _uploaded("original.bin", _original_bytes()),
        "definitions_file": _uploaded("maps.csv", _definitions_csv()),
        "engine_displacement": 1.0,
        "fuel_type": "petrol",
        "is_turbo": False,
        "stock_hp": 101,
    }


def _missing_definitions_payload() -> dict:
    return {
        "original_file": _uploaded("original.bin", _original_bytes()),
        "modified_file": _uploaded("stage1.bin", _stage1_bytes()),
        "engine_displacement": 1.0,
        "fuel_type": "petrol",
        "is_turbo": False,
        "stock_hp": 101,
    }


def _invalid_base64_payload() -> dict:
    return {
        "original_file": {
            "file_name": "broken.bin",
            "content_base64": "not-valid-base64",
        },
        "definitions_file": _uploaded("maps.csv", _definitions_csv()),
        "engine_displacement": 1.0,
        "fuel_type": "petrol",
        "is_turbo": False,
        "stock_hp": 101,
    }


def _metric_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _html_list(items: list[str]) -> str:
    if not items:
        return "<li>No items reported.</li>"
    return "".join(f"<li>{escape(str(item))}</li>" for item in items)


def _generate_visual_evidence_html(analysis: dict, summary: dict) -> str:
    analysis_summary = analysis.get("summary", {})
    binary_diff = analysis.get("binary_diff", {})
    verdict = analysis.get("analysis_verdict", {})
    power = analysis.get("power_estimate", {})
    maps = analysis.get("maps") or []
    recommendations = analysis.get("recommendations") or []

    checks = "".join(
        f"""
        <article class="check">
          <span class="status">PASS</span>
          <div>
            <strong>{escape(item["step"])}</strong>
            <p>{escape(item["evidence"])}</p>
          </div>
        </article>
        """
        for item in summary["checks"]
    )

    map_rows = "".join(
        f"""
        <tr>
          <td>{escape(item.get("name", "-"))}</td>
          <td>{escape(item.get("category", "-"))}</td>
          <td>{_metric_value(item.get("changed_percent"))}%</td>
          <td>{_metric_value(item.get("delta_max"))}</td>
        </tr>
        """
        for item in maps
    )

    recommendation_cards = "".join(
        f"""
        <article class="recommendation">
          <div class="recommendation-head">
            <strong>{escape(item.get("title", "-"))}</strong>
            <span>{escape(item.get("priority", "unknown"))} priority</span>
          </div>
          <p>{escape(item.get("message", ""))}</p>
          <div class="split">
            <div>
              <h4>Recommended actions</h4>
              <ul>{_html_list(item.get("actions", []))}</ul>
            </div>
            <div>
              <h4>Risks</h4>
              <ul>{_html_list(item.get("risks", []))}</ul>
            </div>
          </div>
        </article>
        """
        for item in recommendations[:3]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>E2E-01 Visual Evidence - ECU Calibration Analyzer</title>
  <style>
    :root {{
      --ink: #101827;
      --muted: #5f6f89;
      --line: #dbe4f0;
      --panel: #f6f9fc;
      --blue: #3159c8;
      --teal: #087b74;
      --green: #0a7b5f;
      --amber: #b85c00;
      --red: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      color: var(--ink);
      background: #edf2f7;
    }}
    main {{
      width: min(1180px, calc(100vw - 48px));
      margin: 32px auto;
      display: grid;
      gap: 20px;
    }}
    header {{
      background: linear-gradient(120deg, #0f172a, #2448a8);
      color: white;
      border-radius: 18px;
      padding: 28px 32px;
      box-shadow: 0 18px 40px rgba(15, 23, 42, .18);
    }}
    header h1 {{ margin: 0 0 8px; font-size: 34px; }}
    header p {{ margin: 0; color: #dce8ff; }}
    section {{
      background: white;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 22px;
    }}
    h2 {{ margin: 0 0 16px; font-size: 22px; }}
    h3 {{ margin: 0 0 10px; font-size: 17px; }}
    h4 {{ margin: 0 0 8px; color: var(--teal); }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      background: var(--panel);
    }}
    .label {{ color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: 12px; letter-spacing: .04em; }}
    .value {{ margin-top: 8px; font-size: 25px; font-weight: 800; }}
    .checks {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
    .check {{ display: flex; gap: 12px; align-items: flex-start; border: 1px solid #cde7dc; background: #f1fbf7; border-radius: 12px; padding: 12px; }}
    .check p {{ margin: 4px 0 0; color: var(--muted); }}
    .status {{ color: white; background: var(--green); border-radius: 999px; padding: 5px 8px; font-size: 11px; font-weight: 800; }}
    .verdict {{ border-color: #f5c9c9; background: #fff5f5; }}
    .verdict .value {{ color: var(--red); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .recommendations {{ display: grid; gap: 14px; }}
    .recommendation {{ border: 1px solid #f1caa8; border-radius: 14px; padding: 16px; background: #fffaf5; }}
    .recommendation-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .recommendation-head span {{ border: 1px solid #ffd39b; border-radius: 999px; color: var(--amber); padding: 5px 10px; font-weight: 800; }}
    .recommendation p {{ color: #31415a; }}
    .split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    ul {{ margin: 0; padding-left: 20px; color: #31415a; }}
    .artifact-links {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    a {{ color: var(--blue); font-weight: 800; text-decoration: none; }}
    @media print {{
      body {{ background: white; }}
      main {{ width: 100%; margin: 0; }}
      section, header {{ box-shadow: none; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>E2E-01 Visual Evidence</h1>
      <p>Complete calibration workflow: original ECU + tuned/current + map pack + analysis + PDF report.</p>
    </header>

    <section>
      <h2>Scenario status</h2>
      <div class="checks">{checks}</div>
    </section>

    <section>
      <h2>Analysis snapshot</h2>
      <div class="grid">
        <div class="card"><div class="label">Maps extracted</div><div class="value">{_metric_value(analysis_summary.get("maps_extracted"))}</div></div>
        <div class="card"><div class="label">Maps changed</div><div class="value">{_metric_value(analysis_summary.get("maps_changed"))}</div></div>
        <div class="card"><div class="label">Binary changed</div><div class="value">{_metric_value(binary_diff.get("changed_percent"))}%</div></div>
        <div class="card verdict"><div class="label">Verdict</div><div class="value">{escape(verdict.get("title", "-"))}</div></div>
        <div class="card"><div class="label">Estimated HP</div><div class="value">{_metric_value(power.get("estimated_hp_after_stage1"))}</div></div>
        <div class="card"><div class="label">Power gain</div><div class="value">{_metric_value(power.get("stage1_gain_percent"))}%</div></div>
      </div>
    </section>

    <section>
      <h2>Changed maps</h2>
      <table>
        <thead><tr><th>Map</th><th>Category</th><th>Changed cells</th><th>Max delta</th></tr></thead>
        <tbody>{map_rows}</tbody>
      </table>
    </section>

    <section>
      <h2>Recommendation evidence</h2>
      <div class="recommendations">{recommendation_cards}</div>
    </section>

    <section>
      <h2>Generated artifacts</h2>
      <div class="artifact-links">
        <a href="analysis.json">analysis.json</a>
        <a href="e2e_summary.json">e2e_summary.json</a>
        <a href="calibration_tuner_report.pdf">calibration_tuner_report.pdf</a>
        <a href="visual_summary.svg">visual_summary.svg</a>
      </div>
    </section>
  </main>
</body>
</html>
"""


def _generate_visual_summary_svg(analysis: dict) -> str:
    analysis_summary = analysis.get("summary", {})
    binary_diff = analysis.get("binary_diff", {})
    verdict = analysis.get("analysis_verdict", {})
    recommendations = analysis.get("recommendations") or []
    first_recommendation = recommendations[0] if recommendations else {}

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
  <defs>
    <linearGradient id="hero" x1="0" x2="1">
      <stop offset="0" stop-color="#0f172a"/>
      <stop offset="1" stop-color="#2448a8"/>
    </linearGradient>
    <style>
      .title {{ font: 800 38px 'Segoe UI', Arial, sans-serif; fill: #fff; }}
      .subtitle {{ font: 500 17px 'Segoe UI', Arial, sans-serif; fill: #dbeafe; }}
      .h2 {{ font: 800 24px 'Segoe UI', Arial, sans-serif; fill: #101827; }}
      .label {{ font: 700 14px 'Segoe UI', Arial, sans-serif; fill: #64748b; }}
      .value {{ font: 800 31px 'Segoe UI', Arial, sans-serif; fill: #101827; }}
      .small {{ font: 500 15px 'Segoe UI', Arial, sans-serif; fill: #334155; }}
      .chip {{ font: 800 14px 'Segoe UI', Arial, sans-serif; fill: #0f766e; }}
    </style>
  </defs>
  <rect width="1200" height="720" fill="#eef3f8"/>
  <rect x="48" y="38" width="1104" height="120" rx="24" fill="url(#hero)"/>
  <text x="84" y="92" class="title">E2E-01 Visual Evidence</text>
  <text x="84" y="124" class="subtitle">original ECU + tuned/current + map pack - recommendations - PDF report</text>

  <rect x="68" y="202" width="320" height="130" rx="18" fill="#fff" stroke="#dbe4f0" stroke-width="2"/>
  <text x="96" y="246" class="label">MAPS EXTRACTED</text>
  <text x="96" y="292" class="value">{_metric_value(analysis_summary.get("maps_extracted"))}</text>

  <rect x="440" y="202" width="320" height="130" rx="18" fill="#fff" stroke="#dbe4f0" stroke-width="2"/>
  <text x="468" y="246" class="label">MAPS CHANGED</text>
  <text x="468" y="292" class="value">{_metric_value(analysis_summary.get("maps_changed"))}</text>

  <rect x="812" y="202" width="320" height="130" rx="18" fill="#fff" stroke="#dbe4f0" stroke-width="2"/>
  <text x="840" y="246" class="label">BINARY CHANGED</text>
  <text x="840" y="292" class="value">{_metric_value(binary_diff.get("changed_percent"))}%</text>

  <rect x="68" y="378" width="492" height="196" rx="18" fill="#fff7ed" stroke="#fed7aa" stroke-width="2"/>
  <text x="96" y="426" class="h2">{escape(verdict.get("title", "-"))}</text>
  <text x="96" y="462" class="small">{escape(verdict.get("message", "-")[:72])}</text>
  <text x="96" y="490" class="small">{escape(verdict.get("message", "-")[72:144])}</text>
  <text x="96" y="534" class="chip">Next step: {escape(verdict.get("next_step", "-")[:70])}</text>

  <rect x="608" y="378" width="524" height="196" rx="18" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>
  <text x="636" y="426" class="h2">{escape(first_recommendation.get("title", "Recommendation coverage"))}</text>
  <text x="636" y="466" class="small">Priority: {escape(first_recommendation.get("priority", "-"))}</text>
  <text x="636" y="498" class="small">Risk: {escape(first_recommendation.get("risk", "-"))}</text>
  <text x="636" y="530" class="small">Benefit: {escape(first_recommendation.get("benefit", "-"))}</text>

  <rect x="68" y="622" width="1064" height="54" rx="16" fill="#ecfdf5" stroke="#99f6e4"/>
  <text x="96" y="656" class="chip">Artifacts: analysis.json - e2e_summary.json - visual_evidence.html - visual_summary.svg - calibration_tuner_report.pdf</text>
</svg>
"""


def _assert_pdf_response(response, min_size: int = 5_000) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].endswith(
        'filename="calibration_tuner_report.pdf"'
    )
    assert response.content.startswith(b"%PDF")
    assert response.content.rstrip().endswith(b"%%EOF")
    assert b"/Type /Page" in response.content
    assert len(response.content) > min_size


def _assert_visual_artifacts_match_analysis(analysis: dict) -> None:
    html = (E2E_OUTPUT_DIR / "visual_evidence.html").read_text(encoding="utf-8")
    svg = (E2E_OUTPUT_DIR / "visual_summary.svg").read_text(encoding="utf-8")
    summary_json = json.loads(
        (E2E_OUTPUT_DIR / "e2e_summary.json").read_text(encoding="utf-8")
    )

    assert "E2E-01 Visual Evidence" in html
    assert "Recommendation evidence" in html
    assert "Generated artifacts" in html
    assert str(analysis["summary"]["maps_extracted"]) in html
    assert str(analysis["summary"]["maps_changed"]) in html
    assert analysis["analysis_verdict"]["title"] in html
    assert analysis["analysis_verdict"]["title"] in svg

    for item in analysis["recommendations"][:3]:
        assert item["title"] in html

    assert summary_json["analysis_snapshot"]["summary"] == analysis["summary"]
    assert summary_json["analysis_snapshot"]["verdict"] == analysis["analysis_verdict"]


def _write_e2e_artifacts(analysis: dict, pdf_bytes: bytes) -> None:
    E2E_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    (E2E_OUTPUT_DIR / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (E2E_OUTPUT_DIR / "calibration_tuner_report.pdf").write_bytes(pdf_bytes)

    recommendations = analysis.get("recommendations") or []
    maps = analysis.get("maps") or []
    summary = {
        "scenario": "E2E-01 complete original + tuned/current + map pack analysis",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "artifacts": {
            "analysis_json": "analysis.json",
            "pdf_report": "calibration_tuner_report.pdf",
            "visual_evidence": "visual_evidence.html",
            "visual_summary": "visual_summary.svg",
        },
        "checks": [
            {
                "step": "API availability",
                "status": "passed",
                "evidence": "/openapi.json returned 200",
            },
            {
                "step": "Calibration analysis",
                "status": "passed",
                "evidence": f"{analysis['summary']['maps_extracted']} maps extracted, "
                f"{analysis['summary']['maps_changed']} maps changed",
            },
            {
                "step": "UI-equivalent content",
                "status": "passed",
                "evidence": "metrics, maps, recommendations, verdict and power estimate are present",
            },
            {
                "step": "Recommendation coverage",
                "status": "passed",
                "evidence": ", ".join(item.get("title", "-") for item in recommendations[:3]),
            },
            {
                "step": "PDF report",
                "status": "passed",
                "evidence": "valid PDF generated from the same request payload",
            },
        ],
        "analysis_snapshot": {
            "summary": analysis.get("summary"),
            "binary_diff": {
                "changed_bytes": analysis.get("binary_diff", {}).get("changed_bytes"),
                "changed_percent": analysis.get("binary_diff", {}).get("changed_percent"),
            },
            "verdict": analysis.get("analysis_verdict"),
            "power_estimate": analysis.get("power_estimate"),
            "map_names": [item.get("name") for item in maps],
            "recommendation_titles": [item.get("title") for item in recommendations],
        },
        "note": (
            "This backend/API E2E scenario verifies the complete analysis and PDF workflow. "
            "Flutter desktop screenshots should be added as a separate visual E2E layer."
        ),
    }
    (E2E_OUTPUT_DIR / "e2e_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (E2E_OUTPUT_DIR / "visual_evidence.html").write_text(
        _generate_visual_evidence_html(analysis, summary),
        encoding="utf-8",
    )
    (E2E_OUTPUT_DIR / "visual_summary.svg").write_text(
        _generate_visual_summary_svg(analysis),
        encoding="utf-8",
    )


def test_e2e_01_complete_analysis_and_pdf_report_are_consistent():
    health_response = client.get("/openapi.json")
    assert health_response.status_code == 200

    payload = _complete_stage1_payload()
    analysis_response = client.post("/api/calibration/analyze", json=payload)

    assert analysis_response.status_code == 200
    analysis = analysis_response.json()

    summary = analysis["summary"]
    assert summary["original_file"] == "original.bin"
    assert summary["modified_file"] == "stage1.bin"
    assert summary["definitions_count"] == 3
    assert summary["maps_extracted"] == 3
    assert summary["maps_changed"] == 3

    categories = {item["category"] for item in analysis["maps"]}
    assert {"torque", "fuel", "air_fuel"} <= categories
    assert analysis["binary_diff"]["changed_bytes"] > 0
    assert analysis["binary_diff"]["changed_percent"] > 0

    recommendations = analysis["recommendations"]
    recommendation_titles = {item["title"] for item in recommendations}
    assert "Torque request / torque limiters" in recommendation_titles
    assert "Fuel quantity / injection duration" in recommendation_titles
    assert "Airflow / lambda / AFR model" in recommendation_titles
    assert all(item["actions"] for item in recommendations)
    assert all(item["risks"] for item in recommendations)

    verdict = analysis["analysis_verdict"]
    assert verdict["status"] in {
        "needs_validation",
        "high_risk_pattern",
        "looks_coherent",
    }
    assert verdict["title"]
    assert verdict["next_step"]

    power_estimate = analysis["power_estimate"]
    assert power_estimate["available"] is True
    assert power_estimate["estimated_hp_after_stage1"] > 101

    report_response = client.post("/api/calibration/report", json=payload)

    _assert_pdf_response(report_response)

    _write_e2e_artifacts(analysis, report_response.content)

    assert (E2E_OUTPUT_DIR / "analysis.json").exists()
    assert (E2E_OUTPUT_DIR / "calibration_tuner_report.pdf").exists()
    assert (E2E_OUTPUT_DIR / "e2e_summary.json").exists()
    assert (E2E_OUTPUT_DIR / "visual_evidence.html").exists()
    assert (E2E_OUTPUT_DIR / "visual_summary.svg").exists()
    _assert_visual_artifacts_match_analysis(analysis)


def test_e2e_02_original_only_with_map_pack_enters_planning_mode():
    payload = _original_only_payload()
    analysis_response = client.post("/api/calibration/analyze", json=payload)

    assert analysis_response.status_code == 200
    analysis = analysis_response.json()

    assert analysis["summary"]["original_file"] == "original.bin"
    assert analysis["summary"]["modified_file"] is None
    assert analysis["summary"]["definitions_count"] == 3
    assert analysis["summary"]["maps_extracted"] == 3
    assert analysis["summary"]["maps_changed"] == 0
    assert analysis["analysis_verdict"]["status"] == "planning_mode"
    tuner_summary = " ".join(analysis["report"]["tuner_summary"]).lower()
    assert "original-only mode" in tuner_summary
    assert "investigation plan" in tuner_summary
    assert analysis["recommendations"]

    report_response = client.post("/api/calibration/report", json=payload)
    _assert_pdf_response(report_response, min_size=4_000)


def test_e2e_03_missing_map_pack_keeps_analysis_in_missing_context_mode():
    payload = _missing_definitions_payload()
    analysis_response = client.post("/api/calibration/analyze", json=payload)

    assert analysis_response.status_code == 200
    analysis = analysis_response.json()

    assert analysis["summary"]["definitions_count"] == 0
    assert analysis["summary"]["maps_extracted"] == 0
    assert analysis["summary"]["maps_changed"] == 0
    assert analysis["binary_diff"]["changed_bytes"] > 0
    assert analysis["analysis_verdict"]["status"] == "missing_context"
    assert analysis["recommendations"][0]["category"] == "definitions"
    assert "map-pack" in analysis["analysis_verdict"]["next_step"].lower()


def test_e2e_04_invalid_uploaded_file_is_rejected_before_analysis():
    response = client.post("/api/calibration/analyze", json=_invalid_base64_payload())

    assert response.status_code == 400
    assert "broken.bin" in response.json()["detail"]

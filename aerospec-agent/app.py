"""Gradio UI entrypoint for AeroSpec Agent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr

from agents.graph import build_graph
from config import settings
from core.llm_provider import provider
from core.utils import load_json
from tools.plotting import plot_selected_regions

GRAPH = build_graph()
DEMO_PATH = Path(__file__).resolve().parent / "demos" / "demo_inputs.json"

APP_CSS = """
body { background: linear-gradient(180deg, #f8fbff 0%, #f4f7fb 100%); }
#hero { border: 1px solid #dbeafe; border-radius: 16px; padding: 18px; background: white; box-shadow: 0 4px 16px rgba(30,64,175,.08); }
.section-card { border: 1px solid #e2e8f0; border-radius: 14px; background: #ffffff; padding: 12px; box-shadow: 0 2px 10px rgba(15,23,42,.05); }
.small-muted { color: #475569; font-size: 0.92rem; }
"""


def _safe_float(v: float | None) -> float | None:
    return None if v in (None, "") else float(v)


def _spectral_region_color(lo: float, hi: float) -> str:
    center = (lo + hi) / 2
    if center < 700:
        return "#fef9c3"  # visible
    if center < 1000:
        return "#dcfce7"  # NIR
    return "#f3e8ff"  # SWIR


def _as_band_cards(items: list[dict[str, Any]]) -> str:
    if not items:
        return "<div class='section-card'>No bands selected.</div>"
    cards = []
    for idx, item in enumerate(items, start=1):
        lo, hi = item["range_nm"]
        bg = _spectral_region_color(lo, hi)
        cards.append(
            f"""
<div style="border:1px solid #cbd5e1;border-radius:12px;padding:10px;margin-bottom:8px;background:{bg};">
  <div style="font-weight:700;font-size:1rem;">#{idx} {item['id']}</div>
  <div style="font-size:.86rem;margin-top:3px;"><b>Range:</b> {lo:.0f}-{hi:.0f} nm | <b>Score:</b> {item['score']} | <b>Targets:</b> {', '.join(item.get('target_tags', []))}</div>
  <div style="font-size:.85rem;color:#334155;margin-top:4px;"><b>Why selected:</b> {item['rationale']}</div>
</div>
"""
        )
    return "\n".join(cards)


def _summary_block(report: dict[str, Any]) -> str:
    mission = report.get("mission_summary", {})
    targets = report.get("inferred_targets", mission.get("targets", []))
    bands = len(report.get("recommendations", {}).get("best_overall", []))
    return f"""
<div class="section-card" style="border-left:6px solid #2563eb;">
  <div style="font-size:1.15rem;font-weight:800;">Executive Mission Brief</div>
  <div class="small-muted" style="margin-top:6px;">{report.get('executive_summary', '')}</div>
  <div style="margin-top:8px;font-size:.9rem;">
    <b>Mission:</b> {mission.get('mission_goal', 'n/a')}<br>
    <b>Detected targets:</b> {targets}<br>
    <b>Recommended bands:</b> {bands}<br>
    <b>Confidence tier:</b> {report.get('confidence_tier', 'n/a')} ({report.get('confidence', 0):.2f})
  </div>
</div>
"""


def _alternatives_block(report: dict[str, Any]) -> str:
    recs = report.get("recommendations", {})
    overall = [x["id"] for x in recs.get("best_overall", [])]
    compact = [x["id"] for x in recs.get("best_compact", [])]
    robust = [x["id"] for x in recs.get("best_robust", [])]
    compromise = "Compromise plan detected due to constraints." if report.get("warnings") else "No major compromise warnings."
    return f"""
<div class="section-card">
  <div style="font-size:1.05rem;font-weight:700;">Alternatives & Compromise View</div>
  <div class="small-muted" style="margin:6px 0 8px 0;">{compromise}</div>
  <div style="font-size:.88rem;"><b>Best overall:</b> {overall}</div>
  <div style="font-size:.88rem;"><b>Compact option:</b> {compact}</div>
  <div style="font-size:.88rem;"><b>Robust option:</b> {robust}</div>
</div>
"""


def _workflow_card(log_lines: list[str]) -> str:
    pipeline = [
        "[1/5] Mission Interpreter",
        "[2/5] Knowledge Retriever",
        "[3/5] Constraint + Ranking",
        "[4/5] Verification",
        "[5/5] Report Agent",
    ]
    lines = "\n".join(f"- {x}" for x in log_lines)
    head = "\n".join(f"- {x}" for x in pipeline)
    return f"### Agent Workflow\n{head}\n\n**Run details**\n{lines}"


def _trust_block(report: dict[str, Any]) -> str:
    tier = report.get("confidence_tier", "Exploratory")
    color = {"High": "#166534", "Moderate": "#b45309"}.get(tier, "#b91c1c")
    coverage = report.get("verification", {}).get("target_coverage", {})
    coverage_text = "\n".join(f"- {k}: {v} bands" for k, v in coverage.items()) or "- no coverage details"
    assumptions = report.get("assumptions", [])
    assumptions_text = "\n".join(f"- {a}" for a in assumptions)
    warnings = report.get("warnings") or ["No major verification warnings."]
    warnings_text = "\n".join(f"- {w}" for w in warnings)
    return (
        f"<span style='color:{color};font-weight:700;'>Confidence tier: {tier} ({report.get('confidence',0):.2f})</span>\n\n"
        f"**Warnings / Conflicts**\n{warnings_text}\n\n"
        f"**Target coverage**\n{coverage_text}\n\n"
        f"**Assumptions**\n{assumptions_text}"
    )


def _run_agent(
    mission_goal: str,
    targets: list[str],
    platform_type: str,
    max_bands: int,
    photon_flux_condition: str,
    priority: str,
    range_min: float | None,
    range_max: float | None,
    notes: str,
):
    if not mission_goal.strip():
        raise gr.Error("Mission goal is required.")

    user_input = {
        "mission_goal": mission_goal,
        "targets": targets,
        "platform_type": platform_type,
        "max_bands": int(max_bands),
        "photon_flux_condition": photon_flux_condition,
        "priority": priority,
        "wavelength_range_min_nm": _safe_float(range_min),
        "wavelength_range_max_nm": _safe_float(range_max),
        "notes": notes,
    }

    try:
        result = GRAPH.invoke({"user_input": user_input, "workflow_log": [], "errors": [], "mode": provider.mode})
    except Exception as exc:
        raise gr.Error(f"Agent execution failed: {exc}") from exc

    report = result["report"]
    selected = report["recommendations"]["best_overall"]

    return (
        _summary_block(report),
        f"### Current run mode\n**{report.get('mode', provider.mode)}**",
        _workflow_card(report["workflow_steps"]),
        _as_band_cards(selected),
        _alternatives_block(report),
        selected,
        plot_selected_regions(selected),
        _trust_block(report),
        json.dumps(report, indent=2),
    )


def _load_sample(name: str):
    demos = load_json(DEMO_PATH)
    found = next((x for x in demos if x.get("name") == name), demos[0])
    return (
        found["mission_goal"],
        found["targets"],
        found["platform_type"],
        found["max_bands"],
        found["photon_flux_condition"],
        found["priority"],
        found.get("wavelength_range_min_nm"),
        found.get("wavelength_range_max_nm"),
        found.get("notes", ""),
    )


def _load_demo_1():
    return _load_sample("Thin cirrus fast-look")


def _load_demo_2():
    return _load_sample("Runway standing-water check")


def _load_demo_3():
    return _load_sample("Cloud + water aviation sweep")


def _load_demo_4():
    return _load_sample("4-band compact moisture brief")


def _load_demo_5():
    return _load_sample("Cloud + water + moisture constrained mission")


def build_ui() -> gr.Blocks:
    with gr.Blocks(title=settings.app_title, theme=gr.themes.Soft(), css=APP_CSS) as demo:
        gr.HTML(
            f"""
<div id='hero'>
  <div style='font-size:2rem;font-weight:800;color:#1e3a8a;'>AeroSpec Agent</div>
  <div style='font-size:1.1rem;color:#334155;font-weight:600;'>Trustworthy Hyperspectral Mission Design Copilot for Aviation</div>
  <div style='margin-top:8px;color:#334155;'>
  AeroSpec Agent helps researchers and aviation engineers design hyperspectral sensing plans by recommending wavelength bands
  based on mission goals such as cloud detection, water monitoring, or environmental analysis.
  The system combines spectral knowledge, constraint reasoning, and explainable AI to produce trustworthy sensing recommendations.
  </div>
  <div style='margin-top:10px;'><b>What makes this agent different?</b></div>
  <ul style='margin-top:6px;'>
    <li>tool-based reasoning</li>
    <li>constraint-aware band planning</li>
    <li>explainable spectral decisions</li>
    <li>trustworthy verification</li>
  </ul>
</div>
"""
        )

        gr.Markdown("### Try Example Missions")
        with gr.Row():
            demo1 = gr.Button("Thin Cirrus Fast-Look")
            demo2 = gr.Button("Runway Standing Water Check")
            demo3 = gr.Button("Cloud + Water Aviation Sweep")
            demo4 = gr.Button("4-Band Compact Moisture Brief")
            demo5 = gr.Button("Cloud + Water + Moisture Constrained Mission")

        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                gr.HTML("<div class='section-card'><h3 style='margin:0;'>Mission Configuration</h3><div class='small-muted'>Define mission intent, sensing targets, and constraints.</div></div>")
                mission_goal = gr.Textbox(label="Mission Description", lines=4, placeholder="Describe sensing objectives and operational constraints...")
                targets = gr.CheckboxGroup(["cloud", "water", "moisture", "vegetation", "custom"], label="Target Selector (multi-select)")
                platform_type = gr.Dropdown(["airborne", "satellite", "runway-side", "drone"], value="airborne", label="Platform")
                max_bands = gr.Slider(1, 12, value=6, step=1, label="Max Band Budget")
                photon_flux_condition = gr.Radio(["low", "medium", "high"], value="medium", label="Photon Flux")
                priority = gr.Dropdown(["accuracy", "robustness", "compactness", "interpretability"], value="accuracy", label="Priority")
                with gr.Row():
                    range_min = gr.Number(label="Optional Min Wavelength (nm)", value=None)
                    range_max = gr.Number(label="Optional Max Wavelength (nm)", value=None)
                notes = gr.Textbox(label="Optional Notes", lines=2)
                with gr.Row():
                    run_btn = gr.Button("Run Mission Design Agent", variant="primary")
                    clear_btn = gr.Button("Clear")

            with gr.Column(scale=7):
                summary = gr.HTML(elem_classes=["section-card"])
                mode_info = gr.Markdown(elem_classes=["section-card"])
                workflow = gr.Markdown(label="Agent Workflow", elem_classes=["section-card"])
                cards = gr.HTML(label="Recommended Bands", elem_classes=["section-card"])
                alternatives = gr.HTML(label="Alternatives", elem_classes=["section-card"])
                table = gr.Dataframe(label="Selected Band Plan")
                plot = gr.Plot(label="Spectral Plot")
                trust = gr.Markdown(label="Trust Notes", elem_classes=["section-card"])
                with gr.Accordion("Developer Debug View", open=False):
                    debug = gr.Code(language="json")

        gr.HTML(
            """
<div style='margin-top:16px;padding:12px;border-top:1px solid #d1d5db;color:#475569;font-size:.9rem;'>
  <b>AeroSpec Agent</b> · Research prototype for hyperspectral mission design<br>
  - uses spectral knowledge base<br>
  - uses constraint-aware band selection<br>
  - built for aviation sensing demonstrations
</div>
"""
        )

        outputs = [summary, mode_info, workflow, cards, alternatives, table, plot, trust, debug]
        inputs = [mission_goal, targets, platform_type, max_bands, photon_flux_condition, priority, range_min, range_max, notes]
        run_btn.click(_run_agent, inputs=inputs, outputs=outputs)

        for btn, fn in [
            (demo1, _load_demo_1),
            (demo2, _load_demo_2),
            (demo3, _load_demo_3),
            (demo4, _load_demo_4),
            (demo5, _load_demo_5),
        ]:
            btn.click(fn, outputs=inputs)

        clear_btn.click(
            lambda: ("", [], "airborne", 6, "medium", "accuracy", None, None, ""),
            outputs=inputs,
        )
    return demo


if __name__ == "__main__":
    build_ui().launch()

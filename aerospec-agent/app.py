"""Gradio UI entrypoint for AeroSpec Agent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr

from agents.graph import build_graph
from config import settings
from core.utils import load_json
from tools.plotting import plot_selected_regions

GRAPH = build_graph()
MISSION_HISTORY: list[dict[str, Any]] = []
DATA_DIR = Path(__file__).resolve().parent / "data"


def _safe_float(v: float | None) -> float | None:
    return None if v in (None, "") else float(v)


def _as_cards(items: list[dict[str, Any]]) -> str:
    if not items:
        return "<div style='padding:8px;border:1px solid #ddd;border-radius:8px;'>No recommendations available.</div>"

    card_html: list[str] = []
    for idx, item in enumerate(items[:4], start=1):
        lo, hi = item["range_nm"]
        card_html.append(
            f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;padding:12px;margin-bottom:8px;background:#f8fafc;">
  <div style="font-weight:700;font-size:16px;">#{idx} {item['id']}</div>
  <div style="font-size:13px;color:#0f172a;">Range: <b>{lo:.0f}-{hi:.0f} nm</b> | Score: <b>{item['score']}</b></div>
  <div style="font-size:12px;margin-top:4px;color:#334155;">{item['rationale']}</div>
  <div style="font-size:11px;margin-top:4px;color:#64748b;">Evidence: {item.get('retrieval_reason','n/a')}</div>
</div>
"""
        )
    return "\n".join(card_html)


def _summary_block(report: dict[str, Any]) -> str:
    color = "#065f46" if report.get("confidence", 0) >= 0.7 else "#92400e"
    return f"""
<div style="border-radius:12px;padding:14px;background:#f1f5f9;border:1px solid #dbeafe;">
  <div style="font-size:20px;font-weight:700;">Executive Mission Brief</div>
  <div style="margin-top:6px;font-size:14px;">{report['executive_summary']}</div>
  <div style="margin-top:8px;font-size:13px;color:{color};">
    Trust signal: <b>{report.get('confidence_tier', 'n/a')}</b> confidence ({report['confidence']:.2f})
  </div>
</div>
"""


def _run_agent(
    mission_goal: str,
    target_type: str,
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
        "target_type": target_type,
        "platform_type": platform_type,
        "max_bands": int(max_bands),
        "photon_flux_condition": photon_flux_condition,
        "priority": priority,
        "wavelength_range_min_nm": _safe_float(range_min),
        "wavelength_range_max_nm": _safe_float(range_max),
        "notes": notes,
    }

    try:
        result = GRAPH.invoke({"user_input": user_input, "workflow_log": [], "errors": []})
    except Exception as exc:
        raise gr.Error(f"Agent execution failed: {exc}") from exc

    report = result["report"]
    MISSION_HISTORY.append(report)

    summary_html = _summary_block(report)
    workflow_log = "\n".join(f"• {s}" for s in report["workflow_steps"])
    final_table = report["recommendations"]["best_overall"]
    fig = plot_selected_regions(final_table)
    cards_html = _as_cards(final_table)
    json_blob = json.dumps(report, indent=2)
    md_report = _to_markdown(report)
    history_json = json.dumps(MISSION_HISTORY[-5:], indent=2)
    trust_notes = "\n".join(f"- {w}" for w in (report.get("warnings") or ["No major warnings from rule-based verification."]))
    return summary_html, workflow_log, cards_html, final_table, fig, trust_notes, json_blob, md_report, history_json


def _to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AeroSpec Agent Recommendation Report",
        f"**Confidence:** {report['confidence']:.2f} ({report.get('confidence_tier','n/a')})",
        "",
        "## Mission Summary",
        f"```json\n{json.dumps(report['mission_summary'], indent=2)}\n```",
        "## Best Overall Recommendations",
    ]
    for item in report["recommendations"]["best_overall"]:
        lines.append(
            f"- **{item['id']}** ({item['range_nm'][0]}-{item['range_nm'][1]} nm), score={item['score']}, rationale: {item['rationale']}"
        )
    if report["warnings"]:
        lines.append("## Verification Warnings")
        lines.extend([f"- {w}" for w in report["warnings"]])
    return "\n".join(lines)


def _load_sample(sample_name: str):
    demos = load_json(DATA_DIR / "aviation_missions.json")
    found = next((x for x in demos if x["name"] == sample_name), demos[0])
    default_overrides = {
        "Thin cirrus fast-look": (5, "medium", "accuracy"),
        "Runway standing-water check": (4, "medium", "robustness"),
        "4-band compact moisture brief": (4, "low", "compactness"),
        "Vegetation stress perimeter scan": (5, "high", "interpretability"),
        "All-weather mixed hazard quick plan": (4, "medium", "robustness"),
    }
    max_bands, flux, priority = default_overrides.get(sample_name, (6, "medium", "accuracy"))
    return found["goal"], found["target_type"], found["platform_type"], max_bands, flux, priority, None, None, ""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title=settings.app_title, theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# {settings.app_title}\n### {settings.app_subtitle}")
        with gr.Accordion("Why this is agentic AI (not a chatbot)", open=False):
            gr.Markdown(
                """
- The app runs a **5-stage LangGraph workflow** with explicit state transitions.
- The LLM (optional) only normalizes mission fields and **cannot output spectral answers**.
- Wavelength recommendations are produced by **retrieval + deterministic scoring + rule verification**.
- You can inspect workflow logs, confidence signals, warnings, and machine-readable artifacts.
                """
            )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### Mission Inputs")
                mission_goal = gr.Textbox(label="Mission Goal", lines=4, placeholder="Describe sensing intent and constraints...")
                target_type = gr.Dropdown(["cloud", "water", "moisture", "vegetation", "custom"], value="custom", label="Target Type")
                platform_type = gr.Dropdown(["airborne", "satellite", "runway-side", "drone"], value="airborne", label="Platform Type")
                max_bands = gr.Slider(1, 12, value=6, step=1, label="Max Bands")
                photon_flux_condition = gr.Radio(["low", "medium", "high"], value="medium", label="Photon Flux")
                priority = gr.Dropdown(["accuracy", "robustness", "compactness", "interpretability"], value="accuracy", label="Priority")
                with gr.Row():
                    range_min = gr.Number(label="Min λ (nm)", value=None)
                    range_max = gr.Number(label="Max λ (nm)", value=None)
                notes = gr.Textbox(label="Optional Notes", lines=2)
                with gr.Row():
                    run_btn = gr.Button("Run Agent", variant="primary")
                    clear_btn = gr.Button("Clear")

                gr.Markdown("#### Live Demo Presets")
                sample = gr.Dropdown(
                    [
                        "Thin cirrus fast-look",
                        "Runway standing-water check",
                        "4-band compact moisture brief",
                        "Vegetation stress perimeter scan",
                        "All-weather mixed hazard quick plan",
                    ],
                    value="Thin cirrus fast-look",
                    label="Load preset",
                )
                load_btn = gr.Button("Load Sample")

            with gr.Column(scale=2):
                summary = gr.HTML(label="Executive Brief")
                workflow = gr.Markdown(label="Workflow Step Log")
                trust_notes = gr.Markdown(label="Trust & Verification Notes")
                cards = gr.HTML(label="Recommendation Cards")
                recommendations = gr.Dataframe(label="Recommended Bands (Structured)")
                spectral_plot = gr.Plot(label="Spectral Region Plot")
                with gr.Accordion("Debug JSON / Reasoning Artifacts", open=False):
                    debug_json = gr.Code(language="json")
                md_report = gr.Markdown(label="Markdown Report")
                mission_history = gr.Code(label="Recent Mission History (last 5)", language="json")

        run_btn.click(
            _run_agent,
            inputs=[mission_goal, target_type, platform_type, max_bands, photon_flux_condition, priority, range_min, range_max, notes],
            outputs=[summary, workflow, cards, recommendations, spectral_plot, trust_notes, debug_json, md_report, mission_history],
        )
        load_btn.click(
            _load_sample,
            inputs=[sample],
            outputs=[mission_goal, target_type, platform_type, max_bands, photon_flux_condition, priority, range_min, range_max, notes],
        )
        clear_btn.click(
            lambda: ("", "custom", "airborne", 6, "medium", "accuracy", None, None, ""),
            outputs=[mission_goal, target_type, platform_type, max_bands, photon_flux_condition, priority, range_min, range_max, notes],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch()

"""LangGraph 图状态机 — 主编排器。

流程:
  scraper → matcher →┬→ tailor → applicant → tracker → END  (score ≥ 0.6)
                     ├→ tracker → END                        (0.3 ≤ score < 0.6, notify)
                     └→ END                                  (score < 0.3, skip)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.applicant_node import applicant_node
from app.agents.matcher_node import matcher_node
from app.agents.scraper_node import scraper_node
from app.agents.state import AgentState
from app.agents.tailor_node import tailor_node
from app.agents.tracker_node import tracker_node


def _route_after_matcher(state: AgentState) -> str:
    status = state.get("pipeline_status", "skip")
    if status == "tailor":
        return "tailor"
    if status == "notify":
        return "tracker"
    return "end"


workflow = StateGraph(AgentState)

workflow.add_node("scraper", scraper_node)
workflow.add_node("matcher", matcher_node)
workflow.add_node("tailor", tailor_node)
workflow.add_node("applicant", applicant_node)
workflow.add_node("tracker", tracker_node)

workflow.add_edge(START, "scraper")
workflow.add_edge("scraper", "matcher")
workflow.add_conditional_edges(
    "matcher",
    _route_after_matcher,
    {"tailor": "tailor", "tracker": "tracker", "end": END},
)
workflow.add_edge("tailor", "applicant")
workflow.add_edge("applicant", "tracker")
workflow.add_edge("tracker", END)

graph = workflow.compile()

from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    raw_data: Dict[str, Any]                  # Input daily hotel data (JSON/CSV)
    validation_results: Dict[str, Any]        # Data checks and outlier detection results
    forecast_14d: Dict[str, Any]              # 14-day demand forecast by segment
    analysis: Dict[str, Any]                  # Budget vs actual variance, last year comparison
    risks: Dict[str, Any]                     # Anomalies, cancellation spikes, pace drop alerts
    strategy_recommendations: Dict[str, Any]  # Actionable rate and inventory rules
    report_markdown: str                      # Fully compiled Markdown report
    audit_trail: List[str]                    # Steps executed by the orchestrator

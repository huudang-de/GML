"""Business AI Agents package."""

from app.agents.advisor import (
    create_advise_node,
    evaluate_kpi_threshold_level,
    filter_approved_actions,
    run_advisor,
)
from app.agents.explainer import (
    create_explain_node,
    run_explainer,
)
from app.agents.models import (
    Advice,
    Answer,
    Explanation,
    Figure,
    GroundingVerdict,
    Source,
    Trend,
    TrendAnomaly,
    TrendPoint,
)
from app.agents.rag_agent import (
    create_rag_lookup_node,
    run_rag_pipeline,
)
from app.agents.sql_agent import (
    SqlPipelineOutput,
    confidence_gate_node,
    create_sql_lookup_node,
    run_sql_pipeline,
)
from app.agents.synthesizer import (
    create_clarify_node,
    create_synthesize_node,
    run_synthesizer,
    verify_figure_provenance,
)
from app.agents.trend_agent import (
    analyze_kpi_trend,
    create_trend_node,
    detect_series_anomalies,
)

__all__ = [
    "Advice",
    "Answer",
    "Explanation",
    "Figure",
    "GroundingVerdict",
    "Source",
    "SqlPipelineOutput",
    "Trend",
    "TrendAnomaly",
    "TrendPoint",
    "analyze_kpi_trend",
    "confidence_gate_node",
    "create_advise_node",
    "create_clarify_node",
    "create_explain_node",
    "create_rag_lookup_node",
    "create_sql_lookup_node",
    "create_synthesize_node",
    "create_trend_node",
    "detect_series_anomalies",
    "evaluate_kpi_threshold_level",
    "filter_approved_actions",
    "run_advisor",
    "run_explainer",
    "run_rag_pipeline",
    "run_sql_pipeline",
    "run_synthesizer",
    "verify_figure_provenance",
]

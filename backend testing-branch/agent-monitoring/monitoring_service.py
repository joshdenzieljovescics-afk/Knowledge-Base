"""
Agent Monitoring Service - Collects and stores metrics from all agents
Port: 8009
"""

print("🔍 Loading monitoring_service.py...")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import uvicorn
from collections import defaultdict
import statistics

print("✅ All imports successful")

app = FastAPI(title="Agent Monitoring Service", version="1.0.0")

print("✅ FastAPI app created")

# In-memory storage (use Redis/DB in production)
agent_metrics = defaultdict(list)
agent_summaries = {}

# ============================================================
# MODELS
# ============================================================


class MetricRecord(BaseModel):
    """Single metric record from an agent"""

    agent_name: str
    task_id: str
    timestamp: str

    # Core metrics
    accuracy_score: Optional[float] = None  # 0-100
    latency_seconds: float
    success: bool
    error_message: Optional[str] = None

    # Resource metrics
    tokens_used: Optional[int] = None
    memory_mb: Optional[float] = None
    api_calls: Optional[int] = None

    # Task details
    task_type: str
    input_size: Optional[int] = None
    output_size: Optional[int] = None

    # User feedback (optional, added later)
    user_rating: Optional[float] = None  # 1-5 stars
    user_comment: Optional[str] = None


class FeedbackRecord(BaseModel):
    """User feedback for a completed task"""

    task_id: str
    agent_name: str
    rating: float  # 1-5
    comment: Optional[str] = None
    timestamp: str


class AgentSummary(BaseModel):
    """Aggregated metrics for an agent"""

    agent_name: str
    time_window: str
    total_tasks: int

    # Accuracy
    avg_accuracy: float
    accuracy_trend: str

    # Speed
    avg_latency: float
    p95_latency: float
    latency_trend: str

    # Reliability
    success_rate: float
    retry_rate: float

    # Resources
    total_tokens: int
    avg_tokens_per_task: float

    # Feedback
    avg_user_rating: float
    total_feedback: int


# ============================================================
# TABLE 8 SCORING FUNCTIONS
# ============================================================


def calculate_component_scores(metrics: List[Dict]) -> Dict[str, float]:
    """
    Calculate individual component scores based on Table 8
    Returns scores normalized to 0-100 scale
    """
    if not metrics:
        return {
            "accuracy": 0,
            "speed": 0,
            "reliability": 0,
            "resource_efficiency": 0,
            "user_feedback": 0,
        }

    # A = Accuracy Score (0-100)
    # ✅ FIX: Cap each individual score at 100 before averaging
    accuracy_scores = []
    for m in metrics:
        if m.get("accuracy_score") is not None:
            score = m["accuracy_score"]
            # ✅ CRITICAL: Cap at 100 before adding to list
            capped_score = min(score, 100.0)
            accuracy_scores.append(capped_score)

    A = statistics.mean(accuracy_scores) if accuracy_scores else 0
    A = min(A, 100.0)  # ✅ Double-check: Cap average at 100

    # S = Speed/Latency Score (0-100)
    latencies = [m["latency_seconds"] for m in metrics]
    latency_scores = []
    for latency in latencies:
        if latency < 3:
            score = 100
        elif latency <= 10:
            score = 100 - ((latency - 3) * (25 / 7))
            score = max(score, 75)
        else:
            score = 50 - ((latency - 11) * (50 / 9))
            score = max(score, 0)

        # ✅ Cap at 100
        latency_scores.append(min(score, 100.0))

    S = statistics.mean(latency_scores) if latency_scores else 0
    S = min(S, 100.0)  # ✅ Cap average at 100

    # L = Reliability Score (0-100)
    successes = sum(1 for m in metrics if m["success"])
    L = (successes / len(metrics)) * 100
    L = min(L, 100.0)  # ✅ Cap at 100

    # E = Resource Efficiency Score (0-100)
    tokens = [m.get("tokens_used", 0) for m in metrics if m.get("tokens_used")]
    if tokens:
        avg_tokens = statistics.mean(tokens)
        E = max(100 - (avg_tokens / 100), 0)
    else:
        E = 100
    E = min(E, 100.0)  # ✅ Cap at 100

    # U = User Feedback Score (0-100)
    ratings = [m.get("user_rating", 0) for m in metrics if m.get("user_rating")]
    if ratings:
        avg_rating = statistics.mean(ratings)
        U = (avg_rating / 5) * 100
    else:
        U = 0
    U = min(U, 100.0)  # ✅ Cap at 100

    return {
        "accuracy": round(min(A, 100.0), 2),
        "speed": round(min(S, 100.0), 2),
        "reliability": round(min(L, 100.0), 2),
        "resource_efficiency": round(min(E, 100.0), 2),
        "user_feedback": round(min(U, 100.0), 2),
    }


def calculate_agent_score(component_scores: Dict[str, float]) -> float:
    """
    Calculate overall agent score using weighted formula from Table 8

    Agent Score = (A × 0.35) + (S × 0.25) + (L × 0.15) + (E × 0.10) + (U × 0.15)
    """
    A = component_scores["accuracy"]
    S = component_scores["speed"]
    L = component_scores["reliability"]
    E = component_scores["resource_efficiency"]
    U = component_scores["user_feedback"]

    agent_score = (A * 0.35) + (S * 0.25) + (L * 0.15) + (E * 0.10) + (U * 0.15)
    return round(agent_score, 2)


def get_performance_tier(score: float) -> Dict[str, str]:
    """
    Determine performance tier based on Table 9
    """
    if score >= 85:
        return {
            "tier": "Excellent",
            "meaning": "Agent is highly effective and consistent",
        }
    elif score >= 70:
        return {
            "tier": "Good",
            "meaning": "Agent performs well but may need optimization",
        }
    elif score >= 50:
        return {"tier": "Fair", "meaning": "Agent needs improvement in key areas"}
    else:
        return {
            "tier": "Poor",
            "meaning": "Agent is underperforming and may need redesign",
        }


# ============================================================
# METRIC COLLECTION
# ============================================================


@app.post("/metrics/record")
async def record_metric(metric: MetricRecord):
    """Record a single metric from an agent"""
    try:
        print(f"\n📊 MONITORING SERVICE - Received metric:")
        print(f"   Agent: {metric.agent_name}")
        print(f"   Task Type: {metric.task_type}")
        print(f"   Success: {metric.success}")
        print(f"   Accuracy: {metric.accuracy_score}")

        # Store the metric
        agent_metrics[metric.agent_name].append(metric.dict())

        # Keep only last 1000 records per agent
        if len(agent_metrics[metric.agent_name]) > 1000:
            agent_metrics[metric.agent_name] = agent_metrics[metric.agent_name][-1000:]

        # Update summary
        update_agent_summary(metric.agent_name)

        print(
            f"   ✅ Stored successfully. Total metrics for {metric.agent_name}: {len(agent_metrics[metric.agent_name])}"
        )

        return {
            "success": True,
            "message": f"Recorded metric for {metric.agent_name}",
            "task_id": metric.task_id,
        }
    except Exception as e:
        print(f"   ❌ Error recording metric: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/metrics/feedback")
async def record_feedback(feedback: FeedbackRecord):
    """Record user feedback for a task"""
    try:
        # Find the corresponding metric record
        agent_name = feedback.agent_name
        task_id = feedback.task_id

        for metric in agent_metrics[agent_name]:
            if metric["task_id"] == task_id:
                metric["user_rating"] = feedback.rating
                metric["user_comment"] = feedback.comment
                break

        # Update summary
        update_agent_summary(agent_name)

        return {"success": True, "message": f"Recorded feedback for task {task_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# METRIC AGGREGATION
# ============================================================


def update_agent_summary(agent_name: str, window_hours: int = 24):
    """Calculate aggregated metrics for an agent using Table 8 formula"""
    try:
        metrics = agent_metrics.get(agent_name, [])

        if not metrics:
            return

        # Filter by time window
        cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()
        recent_metrics = [m for m in metrics if m["timestamp"] >= cutoff]

        if not recent_metrics:
            return

        # Calculate component scores using Table 8 methodology
        component_scores = calculate_component_scores(recent_metrics)

        # Calculate overall agent score using weighted formula
        overall_score = calculate_agent_score(component_scores)

        # Determine performance tier
        performance_tier = get_performance_tier(overall_score)

        # Calculate traditional metrics for backward compatibility
        total_tasks = len(recent_metrics)

        # Tokens
        tokens = [
            m["tokens_used"] for m in recent_metrics if m["tokens_used"] is not None
        ]
        total_tokens = sum(tokens) if tokens else 0
        avg_tokens = statistics.mean(tokens) if tokens else 0

        # Calculate trends
        mid = len(recent_metrics) // 2
        if mid > 5:
            first_half = recent_metrics[:mid]
            second_half = recent_metrics[mid:]

            # Score trend (comparing overall scores)
            first_scores = calculate_component_scores(first_half)
            second_scores = calculate_component_scores(second_half)
            first_overall = calculate_agent_score(first_scores)
            second_overall = calculate_agent_score(second_scores)

            score_trend = "improving" if second_overall > first_overall else "degrading"
        else:
            score_trend = "stable"

        # Store summary with new metrics
        agent_summaries[agent_name] = {
            "agent_name": agent_name,
            "time_window": f"{window_hours}h",
            "total_tasks": total_tasks,
            # Component Scores (Table 8)
            "accuracy_score": component_scores["accuracy"],
            "speed_score": component_scores["speed"],
            "reliability_score": component_scores["reliability"],
            "resource_efficiency_score": component_scores["resource_efficiency"],
            "user_feedback_score": component_scores["user_feedback"],
            # Overall Performance
            "overall_score": overall_score,
            "performance_tier": performance_tier["tier"],
            "performance_meaning": performance_tier["meaning"],
            "score_trend": score_trend,
            # Legacy metrics (for backward compatibility)
            "avg_accuracy": component_scores["accuracy"],
            "avg_latency": statistics.mean(
                [m["latency_seconds"] for m in recent_metrics]
            ),
            "success_rate": component_scores["reliability"],
            "total_tokens": total_tokens,
            "avg_tokens_per_task": round(avg_tokens, 0),
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Error updating summary for {agent_name}: {str(e)}")
        import traceback

        traceback.print_exc()


# ============================================================
# QUERY ENDPOINTS
# ============================================================


@app.get("/metrics/agents")
async def list_agents():
    """Get list of all monitored agents"""
    return {
        "success": True,
        "agents": list(agent_summaries.keys()),
        "count": len(agent_summaries),
    }


@app.get("/metrics/summary/{agent_name}")
async def get_agent_summary(agent_name: str, window_hours: int = 24):
    """Get aggregated metrics for a specific agent"""
    try:
        # Update summary with requested window
        update_agent_summary(agent_name, window_hours)

        summary = agent_summaries.get(agent_name)

        if not summary:
            raise HTTPException(
                status_code=404, detail=f"No data for agent: {agent_name}"
            )

        return {"success": True, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/all")
async def get_all_summaries(window_hours: int = 24):
    """Get summaries for all agents"""
    try:
        # Update all summaries
        for agent_name in agent_metrics.keys():
            update_agent_summary(agent_name, window_hours)

        return {
            "success": True,
            "agents": list(agent_summaries.values()),
            "count": len(agent_summaries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/raw/{agent_name}")
async def get_raw_metrics(agent_name: str, limit: int = 100):
    """Get raw metric records for an agent"""
    try:
        metrics = agent_metrics.get(agent_name, [])

        if not metrics:
            return {"success": True, "metrics": [], "count": 0}

        # Return most recent records
        recent = metrics[-limit:]

        return {
            "success": True,
            "metrics": recent,
            "count": len(recent),
            "total_available": len(metrics),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "agent-monitoring",
        "version": "1.0.0",
        "agents_monitored": len(agent_summaries),
    }


if __name__ == "__main__":
    print("🔍 Starting Agent Monitoring Service on port 8009")
    uvicorn.run(app, host="0.0.0.0", port=8009)

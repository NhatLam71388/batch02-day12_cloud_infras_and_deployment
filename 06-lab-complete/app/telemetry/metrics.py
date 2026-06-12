import time
from typing import Dict, Any, List
from app.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage) # Mock cost calculation
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Calculates the actual cost based on model and token usage.
        Pricing is based on standard rates per 1M tokens (converted to per token).
        """
        pricing = {
            "gpt-4o": [5.00, 15.00],
            "gpt-4o-mini": [0.150, 0.600],
            "gpt-3.5-turbo": [0.50, 1.50],
            "gemini-1.5-pro": [3.50, 10.50],
            "gemini-1.5-flash": [0.075, 0.30],
            "gemini-2.0-flash": [0.075, 0.30],
            "gemini-2.5-flash": [0.075, 0.30],
            "gemini-flash-latest": [0.075, 0.30],
            "gemini-pro-latest": [3.50, 10.50],
        }

        # Default fallback pricing (GPT-3.5 tier)
        rates = pricing.get(model.lower(), [0.50, 1.50])
        
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = (prompt_tokens * rates[0] / 1_000_000) + (completion_tokens * rates[1] / 1_000_000)
        return round(cost, 6)

# Global tracker instance
tracker = PerformanceTracker()

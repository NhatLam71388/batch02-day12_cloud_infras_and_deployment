import time
from typing import Dict, Any, Optional
from app.core.llm_provider import LLMProvider
from app.telemetry.metrics import tracker

class ChatbotBaseline:
    """
    Baseline Chatbot: Calls the LLM directly without any reasoning steps or tools.
    """
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, user_input: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # Simple system prompt for the baseline
        system_prompt = "You are a helpful e-commerce assistant. Answer the customer's question directly based on your knowledge."
        
        # Generate response from LLM
        response = self.llm.generate(user_input, system_prompt=system_prompt)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # usage = response.get("usage", {})
        # prompt_tokens = usage.get("prompt_tokens", 0)
        # completion_tokens = usage.get("completion_tokens", 0)
        # total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        
        # Standard output format requested by Member C
        result = {
            "answer": response["content"],
            "steps": [], # Baseline has no ReAct steps
            "metrics": {
                "latency_ms": response.get("latency_ms", latency_ms),
                "prompt_tokens": response["usage"].get("prompt_tokens", 0),
                "completion_tokens": response["usage"].get("completion_tokens", 0),
                "total_tokens": response["usage"].get("total_tokens", 0),
                "cost_usd": tracker._calculate_cost(self.llm.model_name, response["usage"])
            }
        }
        return result

from __future__ import annotations

from typing import List, Dict, Any
from .config import PRICING


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        (input_tokens / 1000.0) * PRICING.input_per_1k
        + (output_tokens / 1000.0) * PRICING.output_per_1k
    )


COST_LOG: List[Dict[str, Any]] = []


def log_cost(
    node: str,
    role: str,
    in_tok: int,
    out_tok: int,
    prompt_preview: str,
    output_preview: str,
) -> None:
    COST_LOG.append(
        {
            "node": node,
            "role": role,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "input_cost": (in_tok / 1000.0) * PRICING.input_per_1k,
            "output_cost": (out_tok / 1000.0) * PRICING.output_per_1k,
            "total_cost": estimate_cost(in_tok, out_tok),
            "prompt_preview": prompt_preview[:200],
            "output_preview": output_preview[:200],
        }
    )


def summarize_cost() -> Dict[str, Any]:
    total_in = sum(x["input_tokens"] for x in COST_LOG)
    total_out = sum(x["output_tokens"] for x in COST_LOG)
    return {
        "calls": len(COST_LOG),
        "input_tokens": total_in,
        "output_tokens": total_out,
        "est_cost": estimate_cost(total_in, total_out),
    }



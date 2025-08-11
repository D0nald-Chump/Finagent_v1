import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Pricing:
    input_per_1k: float
    output_per_1k: float


PRICE_INPUT_PER_1K = float(os.getenv("FINLLM_INPUT_PRICE_PER_1K", "0.05"))
PRICE_OUTPUT_PER_1K = float(os.getenv("FINLLM_OUTPUT_PRICE_PER_1K", "0.15"))
MODEL_NAME = os.getenv("FINLLM_MODEL", "gpt-5-mini")

PRICING = Pricing(
    input_per_1k=PRICE_INPUT_PER_1K,
    output_per_1k=PRICE_OUTPUT_PER_1K,
)



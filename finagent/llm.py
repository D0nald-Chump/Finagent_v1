from __future__ import annotations

from typing import Tuple
from .tokens import count_tokens


try:
    from openai import OpenAI  # type: ignore
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
    _client = OpenAI()
    _USE_OPENAI = True
except Exception as e:  # pragma: no cover - environment dependent
    print("OpenAI SDK 未就绪（将跳过真实请求，返回 stub 响应）。错误：", e)
    _client = None
    _USE_OPENAI = False


def call_llm(model: str, system: str, user: str) -> Tuple[str, int, int]:
    """Return (text, input_tokens, output_tokens). If SDK is unavailable, return a stub and estimated tokens."""
    prompt_for_count = f"[SYSTEM]\n{system}\n[USER]\n{user}"
    in_tok = count_tokens(prompt_for_count)
    if _USE_OPENAI:
        resp = _client.chat.completions.create(  # type: ignore[arg-type]
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=1,
        )
        text = (resp.choices[0].message.content or "").strip()
        out_tok = getattr(resp, "usage", None).completion_tokens if hasattr(resp, "usage") and resp.usage else count_tokens(text)  # type: ignore[attr-defined]
        in_tok = getattr(resp, "usage", None).prompt_tokens if hasattr(resp, "usage") and resp.usage else in_tok  # type: ignore[attr-defined]
        return text, in_tok, out_tok
    else:
        text = "【stub】此处返回模型输出（SDK 未就绪时的占位内容）。"
        out_tok = count_tokens(text)
        return text, in_tok, out_tok



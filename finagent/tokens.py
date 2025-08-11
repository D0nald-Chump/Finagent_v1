from __future__ import annotations


def _get_encoder():
    try:
        import tiktoken  # type: ignore

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


_ENCODER = _get_encoder()


def count_tokens(text: str) -> int:
    if not text:
        return 0
    if _ENCODER is not None:
        try:
            return len(_ENCODER.encode(text))
        except Exception:
            pass
    return max(1, int(len(text) / 4))



from __future__ import annotations

import json
from typing import Any, Type


def model_to_dict(model: Any) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def model_to_json(model: Any) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json()
    return model.json()


def model_from_json(model_cls: Type[Any], raw: str) -> Any:
    if hasattr(model_cls, "model_validate_json"):
        return model_cls.model_validate_json(raw)
    return model_cls.parse_raw(raw)


def extract_json_block(raw: str) -> str:
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : idx + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    return candidate
    return text

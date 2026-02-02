from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from crewai.llms.base_llm import BaseLLM
except Exception:  # pragma: no cover - crewai optional for shim usage
    class BaseLLM:  # type: ignore[too-many-instance-attributes]
        is_litellm = False

        def __init__(self, model: str, temperature: float | None = None, **kwargs: Any) -> None:
            self.model = model
            self.temperature = temperature
            self.api_key = kwargs.get("api_key")
            self.base_url = kwargs.get("base_url")
            self.stop = kwargs.get("stop") or []

        def supports_stop_words(self) -> bool:
            return False

        def _apply_stop_words(self, content: str) -> str:
            return content


@dataclass(frozen=True)
class LLMConfig:
    openai_api_key: str
    anthropic_api_key: str
    openai_model: str = "gpt-4.1"
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    timeout_s: float = 60.0
    temperature: float = 0.2
    max_tokens: int = 512

    @classmethod
    def from_env(cls) -> "LLMConfig":
        missing: List[str] = []
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not openai_key:
            missing.append("OPENAI_API_KEY")
        if not anthropic_key:
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise RuntimeError(f"Missing API keys: {', '.join(missing)}")

        def _float_env(name: str, default: float) -> float:
            raw = os.environ.get(name, "").strip()
            if not raw:
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        def _int_env(name: str, default: int) -> int:
            raw = os.environ.get(name, "").strip()
            if not raw:
                return default
            try:
                return int(raw)
            except ValueError:
                return default

        return cls(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4.1"),
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            anthropic_base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            timeout_s=_float_env("DEMO_LLM_TIMEOUT_S", 60.0),
            temperature=_float_env("DEMO_LLM_TEMPERATURE", 0.2),
            max_tokens=_int_env("DEMO_LLM_MAX_TOKENS", 512),
        )


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout_s: float) -> Tuple[Dict[str, Any], Dict[str, str], float]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
            elapsed = time.time() - start
            return json.loads(body), dict(response.headers), elapsed
    except urllib.error.HTTPError as exc:
        body = ""
        if exc.fp:
            body = exc.fp.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc


class OpenAIResponsesClient:
    def __init__(self, api_key: str, model: str, base_url: str, timeout_s: float) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def complete(self, prompt: str, temperature: float, max_tokens: int) -> Tuple[str, Dict[str, Any]]:
        url = f"{self.base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        data, _headers, elapsed = _post_json(url, headers, payload, self.timeout_s)
        text = _extract_openai_text(data)
        meta = {
            "provider": "openai",
            "model": self.model,
            "response_id": data.get("id", ""),
            "latency_ms": int(elapsed * 1000),
        }
        return text, meta


class AnthropicMessagesClient:
    def __init__(self, api_key: str, model: str, base_url: str, timeout_s: float) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def complete(self, prompt: str, temperature: float, max_tokens: int) -> Tuple[str, Dict[str, Any]]:
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        data, _headers, elapsed = _post_json(url, headers, payload, self.timeout_s)
        text = _extract_anthropic_text(data)
        meta = {
            "provider": "anthropic",
            "model": self.model,
            "response_id": data.get("id", ""),
            "latency_ms": int(elapsed * 1000),
        }
        return text, meta


class MultiProviderLLM(BaseLLM):
    def __init__(
        self,
        config: LLMConfig,
        task_provider_map: Optional[Dict[str, str]] = None,
        default_provider: str = "openai",
    ) -> None:
        self.config = config
        self.providers = {
            "openai": OpenAIResponsesClient(
                api_key=config.openai_api_key,
                model=config.openai_model,
                base_url=config.openai_base_url,
                timeout_s=config.timeout_s,
            ),
            "anthropic": AnthropicMessagesClient(
                api_key=config.anthropic_api_key,
                model=config.anthropic_model,
                base_url=config.anthropic_base_url,
                timeout_s=config.timeout_s,
            ),
        }
        self.task_provider_map = task_provider_map or {
            "summarize": "openai",
            "plan": "anthropic",
            "forensics": "openai",
        }
        self.default_provider = default_provider
        super().__init__(
            model="multi-provider",
            temperature=config.temperature,
            provider="multi-provider",
        )
        self.max_tokens = config.max_tokens
        self.last_meta: Dict[str, Any] = {}
        self.call_log: List[Dict[str, Any]] = []

    @classmethod
    def from_env(cls) -> "MultiProviderLLM":
        config = LLMConfig.from_env()
        task_provider_map = _task_map_from_env()
        return cls(config=config, task_provider_map=task_provider_map)

    def complete(self, prompt: str, **kwargs: Any) -> str:
        task_name = str(kwargs.pop("task_name", "") or "").strip().lower()
        if not task_name:
            task_name = _extract_task_name(prompt)
        provider = self.task_provider_map.get(task_name, self.default_provider)
        if provider not in self.providers:
            provider = self.default_provider
        temperature = float(kwargs.get("temperature", self.temperature))
        max_tokens = int(kwargs.get("max_tokens", self.max_tokens))
        text, meta = self.providers[provider].complete(prompt, temperature=temperature, max_tokens=max_tokens)
        meta["task_name"] = task_name or "unknown"
        self.last_meta = meta
        self.call_log.append(meta)
        if hasattr(self, "_apply_stop_words"):
            return self._apply_stop_words(text)
        return text

    # Compatibility shims for various LLM call styles
    def __call__(self, prompt: str, **kwargs: Any) -> str:
        return self.complete(prompt, **kwargs)

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        return self.complete(prompt, **kwargs)

    def predict(self, prompt: str, **kwargs: Any) -> str:
        return self.complete(prompt, **kwargs)

    def generate(self, prompts: List[str], **kwargs: Any) -> Dict[str, Any]:
        generations = [self.complete(prompt, **kwargs) for prompt in prompts]
        return {"generations": generations}

    async def agenerate(self, prompts: List[str], **kwargs: Any) -> Dict[str, Any]:
        return self.generate(prompts, **kwargs)

    def _call(self, prompt: str, **kwargs: Any) -> str:
        return self.complete(prompt, **kwargs)

    def call(
        self,
        messages: str | List[Dict[str, Any]],
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
        **kwargs: Any,
    ) -> str:
        task_name = ""
        if from_task is not None and getattr(from_task, "name", None):
            task_name = str(from_task.name).strip().lower()
        prompt = _messages_to_prompt(messages)
        return self.complete(prompt, task_name=task_name, **kwargs)

    async def acall(
        self,
        messages: str | List[Dict[str, Any]],
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
        **kwargs: Any,
    ) -> str:
        return self.call(
            messages,
            tools=tools,
            callbacks=callbacks,
            available_functions=available_functions,
            from_task=from_task,
            from_agent=from_agent,
            response_model=response_model,
            **kwargs,
        )

    def supports_function_calling(self) -> bool:
        return False


def _extract_task_name(prompt: str) -> str:
    for line in prompt.splitlines():
        if line.startswith("TASK_NAME:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def _messages_to_prompt(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    if isinstance(messages, list):
        parts: List[str] = []
        for message in messages:
            if not isinstance(message, dict):
                parts.append(str(message))
                continue
            content = message.get("content", "")
            parts.append(_flatten_content(content))
        return "\n\n".join([part for part in parts if part])
    return str(messages)


def _flatten_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: List[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    chunks.append(str(text))
                elif "content" in item:
                    chunks.append(str(item.get("content")))
            else:
                chunks.append(str(item))
        return "\n".join([chunk for chunk in chunks if chunk])
    return str(content)


def _task_map_from_env() -> Optional[Dict[str, str]]:
    raw = os.environ.get("DEMO_LLM_TASK_MAP", "").strip()
    if not raw:
        return None
    mapping: Dict[str, str] = {}
    for entry in raw.split(","):
        if not entry.strip():
            continue
        if ":" not in entry:
            continue
        task, provider = entry.split(":", 1)
        mapping[task.strip().lower()] = provider.strip().lower()
    return mapping or None


def _extract_openai_text(data: Dict[str, Any]) -> str:
    text = data.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    chunks: List[str] = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    chunks.append(str(content.get("text")))
        if item.get("type") in {"output_text", "text"} and item.get("text"):
            chunks.append(str(item.get("text")))
    if not chunks and "choices" in data:
        try:
            choice_text = data["choices"][0]["message"]["content"]
            if isinstance(choice_text, str):
                chunks.append(choice_text)
        except Exception:
            pass
    return "\n".join(chunks).strip()


def _extract_anthropic_text(data: Dict[str, Any]) -> str:
    chunks: List[str] = []
    for item in data.get("content", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and item.get("text"):
            chunks.append(str(item.get("text")))
    return "\n".join(chunks).strip()


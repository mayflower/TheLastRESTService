"""LLM client for in-sandbox planning calls."""

from __future__ import annotations

import os


class LLMClientError(Exception):
    """Raised when LLM client encounters an error."""


def _call_anthropic(prompt: str, api_key: str) -> str:
    """Call Anthropic API."""
    try:
        import httpx
    except ImportError as exc:
        raise LLMClientError("httpx not available") from exc

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            return ""
    except Exception as exc:
        raise LLMClientError(f"Anthropic API call failed: {exc}") from exc


def _call_openai(prompt: str, api_key: str) -> str:
    """Call OpenAI API."""
    try:
        import httpx
    except ImportError as exc:
        raise LLMClientError("httpx not available") from exc

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
    except Exception as exc:
        raise LLMClientError(f"OpenAI API call failed: {exc}") from exc


def call_llm(prompt: str) -> str:
    """Call configured LLM provider with the given prompt."""
    # Check for mock mode (used in tests)
    mock_handler = os.environ.get("LLM_MOCK_HANDLER")
    if mock_handler:
        # Import and call the mock
        import importlib

        module_name, func_name = mock_handler.rsplit(".", 1)
        module = importlib.import_module(module_name)
        mock_func = getattr(module, func_name)
        return mock_func(prompt)

    provider = os.environ.get("LARS_DEFAULT_PROVIDER", "openai").lower()

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMClientError("ANTHROPIC_API_KEY not set")
        return _call_anthropic(prompt, api_key)
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientError("OPENAI_API_KEY not set")
        return _call_openai(prompt, api_key)
    raise LLMClientError(f"Unsupported provider: {provider}")

"""
Multi-provider LLM client — Ollama, Groq, OpenRouter.

Reads API keys from environment variables:
  - OLLAMA_URL (default: http://localhost:11434/api/generate)
  - GROQ_API_KEY
  - OPENROUTER_API_KEY

Usage:
    from rm_traffic.llm_client import LLMClient
    client = LLMClient(provider="groq", model="llama-3.1-8b-instant")
    response = client.generate(prompt)
"""

import json
import logging
import os
import time
from typing import Optional

import requests

log = logging.getLogger("llm_client")

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"


class LLMClient:
    """Unified LLM client supporting Ollama, Groq, and OpenRouter."""

    def __init__(self, provider: str = "ollama", model: Optional[str] = None):
        self.provider = provider.lower().strip()
        self.model = model or self._default_model()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ProfileOps/1.0",
            "Accept": "application/json",
        })

    def _default_model(self) -> str:
        defaults = {
            "ollama": "llama3.2",
            "groq": "llama-3.1-8b-instant",
            "openrouter": "meta-llama/llama-3.1-8b-instruct",
        }
        return defaults.get(self.provider, "llama3.2")

    def _ollama_generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        try:
            resp = self.session.post(url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "num_predict": max_tokens,
                }
            }, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("response", "")
            log.error("Ollama error: %d %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            log.error("Ollama failed: %s", e)
            return None

    def _groq_generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            log.error("GROQ_API_KEY not set")
            return None
        try:
            resp = self.session.post("https://api.groq.com/openai/v1/chat/completions", json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.75,
                "max_tokens": max_tokens,
            }, headers={"Authorization": f"Bearer {key}"}, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            log.error("Groq error: %d %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            log.error("Groq failed: %s", e)
            return None

    def _openrouter_generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            log.error("OPENROUTER_API_KEY not set")
            return None
        try:
            resp = self.session.post("https://openrouter.ai/api/v1/chat/completions", json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.75,
                "max_tokens": max_tokens,
            }, headers={
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "ProfileOps",
            }, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            log.error("OpenRouter error: %d %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            log.error("OpenRouter failed: %s", e)
            return None

    def generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        """Generate text from the configured provider."""
        log.info("Generating with %s/%s", self.provider, self.model)
        start = time.time()
        if self.provider == "ollama":
            result = self._ollama_generate(prompt, max_tokens)
        elif self.provider == "groq":
            result = self._groq_generate(prompt, max_tokens)
        elif self.provider == "openrouter":
            result = self._openrouter_generate(prompt, max_tokens)
        else:
            log.error("Unknown provider: %s", self.provider)
            return None
        log.info("LLM response in %.1fs", time.time() - start)
        return result


# ---------------------------------------------------------------------------
# Convenience: try multiple providers in order
# ---------------------------------------------------------------------------

def generate_with_fallback(prompt: str, max_tokens: int = 800) -> Optional[str]:
    """Try Ollama, then Groq, then OpenRouter."""
    providers = []
    if os.environ.get("OLLAMA_URL") or os.environ.get("LLM_PROVIDER") == "ollama":
        providers.append(("ollama", "llama3.2"))
    if os.environ.get("GROQ_API_KEY"):
        providers.append(("groq", "llama-3.1-8b-instant"))
    if os.environ.get("OPENROUTER_API_KEY"):
        providers.append(("openrouter", "meta-llama/llama-3.1-8b-instruct"))
    if not providers:
        providers.append(("ollama", "llama3.2"))

    for provider, model in providers:
        client = LLMClient(provider, model)
        result = client.generate(prompt, max_tokens)
        if result:
            return result
    log.error("All LLM providers failed")
    return None

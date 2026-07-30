"""Optional external LLM advisor for player-facing discard suggestions.

This is intentionally separate from Basic/Advanced AI v1.  It never changes
the legal-action engine or automatically plays a move.  API keys are read from
environment variables only, and callers must pass a redacted public snapshot
plus the player's own hand.  No key or raw response is written to disk.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class AIAssistantError(RuntimeError):
    """Base error for configuration, transport, or provider responses."""


@dataclass(frozen=True)
class AIProviderConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    timeout_seconds: float = 20.0

    def normalized(self) -> "AIProviderConfig":
        provider = self.provider.strip().lower()
        aliases = {"chatgpt": "openai", "gemini": "gemini", "deepseek": "deepseek"}
        provider = aliases.get(provider, provider)
        if provider not in {"openai", "deepseek", "gemini", "custom"}:
            raise AIAssistantError("provider must be openai, deepseek, gemini, or custom.")
        if self.timeout_seconds <= 0:
            raise AIAssistantError("timeout_seconds must be positive.")
        return AIProviderConfig(provider, self.model.strip(), self.api_key_env.strip(), self.base_url, self.timeout_seconds)


@dataclass(frozen=True)
class AIRecommendation:
    tile: str
    reason: str
    provider: str
    model: str


class ExternalAIAssistant:
    """Ask a configured provider for a suggestion without granting game control."""

    def __init__(self, config: AIProviderConfig | None = None) -> None:
        self.config = (config or AIProviderConfig()).normalized()

    def _key(self) -> str:
        key = os.getenv(self.config.api_key_env, "").strip()
        if not key:
            raise AIAssistantError(
                f"Set {self.config.api_key_env} before enabling the external AI advisor."
            )
        return key

    def _prompt(self, hand: list[str], snapshot: Mapping[str, Any], legal_actions: list[str]) -> str:
        safe_snapshot = deepcopy(dict(snapshot))
        # Do not allow accidental hidden-hand leakage if a caller supplied a full snapshot.
        for player in safe_snapshot.get("players", []):
            if isinstance(player, dict) and player.get("seat") != 0:
                player["hand"] = None
        return json.dumps({
            "task": "Recommend one legal discard for a riichi mahjong player.",
            "hand": hand,
            "legal_discards": legal_actions,
            "public_state": safe_snapshot,
            "output": {"tile": "one item from legal_discards", "reason": "brief explanation"},
        }, ensure_ascii=False)

    def _request_json(self, url: str, headers: Mapping[str, str], body: Mapping[str, Any]) -> Mapping[str, Any]:
        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIAssistantError(f"External AI request failed: {exc}") from exc
        if not isinstance(value, Mapping):
            raise AIAssistantError("External AI response must be a JSON object.")
        return value

    def recommend(self, *, hand: list[str], snapshot: Mapping[str, Any], legal_actions: list[str]) -> AIRecommendation:
        if not hand or not legal_actions:
            raise AIAssistantError("hand and legal_actions are required.")
        prompt = self._prompt(list(hand), snapshot, list(legal_actions))
        key = self._key()
        if self.config.provider in {"openai", "deepseek", "custom"}:
            base = self.config.base_url or (
                "https://api.deepseek.com" if self.config.provider == "deepseek" else "https://api.openai.com"
            )
            response = self._request_json(
                f"{base.rstrip('/')}/v1/chat/completions",
                {"Authorization": f"Bearer {key}"},
                {"model": self.config.model, "temperature": 0.1,
                 "messages": [{"role": "system", "content": "Return JSON only."}, {"role": "user", "content": prompt}]},
            )
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            model = self.config.model or "gemini-2.0-flash"
            base = self.config.base_url or "https://generativelanguage.googleapis.com/v1beta"
            response = self._request_json(
                f"{base.rstrip('/')}/models/{model}:generateContent?key={key}", {},
                {"contents": [{"parts": [{"text": f"Return JSON only.\n{prompt}"}]}]},
            )
            content = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        try:
            parsed = json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())
            tile = str(parsed["tile"])
            reason = str(parsed.get("reason", ""))
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AIAssistantError("External AI returned invalid recommendation JSON.") from exc
        if tile not in legal_actions:
            raise AIAssistantError("External AI recommended a tile that is not legal in the current hand.")
        return AIRecommendation(tile, reason, self.config.provider, self.config.model)

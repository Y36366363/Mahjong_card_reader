"""Optional localhost bridge for browser AI hints.

Run this file locally; it reads the same MAHJONG_AI_* environment variables as
the desktop helper and never exposes the provider key to the browser.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_assistant import AIAssistantError, AIProviderConfig, ExternalAIAssistant


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self._send(204, {})

    def do_POST(self):  # noqa: N802
        if self.path != "/recommend":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            config = AIProviderConfig(
                provider=os.getenv("MAHJONG_AI_PROVIDER", "openai"),
                model=os.getenv("MAHJONG_AI_MODEL", ""),
                api_key_env=os.getenv("MAHJONG_AI_KEY_ENV", "OPENAI_API_KEY"),
            )
            assistant = ExternalAIAssistant(config)
            result = assistant.recommend(hand=request.get("hand", []), snapshot=request.get("snapshot", {}), legal_actions=request.get("legal_actions", []))
            self._send(200, {"recommendation": result.tile, "reason": result.reason, "provider": result.provider, "model": result.model})
        except (AIAssistantError, ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    port = int(os.getenv("MAHJONG_AI_PORT", "8766"))
    print(f"Mahjong local AI bridge listening on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

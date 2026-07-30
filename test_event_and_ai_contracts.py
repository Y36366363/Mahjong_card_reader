from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from ai_assistant import AIProviderConfig, AIAssistantError, ExternalAIAssistant
from game_events import EventLog, GameEvent, snapshot_event
from game import MahjongGame


class EventContractTests(unittest.TestCase):
    def test_game_records_and_saves_lifecycle_events(self) -> None:
        game = MahjongGame(seed=11, interactive=False, assist_mode="normal")
        game.play()
        kinds = [event.kind for event in game.event_log.events]
        self.assertIn("match.started", kinds)
        self.assertIn("hand.started", kinds)
        self.assertIn("match.finished", kinds)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "replay.json")
            game.save_replay(path)
            restored = MahjongGame.load_replay(path)
        self.assertEqual(len(restored.events), len(game.event_log.events))

    def test_event_log_round_trips_json_and_sequences(self) -> None:
        log = EventLog()
        log.append("hand.started", {"seed": 7, "round_hand": 0})
        log.append("action.discard", {"seat": 0, "tile": "5m"})
        restored = EventLog.from_json(log.to_json())
        self.assertEqual([event.kind for event in restored.events], ["hand.started", "action.discard"])
        self.assertEqual(restored.events[1].payload["tile"], "5m")

    def test_invalid_event_sequence_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EventLog.from_dict({"schema_version": 1, "events": [{"sequence": 2, "kind": "x"}]})

    def test_snapshot_event_does_not_change_snapshot(self) -> None:
        snapshot = {"schema_version": 1, "players": [{"seat": 0, "hand": ["1m"]}]}
        event = snapshot_event(snapshot)
        self.assertEqual(event.kind, "state.snapshot")
        self.assertEqual(event.payload, snapshot)


class ExternalAIContractTests(unittest.TestCase):
    def test_provider_aliases_and_validation(self) -> None:
        self.assertEqual(AIProviderConfig("chatgpt").normalized().provider, "openai")
        self.assertEqual(AIProviderConfig("deepseek").normalized().model, "deepseek-chat")
        self.assertEqual(AIProviderConfig("gemini").normalized().model, "gemini-flash-latest")
        with self.assertRaises(AIAssistantError):
            AIProviderConfig("unknown").normalized()

    def test_missing_key_fails_before_network(self) -> None:
        advisor = ExternalAIAssistant(AIProviderConfig(api_key_env="MAHJONG_TEST_MISSING"))
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(AIAssistantError):
            advisor.recommend(hand=["1m"], snapshot={"players": []}, legal_actions=["1m"])

    def test_external_advisor_redacts_other_hands_in_prompt(self) -> None:
        advisor = ExternalAIAssistant()
        snapshot = {"players": [{"seat": 0, "hand": ["1m"]}, {"seat": 1, "hand": ["9m"]}]}
        prompt = advisor._prompt(["1m"], snapshot, ["1m"])
        self.assertNotIn("9m", prompt)
        self.assertEqual(snapshot["players"][1]["hand"], ["9m"])


if __name__ == "__main__":
    unittest.main()

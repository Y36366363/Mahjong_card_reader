from __future__ import annotations

import queue
import unittest
from unittest.mock import patch

from desktop_ui import (
    PROFILE_DISPLAY_TO_ID,
    TABLE_POSITIONS,
    QueueWriter,
    classify_prompt,
    resolve_desktop_seed,
)


class DesktopUIAdapterTests(unittest.TestCase):
    def test_human_seat_is_at_the_bottom_of_the_table(self) -> None:
        self.assertEqual(TABLE_POSITIONS[0], (2, 1))
        self.assertEqual(TABLE_POSITIONS[2], (0, 1))
        self.assertEqual(TABLE_POSITIONS[3], (1, 0))
        self.assertEqual(TABLE_POSITIONS[1], (1, 2))

    def test_prompt_classification_covers_game_actions(self) -> None:
        self.assertEqual(classify_prompt("Discard tile (or index): "), "discard")
        self.assertEqual(classify_prompt("请输入要打出的牌或编号："), "discard")
        self.assertEqual(classify_prompt("Declare riichi? [y/N]"), "yes_no")
        self.assertEqual(classify_prompt("请选择吃法："), "chi")
        self.assertEqual(classify_prompt("Press Enter to continue"), "continue")

    def test_queue_writer_forwards_engine_output(self) -> None:
        events: queue.Queue[tuple[str, object]] = queue.Queue()
        writer = QueueWriter(events)
        self.assertEqual(writer.write("East 1\n"), 7)
        self.assertEqual(events.get_nowait(), ("output", "East 1\n"))

    def test_ai_profile_labels_and_replay_seeds_are_ui_ready(self) -> None:
        self.assertEqual(PROFILE_DISPLAY_TO_ID["Basic AI v1"], "basic_v1")
        self.assertEqual(PROFILE_DISPLAY_TO_ID["Advanced AI v1"], "advanced_v1")
        self.assertEqual(resolve_desktop_seed(" 20260718 "), 20260718)
        with patch("desktop_ui.secrets.randbits", return_value=987654321):
            self.assertEqual(resolve_desktop_seed(""), 987654321)


if __name__ == "__main__":
    unittest.main()

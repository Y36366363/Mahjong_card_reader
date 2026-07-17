from __future__ import annotations

import queue
import unittest

from desktop_ui import QueueWriter, classify_prompt


class DesktopUIAdapterTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

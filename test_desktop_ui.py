from __future__ import annotations

import queue
import unittest
from unittest.mock import patch

from desktop_ui import (
    FONT_SCALES,
    GameAborted,
    MahjongDesktopApp,
    MATCH_LENGTH_DISPLAY_TO_ID,
    PROFILE_DISPLAY_TO_ID,
    TABLE_POSITIONS,
    QueueWriter,
    classify_prompt,
    concealed_tile_backs,
    display_hand_order,
    display_text,
    display_tile,
    resolve_desktop_seed,
    seat_wind,
    valid_hint_tile,
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

    def test_chinese_tile_labels_are_display_only(self) -> None:
        self.assertEqual(display_tile("E", "zh"), "东")
        self.assertEqual(display_tile("P", "zh"), "白")
        self.assertEqual(display_tile("5m", "zh"), "5万")
        self.assertEqual(display_tile("0s", "zh"), "赤5索")
        self.assertEqual(display_tile("5m", "en"), "5m")
        self.assertEqual(display_text("是否碰 E？ 手牌 5m", "zh"), "是否碰 东？ 手牌 5万")

    def test_draw_is_visually_separated_at_far_right(self) -> None:
        ordered = display_hand_order(["1m", "2m", "2m", "9p"], "2m")
        self.assertEqual(ordered[-1], ("2m", True))
        self.assertEqual([tile for tile, _ in ordered], ["1m", "2m", "9p", "2m"])

    def test_opponent_concealed_tiles_show_the_correct_count(self) -> None:
        backs = concealed_tile_backs(13)
        self.assertEqual(backs.count("🀫"), 13)
        self.assertIn("\n", backs)

    def test_stale_hint_is_never_shown_for_an_absent_tile(self) -> None:
        hand = ["1m", "2m", "E"]
        self.assertEqual(valid_hint_tile(hand, "2m"), "2m")
        self.assertIsNone(valid_hint_tile(hand, "9p"))
        self.assertIsNone(valid_hint_tile(hand, None))

    def test_three_font_sizes_are_ordered_and_medium_is_neutral(self) -> None:
        self.assertEqual(FONT_SCALES["中 / Medium"], 1.0)
        self.assertLess(FONT_SCALES["小 / Small"], 1.0)
        self.assertGreater(FONT_SCALES["大 / Large"], 1.0)

    def test_desktop_offers_east_and_south_matches(self) -> None:
        self.assertEqual(MATCH_LENGTH_DISPLAY_TO_ID["东风战 / East"], "east")
        self.assertEqual(MATCH_LENGTH_DISPLAY_TO_ID["南风战 / South"], "south")

    def test_seat_winds_rotate_with_the_dealer(self) -> None:
        self.assertEqual([seat_wind(seat, 0) for seat in range(4)], ["E", "S", "W", "N"])
        self.assertEqual([seat_wind(seat, 2) for seat in range(4)], ["W", "N", "E", "S"])

    def test_return_to_title_can_unwind_a_blocking_input(self) -> None:
        app = MahjongDesktopApp.__new__(MahjongDesktopApp)
        app.events = queue.Queue()
        app.responses = queue.Queue()
        app.abort_requested = True
        app.responses.put("")
        with self.assertRaises(GameAborted):
            app._gui_input("Discard tile: ")


if __name__ == "__main__":
    unittest.main()

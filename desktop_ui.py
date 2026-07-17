from __future__ import annotations

import io
import queue
import threading
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import messagebox, ttk
from unittest.mock import patch

from game import AI_PROFILES, MahjongGame, dora_from_indicator


COLORS = {
    "bg": "#102d26",
    "table": "#17604f",
    "panel": "#f1eadb",
    "ink": "#17211d",
    "muted": "#63706a",
    "accent": "#d39b34",
    "danger": "#b6403a",
    "tile": "#fffdf4",
}


def classify_prompt(prompt: str) -> str:
    text = prompt.lower()
    if any(word in text for word in ("discard tile", "要打出的牌", "捨てる牌")):
        return "discard"
    if any(word in text for word in ("choose chi", "选择吃法", "チー")):
        return "chi"
    if any(word in text for word in ("press enter", "按回车", "enter")):
        return "continue"
    if any(word in text for word in ("[y/n]", "[是/否", "しますか", "是否", "?")):
        return "yes_no"
    return "text"


class QueueWriter(io.TextIOBase):
    def __init__(self, events: queue.Queue[tuple[str, object]]) -> None:
        self.events = events

    def write(self, text: str) -> int:
        if text:
            self.events.put(("output", text))
        return len(text)

    def flush(self) -> None:
        return None


class MahjongDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mahjong Card Reader — Desktop Game")
        self.root.geometry("1280x820")
        self.root.minsize(1040, 700)
        self.root.configure(bg=COLORS["bg"])
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.responses: queue.Queue[str] = queue.Queue()
        self.game: MahjongGame | None = None
        self.running = False
        self.pending_kind: str | None = None
        self._last_hand: tuple[str, ...] = ()
        self._configure_style()
        self._build_setup()
        self.root.after(80, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TButton", font=("Arial", 11), padding=8)
        style.configure("Accent.TButton", font=("Arial", 11, "bold"), padding=9)
        style.configure("TLabel", font=("Arial", 11))
        style.configure("Title.TLabel", font=("Arial", 24, "bold"))

    def _build_setup(self) -> None:
        self.setup = tk.Frame(self.root, bg=COLORS["bg"])
        self.setup.pack(fill="both", expand=True)
        card = tk.Frame(self.setup, bg=COLORS["panel"], padx=42, pady=34)
        card.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            card, text="Mahjong Card Reader", bg=COLORS["panel"], fg=COLORS["ink"],
            font=("Arial", 26, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 6))
        tk.Label(
            card, text="单机东风战 · Desktop Preview", bg=COLORS["panel"],
            fg=COLORS["muted"], font=("Arial", 12),
        ).grid(row=1, column=0, columnspan=2, pady=(0, 26))

        self.language_var = tk.StringVar(value="zh")
        self.profile_var = tk.StringVar(value="basic_v1")
        self.temperature_var = tk.DoubleVar(value=0.2)
        self.assist_var = tk.StringVar(value="hint")
        self.seed_var = tk.StringVar(value="")
        fields = [
            ("界面语言 / Language", ttk.Combobox(
                card, textvariable=self.language_var, state="readonly",
                values=("zh", "en", "ja"), width=24,
            )),
            ("电脑版本 / AI", ttk.Combobox(
                card, textvariable=self.profile_var, state="readonly",
                values=tuple(AI_PROFILES), width=24,
            )),
            ("提示模式 / Assist", ttk.Combobox(
                card, textvariable=self.assist_var, state="readonly",
                values=("hint", "normal"), width=24,
            )),
            ("牌山种子 / Seed", ttk.Entry(card, textvariable=self.seed_var, width=27)),
        ]
        for row, (label, widget) in enumerate(fields, 2):
            tk.Label(card, text=label, bg=COLORS["panel"], fg=COLORS["ink"]).grid(
                row=row, column=0, sticky="w", padx=(0, 22), pady=7
            )
            widget.grid(row=row, column=1, sticky="ew", pady=7)
        tk.Label(card, text="AI 温度 / Temperature", bg=COLORS["panel"], fg=COLORS["ink"]).grid(
            row=6, column=0, sticky="w", padx=(0, 22), pady=7
        )
        temp_row = tk.Frame(card, bg=COLORS["panel"])
        temp_row.grid(row=6, column=1, sticky="ew")
        ttk.Scale(temp_row, from_=0, to=1, variable=self.temperature_var).pack(
            side="left", fill="x", expand=True
        )
        self.temp_label = tk.Label(temp_row, text="0.20", width=5, bg=COLORS["panel"])
        self.temp_label.pack(side="left", padx=(8, 0))
        self.temperature_var.trace_add(
            "write", lambda *_: self.temp_label.config(text=f"{self.temperature_var.get():.2f}")
        )
        ttk.Button(card, text="开始东风战", style="Accent.TButton", command=self._start).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(28, 0)
        )

    def _build_game(self) -> None:
        self.setup.destroy()
        self.screen = tk.Frame(self.root, bg=COLORS["bg"], padx=12, pady=12)
        self.screen.pack(fill="both", expand=True)
        self.screen.grid_columnconfigure(0, weight=3)
        self.screen.grid_columnconfigure(1, weight=1)
        self.screen.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.screen, bg=COLORS["table"], padx=12, pady=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=2)
        left.grid_columnconfigure(2, weight=1)
        left.grid_rowconfigure(1, weight=1)
        self.player_labels: list[tk.Label | None] = [None] * 4
        positions = ((2, 2, 1), (1, 1, 2), (3, 1, 0), (0, 0, 1))
        for seat, row, column in positions:
            label = tk.Label(
                left, justify="left", anchor="nw", bg=COLORS["panel"], fg=COLORS["ink"],
                font=("Arial", 10), padx=10, pady=8, relief="ridge", bd=2,
            )
            label.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
            self.player_labels[seat] = label
        self.center_label = tk.Label(
            left, text="准备牌局…", justify="center", bg="#133f35", fg="white",
            font=("Arial", 14, "bold"), padx=12, pady=12,
        )
        self.center_label.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)

        bottom = tk.Frame(left, bg=COLORS["table"])
        bottom.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.meld_label = tk.Label(bottom, text="", bg=COLORS["table"], fg="white", anchor="w")
        self.meld_label.pack(fill="x")
        self.hand_frame = tk.Frame(bottom, bg=COLORS["table"])
        self.hand_frame.pack(fill="x", pady=(6, 0))

        right = tk.Frame(self.screen, bg=COLORS["panel"], padx=10, pady=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)
        tk.Label(
            right, text="操作 / Action", bg=COLORS["panel"], fg=COLORS["ink"],
            font=("Arial", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.prompt_label = tk.Label(
            right, text="等待牌局…", wraplength=290, justify="left",
            bg=COLORS["panel"], fg=COLORS["ink"], pady=8,
        )
        self.prompt_label.grid(row=1, column=0, sticky="ew")
        self.action_frame = tk.Frame(right, bg=COLORS["panel"])
        self.action_frame.grid(row=2, column=0, sticky="new")
        tk.Label(
            right, text="牌局记录 / Log", bg=COLORS["panel"], fg=COLORS["ink"],
            font=("Arial", 12, "bold"),
        ).grid(row=3, column=0, sticky="w", pady=(8, 3))
        self.log = tk.Text(
            right, height=18, width=38, state="disabled", wrap="word",
            bg="#fffdf7", fg=COLORS["ink"], relief="sunken", bd=1,
        )
        self.log.grid(row=4, column=0, sticky="nsew")
        right.grid_rowconfigure(4, weight=1)
        ttk.Button(right, text="返回标题（结束当前局）", command=self._close).grid(
            row=5, column=0, sticky="ew", pady=(9, 0)
        )

    def _start(self) -> None:
        try:
            seed_text = self.seed_var.get().strip()
            seed = int(seed_text) if seed_text else None
        except ValueError:
            messagebox.showerror("Invalid seed", "Seed 必须是整数或留空。")
            return
        profile = self.profile_var.get()
        temperature = float(self.temperature_var.get())
        self._build_game()
        self.game = MahjongGame(
            seed=seed,
            interactive=True,
            ai_levels=["basic_v1", profile, profile, profile],
            ai_temperatures=[0.0, temperature, temperature, temperature],
            assist_mode=self.assist_var.get(),
            language=self.language_var.get(),
        )
        self.running = True
        threading.Thread(target=self._run_game, daemon=True).start()

    def _run_game(self) -> None:
        writer = QueueWriter(self.events)
        try:
            with redirect_stdout(writer), patch("builtins.input", self._gui_input):
                assert self.game is not None
                self.game.play()
        except Exception as exc:  # keep a desktop crash visible and actionable
            self.events.put(("error", repr(exc)))
        finally:
            self.events.put(("done", None))

    def _gui_input(self, prompt: str = "") -> str:
        self.events.put(("prompt", prompt))
        return self.responses.get()

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "output":
                    self._append_log(str(payload))
                elif kind == "prompt":
                    self._show_prompt(str(payload))
                elif kind == "error":
                    messagebox.showerror("Game error", str(payload))
                elif kind == "done":
                    self.running = False
                    self.pending_kind = None
                    self.prompt_label.config(text="牌局结束 / Match complete")
                    self._clear_actions()
                    ttk.Button(self.action_frame, text="关闭游戏", command=self._close).pack(fill="x")
        except queue.Empty:
            pass
        self._refresh_table()
        self.root.after(80, self._poll)

    def _show_prompt(self, prompt: str) -> None:
        self.pending_kind = classify_prompt(prompt)
        self.prompt_label.config(text=prompt.strip() or "继续")
        self._clear_actions()
        if self.pending_kind == "discard":
            tk.Label(
                self.action_frame, text="请点击下方手牌", bg=COLORS["panel"], fg=COLORS["accent"],
            ).pack(anchor="w")
        elif self.pending_kind == "yes_no":
            ttk.Button(self.action_frame, text="是 / Yes", command=lambda: self._respond("y")).pack(
                side="left", fill="x", expand=True, padx=(0, 4)
            )
            ttk.Button(self.action_frame, text="否 / No", command=lambda: self._respond("n")).pack(
                side="left", fill="x", expand=True, padx=(4, 0)
            )
        elif self.pending_kind == "chi":
            for value, label in (("0", "跳过"), ("1", "吃法 1"), ("2", "吃法 2"), ("3", "吃法 3")):
                ttk.Button(
                    self.action_frame, text=label, command=lambda v=value: self._respond(v)
                ).pack(fill="x", pady=2)
        elif self.pending_kind == "continue":
            ttk.Button(self.action_frame, text="继续下一局", command=lambda: self._respond("")).pack(fill="x")
        else:
            entry = ttk.Entry(self.action_frame)
            entry.pack(fill="x", pady=(0, 5)); entry.focus_set()
            entry.bind("<Return>", lambda _event: self._respond(entry.get()))
            ttk.Button(self.action_frame, text="确认", command=lambda: self._respond(entry.get())).pack(fill="x")
        self._render_hand(force=True)

    def _respond(self, value: str) -> None:
        if self.pending_kind is None:
            return
        self.pending_kind = None
        self.responses.put(value)
        self.prompt_label.config(text="电脑行动中…")
        self._clear_actions()
        self._render_hand(force=True)

    def _clear_actions(self) -> None:
        for child in self.action_frame.winfo_children():
            child.destroy()

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _refresh_table(self) -> None:
        game = self.game
        if game is None or not hasattr(self, "center_label"):
            return
        try:
            for seat, player in enumerate(game.players):
                status = []
                if seat == game.dealer:
                    status.append("庄 / Dealer")
                if player.riichi:
                    status.append("立直 / Riichi")
                melds = " / ".join(
                    f"{meld.kind}:{' '.join(meld.tiles)}" for meld in list(player.melds)
                ) or "门清 / Closed"
                river = " ".join(list(player.river)) or "—"
                label = self.player_labels[seat]
                if label is None:
                    continue
                label.config(
                    text=(
                        f"{game._name(player)}  {player.points:,}\n"
                        f"{' · '.join(status) if status else ' '}\n"
                        f"{melds}\n河: {river}"
                    )
                )
            doras = " ".join(dora_from_indicator(tile) for tile in list(game.dora_indicators)) or "—"
            self.center_label.config(
                text=(
                    f"东 {game.round_hand + 1} 局\n"
                    f"本场 {game.honba}  ·  立直棒 {game.riichi_sticks}\n"
                    f"牌山 {len(game.wall)}\n宝牌 {doras}"
                )
            )
            player = game.players[0]
            self.meld_label.config(
                text="副露: " + (" / ".join(
                    f"{m.kind}({' '.join(m.tiles)})" for m in list(player.melds)
                ) or "无")
            )
            self._render_hand()
        except (IndexError, RuntimeError, tk.TclError):
            # The engine may be between two atomic-looking list operations; the
            # next 80 ms refresh will render the settled state.
            return

    def _render_hand(self, *, force: bool = False) -> None:
        if self.game is None or not hasattr(self, "hand_frame"):
            return
        hand = tuple(self.game.players[0].hand)
        active = self.pending_kind == "discard"
        signature = hand + (("active" if active else "idle"),)
        if not force and signature == self._last_hand:
            return
        self._last_hand = signature
        for child in self.hand_frame.winfo_children():
            child.destroy()
        for tile in hand:
            suit_color = {
                "m": "#b33b35", "p": "#2c63a0", "s": "#278153",
            }.get(tile[-1:] if len(tile) == 2 else "", COLORS["ink"])
            button = tk.Button(
                self.hand_frame, text=tile, width=4, height=2,
                bg=COLORS["tile"], fg=suit_color, relief="raised", bd=2,
                font=("Arial", 12, "bold"),
                command=lambda value=tile: self._respond(value),
                state="normal" if active else "disabled",
            )
            button.pack(side="left", padx=2)

    def _close(self) -> None:
        if self.running:
            self.responses.put("n")
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MahjongDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

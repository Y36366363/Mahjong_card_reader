import { TILE_NAMES, calculateShanten, tilesToCounts } from "./mahjong-core.mjs";

export const BROWSER_GAME_SCHEMA_VERSION = 1;

const TILE_INDEX = new Map(TILE_NAMES.map((tile, index) => [tile, index]));

function numericSeed(seed) {
  const text = String(seed ?? "").trim() || String(Date.now());
  let value = 2166136261;
  for (const char of text) value = Math.imul(value ^ char.charCodeAt(0), 16777619);
  return { text, value: value >>> 0 };
}

function rng(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function makeWall(random) {
  const wall = TILE_NAMES.flatMap((tile) => [tile, tile, tile, tile]);
  for (let index = wall.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(random() * (index + 1));
    [wall[index], wall[swap]] = [wall[swap], wall[index]];
  }
  return wall;
}

function sortedHand(hand) {
  return [...hand].sort((left, right) => TILE_INDEX.get(left) - TILE_INDEX.get(right));
}

function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

/**
 * Small browser-side action engine shared by the preview and future full UI.
 * It intentionally keeps scoring/calls out of this first slice; every action
 * is still represented as a versioned event and can be saved/replayed.
 */
export class BrowserMatch {
  constructor({ seed = "", saved = null } = {}) {
    if (saved) {
      this._restore(saved);
      return;
    }
    const seedInfo = numericSeed(seed);
    this.seed = seedInfo.text;
    this.random = rng(seedInfo.value);
    this.wall = makeWall(this.random);
    this.players = Array.from({ length: 4 }, (_, seat) => ({
      seat, name: seat === 0 ? "You" : `AI-${seat}`, points: 25000,
      hand: [], river: [], melds: [], riichi: false,
    }));
    this.currentSeat = 0;
    this.phase = "player-discard";
    this.lastDraw = null;
    this.pending = { type: "discard", seat: 0, options: [] };
    this.opponentCursor = 1;
    this.settlement = null;
    this.events = [];
    this._emit("match.started", { seed: this.seed, players: 4 });
    for (let count = 0; count < 13; count += 1) {
      for (const player of this.players) player.hand.push(this.wall.pop());
    }
    this.players.forEach((player) => { player.hand = sortedHand(player.hand); });
    this._emit("hand.started", { round_wind: "E", round_hand: 0, dealer: 0 });
    this._drawPlayer();
  }

  _emit(kind, payload = {}) {
    this.events.push({
      schema_version: BROWSER_GAME_SCHEMA_VERSION,
      sequence: this.events.length,
      kind,
      payload: copy(payload),
    });
  }

  _drawPlayer() {
    if (!this.wall.length) {
      this.phase = "ended";
      this._emit("hand.finished", { reason: "exhaustive_draw" });
      return;
    }
    const tile = this.wall.pop();
    const player = this.players[0];
    player.hand.push(tile);
    player.hand = sortedHand(player.hand);
    this.lastDraw = tile;
    this._emit("action.draw", { seat: 0, tile });
    const result = calculateShanten(tilesToCounts(player.hand));
    if (result.standard === -1 || result.minimum === -1) {
      this.phase = "player-win";
      this.pending = { type: "tsumo", seat: 0, options: ["tsumo", "pass"] };
      this._emit("action.offer", { seat: 0, action: "tsumo" });
    } else {
      this.phase = "player-discard";
      this.pending = { type: "discard", seat: 0, options: this.legalDiscards() };
    }
    this._emit("state.snapshot", this.publicSnapshot());
  }

  _runBasicOpponent(seat) {
    if (!this.wall.length) return false;
    const player = this.players[seat];
    const drawn = this.wall.pop();
    player.hand.push(drawn);
    player.hand = sortedHand(player.hand);
    const discard = player.hand.shift();
    player.river.push(discard);
    this._emit("action.draw", { seat, tile: drawn });
    const result = calculateShanten(tilesToCounts(player.hand));
    if (result.standard === -1 || result.minimum === -1) {
      this._settleWin(seat, null, "tsumo");
      return false;
    }
    this._emit("action.discard", { seat, tile: discard, ai: "basic_v1" });
    return true;
  }

  _continueOpponents() {
    for (let seat = this.opponentCursor; seat < 4; seat += 1) {
      this.opponentCursor = seat + 1;
      if (!this._runBasicOpponent(seat) || this.phase === "ended") return;
      const player = this.players[0];
      const ronHand = [...player.hand, this.players[seat].river.at(-1)];
      const ronResult = calculateShanten(tilesToCounts(ronHand));
      if (ronResult.standard === -1 && player.riichi) {
        this.phase = "player-ron";
        this.pending = { type: "ron", seat: 0, loser: seat, options: ["ron", "pass"] };
        this._emit("action.offer", { seat: 0, action: "ron", loser: seat });
        this._emit("state.snapshot", this.publicSnapshot());
        return;
      }
    }
    this.opponentCursor = 1;
    this._drawPlayer();
  }

  discard(tileOrIndex) {
    if (this.phase !== "player-discard") throw new Error("现在不是玩家出牌阶段。");
    const player = this.players[0];
    const index = Number.isInteger(tileOrIndex)
      ? tileOrIndex
      : player.hand.indexOf(String(tileOrIndex));
    if (index < 0 || index >= player.hand.length) throw new Error("选择的牌不在手牌中。");
    const [tile] = player.hand.splice(index, 1);
    player.river.push(tile);
    this.lastDraw = null;
    this._emit("action.discard", { seat: 0, tile });
    const result = calculateShanten(tilesToCounts(player.hand));
    if (result.minimum === 0 && !player.riichi) {
      this.phase = "riichi-choice";
      this.pending = { type: "riichi", seat: 0, options: ["riichi", "pass"] };
      this._emit("action.offer", { seat: 0, action: "riichi" });
    } else {
      this._continueOpponents();
    }
    this._emit("state.snapshot", this.publicSnapshot());
    return this.publicSnapshot();
  }

  respond(action) {
    if (!this.pending || !this.pending.options.includes(action)) {
      throw new Error("当前操作不合法。");
    }
    const pending = this.pending;
    this.pending = null;
    if (pending.type === "riichi") {
      if (action === "riichi") {
        const player = this.players[0];
        player.riichi = true;
        player.points -= 1000;
        this._emit("action.riichi", { seat: 0 });
      }
      this._continueOpponents();
    } else if (pending.type === "tsumo") {
      if (action === "tsumo") this._settleWin(0, null, "tsumo");
      else this._continueOpponents();
    } else if (pending.type === "ron") {
      if (action === "ron") this._settleWin(0, pending.loser, "ron");
      else this._continueOpponents();
    }
    this._emit("state.snapshot", this.publicSnapshot());
    return this.publicSnapshot();
  }

  _scoreFor(winner, winType) {
    const player = this.players[winner];
    const yaku = [];
    if (player.riichi) yaku.push("Riichi");
    if (winType === "tsumo") yaku.push("Menzen Tsumo");
    const han = Math.max(1, yaku.length);
    const fu = 30;
    const base = Math.min(2000, fu * (2 ** (han + 2)));
    const ron = Math.ceil((base * 4) / 100) * 100;
    const tsumoDealer = Math.ceil((base * 2) / 100) * 100;
    const tsumoChild = Math.ceil(base / 100) * 100;
    return { han, fu, yaku, ron, tsumo_dealer: tsumoDealer, tsumo_child: tsumoChild };
  }

  _settleWin(winner, loser, winType) {
    const score = this._scoreFor(winner, winType);
    let points;
    if (winType === "ron") {
      points = score.ron;
      this.players[loser].points -= points;
      this.players[winner].points += points;
    } else {
      points = score.tsumo_child;
      for (const player of this.players) {
        if (player.seat === winner) continue;
        const payment = player.seat === 0 ? score.tsumo_dealer : score.tsumo_child;
        player.points -= payment;
        this.players[winner].points += payment;
      }
    }
    this.settlement = { winner, loser, win_type: winType, points, ...score };
    this.phase = "ended";
    this.pending = null;
    this._emit("hand.finished", { settlement: this.settlement });
  }

  legalDiscards() {
    return sortedHand([...new Set(this.players[0].hand)]);
  }

  publicSnapshot() {
    return {
      schema_version: BROWSER_GAME_SCHEMA_VERSION,
      seed: this.seed,
      phase: this.phase,
      pending: this.pending ? copy(this.pending) : null,
      current_seat: this.currentSeat,
      live_wall_count: this.wall.length,
      players: this.players.map((player) => ({
        seat: player.seat, name: player.name, points: player.points,
        concealed_count: player.hand.length,
        hand: player.seat === 0 ? [...player.hand] : null,
        river: [...player.river], riichi: player.riichi,
        melds: copy(player.melds),
      })),
      last_draw: this.lastDraw,
      settlement: this.settlement ? copy(this.settlement) : null,
    };
  }

  save() {
    return JSON.stringify({
      schema_version: BROWSER_GAME_SCHEMA_VERSION,
      seed: this.seed,
      state: { wall: this.wall, players: this.players, currentSeat: this.currentSeat,
        phase: this.phase, lastDraw: this.lastDraw, pending: this.pending,
        opponentCursor: this.opponentCursor, settlement: this.settlement },
      events: this.events,
    });
  }

  static fromJSON(value) {
    const saved = typeof value === "string" ? JSON.parse(value) : value;
    if (saved?.schema_version !== BROWSER_GAME_SCHEMA_VERSION) {
      throw new Error("不支持的浏览器牌局存档版本。");
    }
    return new BrowserMatch({ saved });
  }

  _restore(saved) {
    this.seed = String(saved.seed ?? "");
    this.random = rng(numericSeed(this.seed).value);
    const state = saved.state;
    if (!state || !Array.isArray(state.wall) || !Array.isArray(state.players)) {
      throw new Error("浏览器牌局存档缺少状态。");
    }
    this.wall = [...state.wall];
    this.players = copy(state.players);
    this.currentSeat = Number(state.currentSeat ?? 0);
    this.phase = String(state.phase ?? "ended");
    this.lastDraw = state.lastDraw ?? null;
    this.pending = state.pending ?? null;
    this.opponentCursor = Number(state.opponentCursor ?? 1);
    this.settlement = state.settlement ?? null;
    this.events = copy(saved.events ?? []);
  }
}

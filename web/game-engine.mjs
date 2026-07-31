import { TILE_NAMES } from "./mahjong-core.mjs";

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
      hand: [], river: [], riichi: false,
    }));
    this.currentSeat = 0;
    this.phase = "player-discard";
    this.lastDraw = null;
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
    this.phase = "player-discard";
    this._emit("action.draw", { seat: 0, tile });
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
    this._emit("action.discard", { seat, tile: discard, ai: "basic_v1" });
    return true;
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
    for (let seat = 1; seat < 4; seat += 1) this._runBasicOpponent(seat);
    this._drawPlayer();
    return this.publicSnapshot();
  }

  legalDiscards() {
    return sortedHand([...new Set(this.players[0].hand)]);
  }

  publicSnapshot() {
    return {
      schema_version: BROWSER_GAME_SCHEMA_VERSION,
      seed: this.seed,
      phase: this.phase,
      current_seat: this.currentSeat,
      live_wall_count: this.wall.length,
      players: this.players.map((player) => ({
        seat: player.seat, name: player.name, points: player.points,
        concealed_count: player.hand.length,
        hand: player.seat === 0 ? [...player.hand] : null,
        river: [...player.river], riichi: player.riichi,
      })),
      last_draw: this.lastDraw,
    };
  }

  save() {
    return JSON.stringify({
      schema_version: BROWSER_GAME_SCHEMA_VERSION,
      seed: this.seed,
      state: { wall: this.wall, players: this.players, currentSeat: this.currentSeat,
        phase: this.phase, lastDraw: this.lastDraw },
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
    this.events = copy(saved.events ?? []);
  }
}


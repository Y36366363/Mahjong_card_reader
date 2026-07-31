import { TILE_NAMES, calculateShanten, tilesToCounts } from "./mahjong-core.mjs";
import { scoreHand } from "./scoring.mjs";

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
  constructor({ seed = "", ai = ["basic_v1", "basic_v1", "basic_v1"], temperature = 0.2, match = "east", saved = null } = {}) {
    if (saved) {
      this._restore(saved);
      return;
    }
    const seedInfo = numericSeed(seed);
    this.seed = seedInfo.text;
    this.ai = [...ai];
    this.temperature = Number(temperature) || 0;
    this.matchLength = match === "south" ? "south" : "east";
    this.random = rng(seedInfo.value);
    this.wall = makeWall(this.random);
    this.doraIndicators = [this.wall.pop()];
    this.uraIndicators = [this.wall.pop()];
    this.players = Array.from({ length: 4 }, (_, seat) => ({
      seat, name: seat === 0 ? "You" : `AI-${seat}`, points: 25000,
      hand: [], river: [], melds: [], riichi: false,
    }));
    this.dealer = 0;
    this.roundWind = "E";
    this.roundWindIndex = 0;
    this.seatWinds = ["E", "S", "W", "N"];
    this.currentSeat = 0;
    this.phase = "player-discard";
    this.lastDraw = null;
    this.pending = { type: "discard", seat: 0, options: [] };
    this.opponentCursor = 1;
    this.settlement = null;
    this.roundHand = 0;
    this.matchEnded = false;
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
      this.settlement = { win_type: "draw", reason: "exhaustive_draw" };
      this.pending = { type: "next_hand", options: ["next"] };
      this._emit("hand.finished", { settlement: this.settlement });
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
      this.pending = { type: "tsumo", seat: 0, tile, options: ["tsumo", "pass"] };
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
    const discard = this._chooseOpponentDiscard(seat);
    player.hand.splice(player.hand.indexOf(discard), 1);
    player.river.push(discard);
    this._emit("action.draw", { seat, tile: drawn });
    const result = calculateShanten(tilesToCounts(player.hand));
    if (result.standard === -1 || result.minimum === -1) {
      this._settleWin(seat, null, "tsumo", drawn);
      return false;
    }
    if (result.minimum === 0 && !player.riichi && player.melds.length === 0 && (this.ai[seat - 1] || "basic_v1") === "advanced_v1") {
      player.riichi = true;
      player.points -= 1000;
      this._emit("action.riichi", { seat, ai: "advanced_v1" });
    }
    this._emit("action.discard", { seat, tile: discard, ai: this.ai[seat - 1] || "basic_v1" });
    return true;
  }

  _chooseOpponentDiscard(seat) {
    const player = this.players[seat];
    if ((this.ai[seat - 1] || "basic_v1") !== "advanced_v1") return sortedHand(player.hand)[0];
    let best = null;
    const threats = this.players.filter((candidate) => candidate.seat !== seat && candidate.riichi);
    for (const tile of sortedHand([...new Set(player.hand)])) {
      const hand = player.hand.slice();
      hand.splice(hand.indexOf(tile), 1);
      const result = calculateShanten(tilesToCounts(hand));
      const safe = threats.filter((threat) => threat.river.includes(tile)).length;
      const candidate = { tile, shanten: result.minimum, safe };
      if (!best || candidate.shanten < best.shanten || (candidate.shanten === best.shanten && (candidate.safe > best.safe || (candidate.safe === best.safe && TILE_INDEX.get(tile) < TILE_INDEX.get(best.tile))))) best = candidate;
    }
    return best?.tile || sortedHand(player.hand)[0];
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
        this.pending = { type: "ron", seat: 0, loser: seat, tile: this.players[seat].river.at(-1), options: ["ron", "pass"] };
        this._emit("action.offer", { seat: 0, action: "ron", loser: seat });
        this._emit("state.snapshot", this.publicSnapshot());
        return;
      }
      const calls = this._callOptions(this.players[seat].river.at(-1), seat);
      if (calls.length) {
        this.phase = "player-call";
        this.pending = { type: "call", seat: 0, discarder: seat, tile: this.players[seat].river.at(-1), options: ["pass", ...calls] };
        this._emit("action.offer", { seat: 0, action: "call", options: calls });
        this._emit("state.snapshot", this.publicSnapshot());
        return;
      }
    }
    this.opponentCursor = 1;
    this._drawPlayer();
  }

  _callOptions(tile, discarder) {
    const hand = this.players[0].hand;
    const count = hand.filter((candidate) => candidate === tile).length;
    const options = [];
    if (count >= 2) options.push("pon");
    if (count >= 3) options.push("kan");
    const index = TILE_INDEX.get(tile);
    if (discarder === 3 && index < 27) {
      const suitStart = Math.floor(index / 9) * 9;
      const position = index - suitStart;
      const sequences = [[position - 2, position - 1], [position - 1, position + 1], [position + 1, position + 2]];
      for (const positions of sequences) {
        if (positions.some((value) => value < 0 || value > 8)) continue;
        const needed = positions.map((value) => TILE_NAMES[suitStart + value]);
        if (needed.every((candidate) => hand.includes(candidate))) options.push(`chi:${needed.join(",")}`);
      }
    }
    return options;
  }

  _aiCallOptions(seat, tile, discarder) {
    const hand = this.players[seat].hand;
    const count = hand.filter((candidate) => candidate === tile).length;
    const options = [];
    if (count >= 2) options.push("pon");
    if (count >= 3) options.push("kan");
    if (discarder === (seat + 3) % 4 && TILE_INDEX.get(tile) < 27) options.push("chi");
    return options;
  }

  _resolveAICall(tile, discarder) {
    for (let seat = 1; seat < 4; seat += 1) {
      const options = this._aiCallOptions(seat, tile, discarder);
      if (!options.length) continue;
      const player = this.players[seat];
      const profile = this.ai[seat - 1] || "basic_v1";
      const isValueHonor = TILE_INDEX.get(tile) >= 27;
      const action = profile === "advanced_v1"
        ? (isValueHonor && options.includes("pon") ? "pon" : null)
        : (isValueHonor && options.includes("pon") ? "pon" : null);
      if (!action) continue;
      const needed = action === "pon" ? [tile, tile] : [tile, tile, tile];
      if (!needed.every((candidate) => player.hand.includes(candidate))) continue;
      for (const candidate of needed) player.hand.splice(player.hand.indexOf(candidate), 1);
      player.melds.push({ kind: action, tiles: [tile, ...needed], open: true });
      this._emit("action.call", { seat, kind: action, tile, discarder, ai: profile });
      return true;
    }
    return false;
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
    if (result.minimum === 0 && !player.riichi && player.melds.length === 0) {
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
      if (action === "tsumo") this._settleWin(0, null, "tsumo", pending.tile);
      else this._continueOpponents();
    } else if (pending.type === "ron") {
      if (action === "ron") this._settleWin(0, pending.loser, "ron", pending.tile);
      else this._continueOpponents();
    } else if (pending.type === "call") {
      if (action !== "pass") {
        const tile = pending.tile;
        const player = this.players[0];
        const kind = action.split(":", 1)[0];
        const needed = kind === "pon" ? [tile, tile] : kind === "kan" ? [tile, tile, tile] : action.slice(4).split(",");
        for (const candidate of needed) player.hand.splice(player.hand.indexOf(candidate), 1);
        player.melds.push({ kind, tiles: [tile, ...needed], open: true });
        this.phase = "player-discard";
        this.pending = { type: "discard", seat: 0, options: this.legalDiscards() };
        this._emit("action.call", { seat: 0, kind, tile, discarder: pending.discarder });
      } else {
        this._resolveAICall(pending.tile, pending.discarder);
        this._continueOpponents();
      }
    } else if (pending.type === "next_hand") {
      this.nextHand();
    }
    this._emit("state.snapshot", this.publicSnapshot());
    return this.publicSnapshot();
  }

  _scoreFor(winner, winType, winTile = null) {
    const player = this.players[winner];
    const hand = winType === "ron" && winTile ? [...player.hand, winTile] : [...player.hand];
    return scoreHand({ hand, melds: player.melds, winType, riichi: player.riichi,
      dealer: winner === this.dealer, doraIndicators: this.doraIndicators,
      uraIndicators: this.uraIndicators });
  }

  _settleWin(winner, loser, winType, winTile = null) {
    const score = this._scoreFor(winner, winType, winTile);
    let points;
    if (winType === "ron") {
      points = score.ron;
      this.players[loser].points -= points;
      this.players[winner].points += points;
    } else {
      points = score.tsumo_child;
      for (const player of this.players) {
        if (player.seat === winner) continue;
        const payment = player.seat === this.dealer ? score.tsumo_dealer : score.tsumo_child;
        player.points -= payment;
        this.players[winner].points += payment;
      }
    }
    this.settlement = { winner, loser, win_type: winType, points, dora_indicators: this.doraIndicators, ura_indicators: this.uraIndicators, ...score };
    this.phase = "ended";
    this.pending = { type: "next_hand", options: ["next"] };
    this._emit("hand.finished", { settlement: this.settlement });
  }

  nextHand() {
    if (this.phase !== "ended" || this.matchEnded) throw new Error("当前不能进入下一局。");
    const dealerWon = this.settlement?.winner === this.dealer;
    if (!dealerWon) this.dealer = (this.dealer + 1) % 4;
    this.roundHand += 1;
    if (this.roundHand >= 4) {
      const leaderAboveThirty = Math.max(...this.players.map((player) => player.points)) >= 30000;
      const configuredTarget = this.matchLength === "south" ? 1 : 0;
      if (this.roundWindIndex < configuredTarget || (!leaderAboveThirty && this.roundWindIndex < 2)) {
        this.roundWindIndex += 1;
        this.roundWind = ["E", "S", "W"][this.roundWindIndex];
        this.roundHand = 0;
      } else {
        this.matchEnded = true;
        this.pending = null;
        this._emit("match.finished", { players: this.players.map((player) => ({ seat: player.seat, points: player.points })) });
        return this.publicSnapshot();
      }
    }
    this.wall = makeWall(this.random);
    this.doraIndicators = [this.wall.pop()];
    this.uraIndicators = [this.wall.pop()];
    for (const player of this.players) {
      player.hand = []; player.river = []; player.melds = []; player.riichi = false;
    }
    this.seatWinds = ["E", "S", "W", "N"].map((_, index) => ["E", "S", "W", "N"][(index - this.dealer + 4) % 4]);
    for (let count = 0; count < 13; count += 1) {
      for (const player of this.players) player.hand.push(this.wall.pop());
    }
    this.players.forEach((player) => { player.hand = sortedHand(player.hand); });
    this.phase = "player-discard";
    this.settlement = null;
    this.opponentCursor = 1;
    this._emit("hand.started", { round_wind: this.roundWind, round_hand: this.roundHand, dealer: this.dealer });
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
      ai: [...this.ai],
      temperature: this.temperature,
      phase: this.phase,
      pending: this.pending ? copy(this.pending) : null,
      current_seat: this.currentSeat,
      live_wall_count: this.wall.length,
      dora_indicators: [...this.doraIndicators],
      ura_indicators_hidden: this.uraIndicators.length,
      players: this.players.map((player) => ({
        seat: player.seat, name: player.name, points: player.points,
        concealed_count: player.hand.length,
        hand: player.seat === 0 ? [...player.hand] : null,
        river: [...player.river], riichi: player.riichi,
        melds: copy(player.melds),
        ai: player.seat > 0 ? (this.ai[player.seat - 1] || "basic_v1") : null,
        seat_wind: this.seatWinds?.[player.seat] || "E",
      })),
      last_draw: this.lastDraw,
      settlement: this.settlement ? copy(this.settlement) : null,
      round_hand: this.roundHand,
      round_wind: this.roundWind,
      round_wind_index: this.roundWindIndex,
      match_length: this.matchLength,
      dealer: this.dealer,
      match_ended: this.matchEnded,
    };
  }

  save() {
    return JSON.stringify({
      schema_version: BROWSER_GAME_SCHEMA_VERSION,
      seed: this.seed,
      state: { wall: this.wall, players: this.players, currentSeat: this.currentSeat,
        phase: this.phase, lastDraw: this.lastDraw, pending: this.pending,
        opponentCursor: this.opponentCursor, settlement: this.settlement,
        ai: this.ai, temperature: this.temperature, dealer: this.dealer,
        roundHand: this.roundHand, matchEnded: this.matchEnded,
        roundWind: this.roundWind, roundWindIndex: this.roundWindIndex, matchLength: this.matchLength,
        doraIndicators: this.doraIndicators,
        uraIndicators: this.uraIndicators },
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
    this.ai = Array.isArray(saved.state?.ai) ? [...saved.state.ai] : ["basic_v1", "basic_v1", "basic_v1"];
    this.temperature = Number(saved.state?.temperature ?? 0.2);
    this.matchLength = saved.state?.matchLength === "south" ? "south" : "east";
    this.random = rng(numericSeed(this.seed).value);
    const state = saved.state;
    if (!state || !Array.isArray(state.wall) || !Array.isArray(state.players)) {
      throw new Error("浏览器牌局存档缺少状态。");
    }
    this.wall = [...state.wall];
    this.dealer = Number(state.dealer ?? 0);
    this.roundHand = Number(state.roundHand ?? 0);
    this.matchEnded = Boolean(state.matchEnded);
    this.roundWind = state.roundWind || "E";
    this.roundWindIndex = Number(state.roundWindIndex ?? (["E", "S", "W"].indexOf(this.roundWind)));
    this.doraIndicators = [...(state.doraIndicators || [])];
    this.uraIndicators = [...(state.uraIndicators || [])];
    this.seatWinds = ["E", "S", "W", "N"].map((_, index) => ["E", "S", "W", "N"][(index - this.dealer + 4) % 4]);
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

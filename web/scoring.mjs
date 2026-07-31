import { TILE_NAMES, tilesToCounts } from "./mahjong-core.mjs";

const TILE_INDEX = new Map(TILE_NAMES.map((tile, index) => [tile, index]));
const TERMINALS = new Set([0, 8, 9, 17, 18, 26]);
const HONORS = new Set([27, 28, 29, 30, 31, 32, 33]);
function normalizeTile(tile) { return /^0[mps]$/.test(tile) ? `5${tile[1]}` : tile; }

function nextDora(index) {
  if (index < 27) return Math.floor(index / 9) * 9 + ((index % 9 + 1) % 9);
  if (index < 31) return 27 + ((index - 27 + 1) % 4);
  return 31 + ((index - 31 + 1) % 3);
}

function completeSets(counts, openMelds = 0) {
  const total = counts.reduce((sum, value) => sum + value, 0);
  if (total !== 14 - openMelds * 3) return [];
  const result = [];
  function dfs(state, pair, sets) {
    const index = state.findIndex(Boolean);
    if (index < 0) {
      if (pair && sets.length === 4 - openMelds) result.push(sets.slice());
      return;
    }
    if (!pair && state[index] >= 2) {
      state[index] -= 2; dfs(state, true, sets); state[index] += 2;
    }
    if (state[index] >= 3) {
      state[index] -= 3; sets.push({ kind: "triplet", index }); dfs(state, pair, sets); sets.pop(); state[index] += 3;
    }
    if (index < 27 && index % 9 <= 6 && state[index + 1] && state[index + 2]) {
      state[index] -= 1; state[index + 1] -= 1; state[index + 2] -= 1;
      sets.push({ kind: "sequence", index }); dfs(state, pair, sets); sets.pop();
      state[index] += 1; state[index + 1] += 1; state[index + 2] += 1;
    }
  }
  dfs(counts.slice(), false, []);
  return result;
}

function chiitoi(counts) {
  return counts.reduce((sum, count) => sum + (count === 2 ? 1 : 0), 0) === 7;
}

function kokushi(counts) {
  const required = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33];
  return required.every((index) => counts[index] > 0) && required.some((index) => counts[index] >= 2);
}

function isSimple(index) { return index < 27 && index % 9 > 0 && index % 9 < 8; }

function doraCount(tiles, indicators, redCount = 0) {
  const dora = new Set(indicators.map((tile) => nextDora(TILE_INDEX.get(normalizeTile(tile)))));
  return tiles.reduce((sum, tile) => sum + (dora.has(TILE_INDEX.get(normalizeTile(tile))) ? 1 : 0), redCount);
}

export function scoreHand({
  hand, melds = [], winType = "ron", riichi = false, dealer = false,
  seatWind = "S", roundWind = "E", doraIndicators = [], uraIndicators = [], redCount = 0,
}) {
  const redInHand = [...hand, ...melds.flatMap((meld) => meld.tiles.slice(0, 3))].filter((tile) => /^0[mps]$/.test(tile)).length;
  const allTiles = [...hand, ...melds.flatMap((meld) => meld.tiles.slice(0, 3))].map(normalizeTile);
  const counts = tilesToCounts(allTiles);
  const specialChiitoi = chiitoi(counts);
  const specialKokushi = kokushi(counts);
  const normalizedHand = hand.map(normalizeTile);
  const decomposition = completeSets(tilesToCounts(normalizedHand), melds.length)[0];
  if (!specialChiitoi && !specialKokushi && !decomposition) throw new Error("手牌尚未构成完整和牌。");
  const yaku = [];
  if (riichi) yaku.push("Riichi");
  const closed = melds.every((meld) => !meld.open);
  if (winType === "tsumo" && closed) yaku.push("Menzen Tsumo");
  if (specialChiitoi) yaku.push("Chiitoitsu");
  if (specialKokushi) yaku.push("Kokushi Musou");
  if (allTiles.every((tile) => isSimple(TILE_INDEX.get(tile)))) yaku.push("Tanyao");
  const honorTriplets = new Set();
  for (let index = 27; index < 34; index += 1) if (counts[index] >= 3) honorTriplets.add(index);
  const windIndex = { E: 27, S: 28, W: 29, N: 30 };
  for (const index of honorTriplets) {
    if (index >= 31 || index === windIndex[seatWind] || index === windIndex[roundWind]) yaku.push("Yakuhai");
  }
  if (!specialChiitoi && !specialKokushi && decomposition.every((set) => set.kind === "triplet") && melds.every((meld) => meld.kind !== "chi")) yaku.push("Toitoi");
  const suits = new Set(allTiles.map((tile) => TILE_INDEX.get(tile)).filter((index) => index < 27).map((index) => Math.floor(index / 9)));
  const hasHonor = allTiles.some((tile) => HONORS.has(TILE_INDEX.get(tile)));
  if (suits.size === 1) yaku.push(hasHonor ? "Honitsu" : "Chinitsu");
  const hanFromYaku = yaku.reduce((sum, name) => sum + ({ Riichi: 1, "Menzen Tsumo": 1, Chiitoitsu: 2, "Kokushi Musou": 13, Tanyao: 1, Yakuhai: 1, Toitoi: 2, Honitsu: 3, Chinitsu: 6 }[name] || 0), 0);
  const dora = doraCount(allTiles, doraIndicators, redCount + redInHand);
  const ura = riichi ? doraCount(allTiles, uraIndicators, 0) : 0;
  const han = hanFromYaku + dora + ura;
  if (han <= 0) throw new Error("和牌至少需要一项役种。");
  const fu = specialChiitoi ? 25 : Math.max(20, 20 + (winType === "ron" && closed ? 10 : 0) + (winType === "tsumo" ? 2 : 0));
  const base = Math.min(2000, fu * (2 ** (han + 2)));
  const ron = Math.ceil((base * (dealer ? 6 : 4)) / 100) * 100;
  const tsumoDealer = Math.ceil((base * 2) / 100) * 100;
  const tsumoChild = Math.ceil(base / 100) * 100;
  return { yaku, han, fu, dora, ura, ron, tsumo_dealer: tsumoDealer, tsumo_child: tsumoChild, limit: han >= 13 ? "yakuman" : han >= 11 ? "sanbaiman" : han >= 8 ? "baiman" : han >= 6 ? "haneman" : han >= 5 || base >= 2000 ? "mangan" : "normal" };
}

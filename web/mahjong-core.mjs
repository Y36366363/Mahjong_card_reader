const HONORS = ["E", "S", "W", "N", "P", "F", "C"];
export const TILE_NAMES = [
  ...Array.from({ length: 9 }, (_, i) => `${i + 1}m`),
  ...Array.from({ length: 9 }, (_, i) => `${i + 1}p`),
  ...Array.from({ length: 9 }, (_, i) => `${i + 1}s`),
  ...HONORS,
];
const TILE_INDEX = new Map(TILE_NAMES.map((tile, index) => [tile, index]));
const TERMINAL_HONOR_INDICES = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33];

export function normalizeTile(raw) {
  const tile = raw.trim();
  if (/^0[mps]$/.test(tile)) return `5${tile[1]}`;
  if (TILE_INDEX.has(tile)) return tile;
  throw new Error(`无法识别的牌：${raw}`);
}

export function parseTiles(text) {
  const rawTiles = text.replaceAll(",", " ").trim().split(/\s+/).filter(Boolean);
  const tiles = rawTiles.map(normalizeTile);
  if (![13, 14].includes(tiles.length)) {
    throw new Error(`请输入 13 或 14 张牌；当前为 ${tiles.length} 张。`);
  }
  const counts = tilesToCounts(tiles);
  const impossible = counts.findIndex((count) => count > 4);
  if (impossible >= 0) {
    throw new Error(`${TILE_NAMES[impossible]} 超过四张。`);
  }
  return { rawTiles, tiles, counts };
}

export function tilesToCounts(tiles) {
  const counts = Array(34).fill(0);
  for (const tile of tiles) {
    const index = TILE_INDEX.get(tile);
    if (index === undefined) throw new Error(`无法识别的牌：${tile}`);
    counts[index] += 1;
  }
  return counts;
}

export function shantenChiitoitsu(counts) {
  const pairs = Math.min(7, counts.reduce((sum, count) => sum + Math.floor(count / 2), 0));
  const unique = counts.filter(Boolean).length;
  return 6 - pairs + Math.max(0, 7 - unique);
}

export function shantenKokushi(counts) {
  const unique = TERMINAL_HONOR_INDICES.filter((index) => counts[index] > 0).length;
  const hasPair = TERMINAL_HONOR_INDICES.some((index) => counts[index] >= 2);
  return 13 - unique - (hasPair ? 1 : 0);
}

function shantenStandardGeneral(counts) {
  const memo = new Map();
  function dfs(state, melds, shapes, pairUsed) {
    const key = `${state.join("")}|${melds}|${shapes}|${pairUsed}`;
    if (memo.has(key)) return memo.get(key);
    const index = state.findIndex(Boolean);
    const effectiveShapes = Math.min(shapes, Math.max(0, 4 - melds));
    let result = 8 - 2 * melds - effectiveShapes - pairUsed;
    if (index < 0) return result;

    const next = state.slice();
    next[index] -= 1;
    result = Math.min(result, dfs(next, melds, shapes, pairUsed));

    if (state[index] >= 3) {
      const triplet = state.slice();
      triplet[index] -= 3;
      result = Math.min(result, dfs(triplet, melds + 1, shapes, pairUsed));
    }
    if (index <= 26 && index % 9 <= 6 && state[index + 1] && state[index + 2]) {
      const sequence = state.slice();
      sequence[index] -= 1; sequence[index + 1] -= 1; sequence[index + 2] -= 1;
      result = Math.min(result, dfs(sequence, melds + 1, shapes, pairUsed));
    }
    if (!pairUsed && state[index] >= 2) {
      const pair = state.slice();
      pair[index] -= 2;
      result = Math.min(result, dfs(pair, melds, shapes, 1));
    }
    if (shapes < 4) {
      if (state[index] >= 2) {
        const pairShape = state.slice();
        pairShape[index] -= 2;
        result = Math.min(result, dfs(pairShape, melds, shapes + 1, pairUsed));
      }
      if (index <= 26 && index % 9 <= 7 && state[index + 1]) {
        const adjacent = state.slice();
        adjacent[index] -= 1; adjacent[index + 1] -= 1;
        result = Math.min(result, dfs(adjacent, melds, shapes + 1, pairUsed));
      }
      if (index <= 26 && index % 9 <= 6 && state[index + 2]) {
        const gap = state.slice();
        gap[index] -= 1; gap[index + 2] -= 1;
        result = Math.min(result, dfs(gap, melds, shapes + 1, pairUsed));
      }
    }
    memo.set(key, result);
    return result;
  }
  return dfs(counts.slice(), 0, 0, 0);
}

export function shantenStandard(counts) {
  if (counts.reduce((sum, count) => sum + count, 0) !== 14) {
    return shantenStandardGeneral(counts);
  }
  let best = 8;
  for (let index = 0; index < 34; index += 1) {
    if (!counts[index]) continue;
    const afterDiscard = counts.slice();
    afterDiscard[index] -= 1;
    best = Math.min(best, shantenStandardGeneral(afterDiscard));
  }
  return best;
}

export function calculateShanten(counts) {
  const standard = shantenStandard(counts);
  const chiitoitsu = shantenChiitoitsu(counts);
  const kokushi = shantenKokushi(counts);
  return { standard, chiitoitsu, kokushi, minimum: Math.min(standard, chiitoitsu, kokushi) };
}

export function effectiveTiles(counts, currentMinimum) {
  if (counts.reduce((sum, count) => sum + count, 0) !== 13) return [];
  const result = [];
  for (let index = 0; index < 34; index += 1) {
    if (counts[index] >= 4) continue;
    const drawn = counts.slice();
    drawn[index] += 1;
    const next = Math.min(
      shantenStandardGeneral(drawn),
      shantenChiitoitsu(drawn),
      shantenKokushi(drawn),
    );
    if (next < currentMinimum) {
      result.push({ tile: TILE_NAMES[index], remaining: 4 - counts[index] });
    }
  }
  return result;
}

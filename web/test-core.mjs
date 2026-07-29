import assert from "node:assert/strict";
import { calculateShanten, effectiveTiles, parseTiles } from "./mahjong-core.mjs";

const cases = [
  ["1m 2m 3m 4m 5m 6m 2p 3p 4p 6s 7s E E", [0, 5, 10]],
  ["1m 1m 2m 2m 3p 3p 4p 4p 5s 5s E E C", [3, 0, 9]],
  ["1m 9m 1p 9p 1s 9s E S W N P F C", [8, 6, 0]],
];

for (const [hand, expected] of cases) {
  const { counts } = parseTiles(hand);
  const result = calculateShanten(counts);
  assert.deepEqual(
    [result.standard, result.chiitoitsu, result.kokushi],
    expected,
    hand,
  );
}

const sample = parseTiles(cases[0][0]);
assert.deepEqual(
  effectiveTiles(sample.counts, 0),
  [{ tile: "5s", remaining: 4 }, { tile: "8s", remaining: 4 }],
);
assert.throws(
  () => parseTiles("1m 1m 1m 1m 1m 2m 3m 4m 5m 6m 7m 8m 9m"),
  /超过四张/,
);

console.log("Browser shanten core tests passed.");

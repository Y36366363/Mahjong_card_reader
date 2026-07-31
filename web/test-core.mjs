import assert from "node:assert/strict";
import { calculateShanten, effectiveTiles, parseTiles } from "./mahjong-core.mjs";
import { BrowserMatch } from "./game-engine.mjs";

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

const match = new BrowserMatch({ seed: 20260731 });
assert.equal(match.publicSnapshot().players[0].hand.length, 14);
assert.equal(match.publicSnapshot().live_wall_count, 83);
const before = match.events.length;
const discard = match.legalDiscards()[0];
match.discard(discard);
assert.ok(match.events.length > before);
assert.equal(match.publicSnapshot().players[0].river.length, 1);
const restored = BrowserMatch.fromJSON(match.save());
assert.deepEqual(restored.publicSnapshot(), match.publicSnapshot());
assert.equal(restored.events.length, match.events.length);

const callMatch = new BrowserMatch({ seed: 8, ai: ["advanced_v1", "basic_v1", "basic_v1"] });
callMatch.players[0].hand = ["1m", "1m", "2m", "3m"];
assert.ok(callMatch._callOptions("1m", 1).includes("pon"));
callMatch.pending = { type: "call", seat: 0, discarder: 1, tile: "1m", options: ["pass", "pon"] };
callMatch.respond("pon");
assert.equal(callMatch.players[0].melds.at(-1).kind, "pon");
assert.equal(callMatch.players[0].hand.length, 2);
assert.equal(callMatch.publicSnapshot().players[1].ai, "advanced_v1");

console.log("Browser shanten and match engine tests passed.");

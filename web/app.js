import { calculateShanten, effectiveTiles, parseTiles } from "./mahjong-core.mjs";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const STORAGE_KEY = "mahjong-card-reader-web-settings-v1";
const HONOR_LABELS = { E: "东", S: "南", W: "西", N: "北", P: "白", F: "发", C: "中" };

function tileLabel(tile) {
  if (HONOR_LABELS[tile]) return HONOR_LABELS[tile];
  const suit = { m: "万", p: "筒", s: "索" }[tile.at(-1)];
  return `${tile[0] === "0" ? "赤5" : tile[0]}${suit}`;
}

function renderTiles(rawTiles) {
  $("#hand-tiles").replaceChildren(...rawTiles.map((rawTile) => {
    const normalized = /^0[mps]$/.test(rawTile) ? `5${rawTile[1]}` : rawTile;
    const element = document.createElement("span");
    element.className = `tile ${normalized.length === 2 ? normalized[1] : "honor"}`;
    element.textContent = tileLabel(rawTile);
    return element;
  }));
}

function analyze() {
  const error = $("#analysis-error");
  error.textContent = "";
  try {
    const { rawTiles, counts } = parseTiles($("#hand-input").value);
    const result = calculateShanten(counts);
    renderTiles(rawTiles);
    $("#minimum-result").textContent = result.minimum;
    $("#standard-result").textContent = result.standard;
    $("#chiitoi-result").textContent = result.chiitoitsu;
    $("#kokushi-result").textContent = result.kokushi;
    $("#analysis-result").hidden = false;
    const effective = effectiveTiles(counts, result.minimum);
    const effectiveBox = $("#effective-result");
    effectiveBox.hidden = counts.reduce((sum, count) => sum + count, 0) !== 13;
    if (!effectiveBox.hidden) {
      const total = effective.reduce((sum, item) => sum + item.remaining, 0);
      effectiveBox.textContent = effective.length
        ? `有效牌：${effective.map((item) => `${tileLabel(item.tile)}×${item.remaining}`).join("、")}（共 ${total} 张）`
        : "当前没有能够降低综合向听数的进张。";
    }
    $("#analysis-status").textContent = result.minimum === 0 ? "听牌" : `${result.minimum} 向听`;
  } catch (caught) {
    error.textContent = caught instanceof Error ? caught.message : String(caught);
    $("#analysis-result").hidden = true;
    $("#effective-result").hidden = true;
    $("#hand-tiles").replaceChildren();
    $("#analysis-status").textContent = "输入有误";
  }
}

function settingsSnapshot() {
  return {
    language: $("#language-setting").value,
    match: $("#match-setting").value,
    assist: $("#assist-setting").value,
    seed: $("#seed-setting").value,
    ai: $$(".ai-setting").map((element) => element.value),
    temperature: $("#temperature-setting").value,
  };
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settingsSnapshot()));
  $("#temperature-output").textContent = Number($("#temperature-setting").value).toFixed(2);
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!saved) return;
    $("#language-setting").value = saved.language || "zh";
    $("#match-setting").value = saved.match || "east";
    $("#assist-setting").value = saved.assist || "hint";
    $("#seed-setting").value = saved.seed || "";
    $$(".ai-setting").forEach((element, index) => { element.value = saved.ai?.[index] || "basic_v1"; });
    $("#temperature-setting").value = saved.temperature || "0.2";
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function tileBacks(count) {
  return Array.from({ length: count }, () => {
    const back = document.createElement("span");
    back.className = "back";
    return back;
  });
}

function renderPlayer(panel, name, wind, profile, count) {
  const header = document.createElement("div");
  header.className = "player-header";
  header.innerHTML = `<span>${name}</span><span>25,000</span>`;
  const subtitle = document.createElement("p");
  subtitle.className = "player-subtitle";
  subtitle.textContent = `自风 ${wind} · ${profile === "advanced_v1" ? "Advanced AI v1" : "Basic AI v1"}`;
  const backs = document.createElement("div");
  backs.className = "backs";
  backs.replaceChildren(...tileBacks(count));
  panel.replaceChildren(header, subtitle, backs);
}

function renderTable() {
  const settings = settingsSnapshot();
  const profiles = ["玩家", ...settings.ai];
  const winds = ["东", "南", "西", "北"];
  $$(".player").forEach((panel) => {
    const seat = Number(panel.dataset.seat);
    renderPlayer(panel, seat ? `电脑${seat}` : "玩家", winds[seat], profiles[seat], seat ? 13 : 14);
  });
  $("#round-preview").textContent = `${settings.match === "south" ? "南风战 · " : ""}东 1 局`;
  saveSettings();
}

$("#analyze-button").addEventListener("click", analyze);
$("#clear-button").addEventListener("click", () => {
  $("#hand-input").value = "";
  $("#hand-tiles").replaceChildren();
  $("#analysis-result").hidden = true;
  $("#effective-result").hidden = true;
  $("#analysis-error").textContent = "";
  $("#analysis-status").textContent = "等待输入";
});
$("#preview-button").addEventListener("click", renderTable);
$$(".settings-panel input, .settings-panel select").forEach((element) => {
  element.addEventListener("change", saveSettings);
  element.addEventListener("input", saveSettings);
});

loadSettings();
renderTable();
analyze();

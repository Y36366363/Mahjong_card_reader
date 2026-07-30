import { calculateShanten, effectiveTiles, parseTiles } from "./mahjong-core.mjs";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const STORAGE_KEY = "mahjong-card-reader-web-settings-v1";
const HONOR_LABELS = { E: "东", S: "南", W: "西", N: "北", P: "白", F: "发", C: "中" };
const TEXT = {
  zh: {
    heroTitle: "单机立直麻将助手", heroCopy: "无需安装 Python，直接在浏览器中分析手牌并预览未来的完整对局界面。", openSettings: "进入牌局设置", viewProject: "查看 GitHub 项目", playableNow: "PLAYABLE NOW", assistantTitle: "向听与有效牌助手", handLabel: "输入 13 或 14 张牌", fieldHelp: "万子 1m–9m、筒子 1p–9p、索子 1s–9s；字牌 E S W N P F C；支持赤五 0m/0p/0s。", analyze: "开始分析", clear: "清空", minimum: "综合向听", standard: "一般型", chiitoi: "七对子", kokushi: "国士无双", matchSetup: "MATCH SETUP", settingsTitle: "未来网页版对局设置", autosave: "自动保存", languageLabel: "语言", matchLabel: "对局长度", eastMatch: "东风战", southMatch: "南风战", assistLabel: "辅助模式", hintMode: "提示模式", normalMode: "普通模式", seedLabel: "固定种子（可选）", seedPlaceholder: "留空则随机", rightAI: "右家电脑", oppositeAI: "对家电脑", leftAI: "左家电脑", temperatureLabel: "AI 温度", preview: "更新牌桌预览", shareSettings: "复制设置链接", shareCopied: "设置链接已复制，可分享给其他人。", shareUnavailable: "复制失败，请手动复制当前地址。", responsiveTable: "RESPONSIVE TABLE", tableTitle: "网页版牌桌预览", nextPhase: "规则状态机下一阶段接入", roadmapEntry: "网页入口", roadmapEntryCopy: "静态页面、响应式牌桌、设置保存与向听助手已经可部署。", roadmapEngine: "结构化牌局引擎", roadmapEngineCopy: "把同步 input 提示改为状态快照与合法行动，供桌面和网页共同调用。", roadmapGame: "完整单机对局", roadmapGameCopy: "接入吃碰杠、立直、振听、结算、Advanced AI v1 和回放种子.", waiting: "等待输入", invalid: "输入有误", tenpai: "听牌", shanten: "向听", effective: "有效牌", noEffective: "当前没有能够降低综合向听数的进张。", total: "共", player: "玩家", computer: "电脑", selfWind: "自风", round: "局", basic: "Basic AI v1", advanced: "Advanced AI v1", roundEast: "东 1 局", roundSouth: "南风战 · 东 1 局", centerStats: "本场 0 · 立直棒 0", wall: "牌山 70", dora: "宝牌 —"
  },
  en: {
    heroTitle: "Riichi Mahjong Assistant", heroCopy: "Analyze a hand and preview the future full match interface directly in your browser—no Python installation required.", openSettings: "Open match settings", viewProject: "View GitHub project", playableNow: "PLAYABLE NOW", assistantTitle: "Shanten & Effective Tiles", handLabel: "Enter 13 or 14 tiles", fieldHelp: "Suits: 1m–9m, 1p–9p, 1s–9s; honors: E S W N P F C; red fives 0m/0p/0s are supported.", analyze: "Analyze hand", clear: "Clear", minimum: "Minimum shanten", standard: "Standard", chiitoi: "Seven pairs", kokushi: "Thirteen orphans", matchSetup: "MATCH SETUP", settingsTitle: "Browser match settings", autosave: "Saved automatically", languageLabel: "Language", matchLabel: "Match length", eastMatch: "East match", southMatch: "South match", assistLabel: "Assist mode", hintMode: "Hint mode", normalMode: "Normal mode", seedLabel: "Fixed seed (optional)", seedPlaceholder: "Blank = random", rightAI: "Right AI", oppositeAI: "Opposite AI", leftAI: "Left AI", temperatureLabel: "AI temperature", preview: "Update table preview", shareSettings: "Copy settings link", shareCopied: "Settings link copied. You can share it with others.", shareUnavailable: "Copy failed. Please copy the current address manually.", responsiveTable: "RESPONSIVE TABLE", tableTitle: "Browser table preview", nextPhase: "Rules engine in next phase", roadmapEntry: "Web entry", roadmapEntryCopy: "Static page, responsive table, saved settings, and shanten assistant are deployable now.", roadmapEngine: "Structured game engine", roadmapEngineCopy: "Replace synchronous input prompts with state snapshots and legal actions shared by desktop and web.", roadmapGame: "Full single-player match", roadmapGameCopy: "Add calls, riichi, furiten, settlement, Advanced AI v1, and seeded replays.", waiting: "Waiting for input", invalid: "Invalid input", tenpai: "Tenpai", shanten: "shanten", effective: "Effective tiles", noEffective: "No draw currently lowers the minimum shanten.", total: "total", player: "Player", computer: "Computer", selfWind: "Seat", round: "", basic: "Basic AI v1", advanced: "Advanced AI v1", roundEast: "East 1", roundSouth: "South match · East 1", centerStats: "Honba 0 · Riichi 0", wall: "Wall 70", dora: "Dora —"
  },
  ja: {
    heroTitle: "一人用リーチ麻雀アシスタント", heroCopy: "Python をインストールせず、ブラウザで手牌を分析し、将来の対局画面を確認できます。", openSettings: "対局設定を開く", viewProject: "GitHub プロジェクト", playableNow: "PLAYABLE NOW", assistantTitle: "シャンテン数・有効牌アシスタント", handLabel: "13 枚または 14 枚を入力", fieldHelp: "数牌: 1m–9m、1p–9p、1s–9s；字牌: E S W N P F C；赤5 0m/0p/0s 対応。", analyze: "手牌を分析", clear: "クリア", minimum: "最小シャンテン", standard: "一般形", chiitoi: "七対子", kokushi: "国士無双", matchSetup: "MATCH SETUP", settingsTitle: "ブラウザ対局設定", autosave: "自動保存", languageLabel: "言語", matchLabel: "対局長さ", eastMatch: "東風戦", southMatch: "南風戦", assistLabel: "アシスト", hintMode: "ヒントモード", normalMode: "通常モード", seedLabel: "固定シード（任意）", seedPlaceholder: "空欄 = ランダム", rightAI: "右家 AI", oppositeAI: "対面 AI", leftAI: "左家 AI", temperatureLabel: "AI 温度", preview: "卓プレビューを更新", shareSettings: "設定リンクをコピー", shareCopied: "設定リンクをコピーしました。共有できます。", shareUnavailable: "コピーできませんでした。現在のアドレスを手動でコピーしてください。", responsiveTable: "RESPONSIVE TABLE", tableTitle: "ブラウザ卓プレビュー", nextPhase: "ルールエンジンは次の段階", roadmapEntry: "ウェブ入口", roadmapEntryCopy: "静的ページ、レスポンシブ卓、設定保存、シャンテン数アシスタントを利用できます。", roadmapEngine: "構造化対局エンジン", roadmapEngineCopy: "同期 input を状態スナップショットと合法アクションに置き換え、デスクトップとウェブで共有します。", roadmapGame: "完全な一人用対局", roadmapGameCopy: "鳴き、リーチ、フリテン、精算、Advanced AI v1、シードリプレイを追加します。", waiting: "入力待ち", invalid: "入力エラー", tenpai: "テンパイ", shanten: "シャンテン", effective: "有効牌", noEffective: "シャンテン数を下げるツモはありません。", total: "合計", player: "プレイヤー", computer: "コンピューター", selfWind: "自風", round: "局", basic: "Basic AI v1", advanced: "Advanced AI v1", roundEast: "東 1 局", roundSouth: "南風戦 · 東 1 局", centerStats: "本場 0 · リーチ棒 0", wall: "山 70", dora: "ドラ —"
  },
};
TEXT.zh.skipToContent = "跳到主要内容";
TEXT.en.skipToContent = "Skip to main content";
TEXT.ja.skipToContent = "本文へ移動";
let currentLanguage = "zh";
const t = (key) => TEXT[currentLanguage]?.[key] ?? TEXT.zh[key] ?? key;

function applyLanguage() {
  currentLanguage = $("#language-setting").value || "zh";
  document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : currentLanguage;
  document.title = currentLanguage === "en"
    ? "Mahjong Card Reader · Browser Assistant"
    : currentLanguage === "ja"
      ? "Mahjong Card Reader · 麻雀アシスタント"
      : "Mahjong Card Reader · 浏览器版";
  $$('[data-i18n]').forEach((element) => { element.textContent = t(element.dataset.i18n); });
  $$('[data-i18n-placeholder]').forEach((element) => { element.placeholder = t(element.dataset.i18nPlaceholder); });
  $("#analysis-status").textContent = t("waiting");
  renderTable();
}

function tileLabel(tile) {
  if (currentLanguage === "en") return tile;
  if (currentLanguage === "ja") {
    const honors = { E: "東", S: "南", W: "西", N: "北", P: "白", F: "發", C: "中" };
    if (honors[tile]) return honors[tile];
    return `${tile[0] === "0" ? "赤5" : tile[0]}${{ m: "萬", p: "筒", s: "索" }[tile.at(-1)]}`;
  }
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
    element.setAttribute("role", "img");
    element.setAttribute("aria-label", tileLabel(rawTile));
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
        ? `${t("effective")}：${effective.map((item) => `${tileLabel(item.tile)}×${item.remaining}`).join(currentLanguage === "en" ? ", " : "、")}（${t("total")} ${total}）`
        : t("noEffective");
    }
    $("#analysis-status").textContent = result.minimum === 0 ? t("tenpai") : `${result.minimum} ${t("shanten")}`;
  } catch (caught) {
    error.textContent = caught instanceof Error ? caught.message : String(caught);
    $("#analysis-result").hidden = true;
    $("#effective-result").hidden = true;
    $("#hand-tiles").replaceChildren();
    $("#analysis-status").textContent = t("invalid");
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

function applySettings(saved) {
  if (!saved) return;
  $("#language-setting").value = TEXT[saved.language] ? saved.language : "zh";
  $("#match-setting").value = ["east", "south"].includes(saved.match) ? saved.match : "east";
  $("#assist-setting").value = ["hint", "normal"].includes(saved.assist) ? saved.assist : "hint";
  $("#seed-setting").value = saved.seed || "";
  $$(".ai-setting").forEach((element, index) => { element.value = saved.ai?.[index] || "basic_v1"; });
  const temperature = Number(saved.temperature);
  $("#temperature-setting").value = Number.isFinite(temperature) ? Math.min(1, Math.max(0, temperature)) : 0.2;
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    const hashValue = location.hash.startsWith("#settings=")
      ? JSON.parse(decodeURIComponent(location.hash.slice("#settings=".length)))
      : null;
    applySettings(hashValue || saved);
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

async function shareSettings() {
  const url = `${location.origin}${location.pathname}#settings=${encodeURIComponent(JSON.stringify(settingsSnapshot()))}`;
  try {
    await navigator.clipboard.writeText(url);
    $("#share-status").textContent = t("shareCopied");
  } catch {
    $("#share-status").textContent = `${t("shareUnavailable")} ${url}`;
  }
}

function tileBacks(count) {
  return Array.from({ length: count }, () => {
    const back = document.createElement("span");
    back.className = "back";
    back.setAttribute("aria-hidden", "true");
    return back;
  });
}

function renderPlayer(panel, name, wind, profile, count) {
  panel.setAttribute("aria-label", name);
  const header = document.createElement("div");
  header.className = "player-header";
  header.innerHTML = `<span>${name}</span><span>25,000</span>`;
  const subtitle = document.createElement("p");
  subtitle.className = "player-subtitle";
  subtitle.textContent = `${t("selfWind")} ${wind} · ${profile === "advanced_v1" ? t("advanced") : t("basic")}`;
  const backs = document.createElement("div");
  backs.className = "backs";
  backs.replaceChildren(...tileBacks(count));
  panel.replaceChildren(header, subtitle, backs);
}

function renderTable() {
  const settings = settingsSnapshot();
  const profiles = ["玩家", ...settings.ai];
  const winds = currentLanguage === "en" ? ["East", "South", "West", "North"] : ["东", "南", "西", "北"];
  $$(".player").forEach((panel) => {
    const seat = Number(panel.dataset.seat);
    renderPlayer(panel, seat ? `${t("computer")}${seat}` : t("player"), winds[seat], profiles[seat], seat ? 13 : 14);
  });
  $("#round-preview").textContent = settings.match === "south" ? t("roundSouth") : t("roundEast");
  const centerLines = $(".table-center").querySelectorAll("span");
  centerLines[0].textContent = t("centerStats");
  centerLines[1].textContent = t("wall");
  centerLines[2].textContent = t("dora");
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
  $("#analysis-status").textContent = t("waiting");
});
$("#preview-button").addEventListener("click", renderTable);
$("#share-settings-button").addEventListener("click", shareSettings);
$$(".settings-panel input, .settings-panel select").forEach((element) => {
  const persistSetting = () => {
    saveSettings();
    if (element.id === "language-setting") applyLanguage();
  };
  element.addEventListener("change", persistSetting);
  element.addEventListener("input", persistSetting);
});

loadSettings();
applyLanguage();
renderTable();
analyze();

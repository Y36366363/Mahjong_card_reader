import { calculateShanten, effectiveTiles, parseTiles } from "./mahjong-core.mjs";
import { BrowserMatch } from "./game-engine.mjs";

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
Object.assign(TEXT.zh, { backgroundLabel: "背景", backgroundFelt: "0 - 默认", backgroundAsset1: "1 - 天才麻将少女", backgroundAsset2: "2 - 辉夜大小姐", backgroundAsset3: "3 - Re:Zero", backgroundUploaded: "本地上传图片", uploadBackground: "选择本地背景图片（可选）", backgroundHelp: "项目图片请放入 web/assets/backgrounds/，对应 1/2/3 选项。" });
Object.assign(TEXT.en, { backgroundLabel: "Background", backgroundFelt: "0 - Default", backgroundAsset1: "1 - Saki", backgroundAsset2: "2 - Kaguya-sama", backgroundAsset3: "3 - Re:Zero", backgroundUploaded: "Uploaded image", uploadBackground: "Choose a local background image (optional)", backgroundHelp: "Put project images in web/assets/backgrounds/ for options 1/2/3." });
Object.assign(TEXT.ja, { backgroundLabel: "背景", backgroundFelt: "0 - デフォルト", backgroundAsset1: "1 - 咲-Saki-", backgroundAsset2: "2 - かぐや様は告らせたい", backgroundAsset3: "3 - Re:ゼロ", backgroundUploaded: "アップロード画像", uploadBackground: "ローカル背景画像を選択（任意）", backgroundHelp: "プロジェクト画像は web/assets/backgrounds/ に置くと 1/2/3 で選べます。" });
Object.assign(TEXT.zh, { browserGameTitle: "浏览器牌局（实验阶段）", browserGameCopy: "使用固定种子开始可保存、可回放的浏览器牌局；其他三家可选择 Basic 或 Advanced AI v1。", browserStart: "开始浏览器牌局", browserSave: "下载存档", browserLoad: "读取存档", browserHand: "你的手牌", browserStatus: "牌局状态", browserNoGame: "尚未开始牌局", browserDiscard: "选择要打出的牌", browserSaved: "存档已下载", browserLoaded: "存档已读取", browserRiver: "牌河", browserRiichi: "立直", browserTsumo: "自摸", browserRon: "荣和", browserPon: "碰", browserChi: "吃", browserKan: "杠", browserCall: "鸣牌", browserPass: "跳过", browserNextHand: "确认进入下一局", browserFinal: "对局结束", browserSettlement: "本局结算", browserReplay: "事件回放", browserPrev: "上一事件", browserNext: "下一事件", browserReset: "回到最新", browserReplayState: "牌桌状态", browserLocalAI: "请求本地 AI 建议", browserLocalAIPending: "正在请求本地 AI…", browserLocalAIUnavailable: "本地 AI 服务不可用，请先启动 ai_advisor_server.py。" });
Object.assign(TEXT.en, { browserGameTitle: "Browser match (experimental)", browserGameCopy: "Start a seeded, saveable and replayable browser match with Basic or Advanced AI v1 seats.", browserStart: "Start browser match", browserSave: "Download save", browserLoad: "Load save", browserHand: "Your hand", browserStatus: "Match status", browserNoGame: "No match started", browserDiscard: "Choose a discard", browserSaved: "Save downloaded", browserLoaded: "Save loaded", browserRiver: "River", browserRiichi: "Riichi", browserTsumo: "Tsumo", browserRon: "Ron", browserPon: "Pon", browserChi: "Chi", browserKan: "Kan", browserCall: "Call", browserPass: "Pass", browserNextHand: "Continue to next hand", browserFinal: "Match complete", browserSettlement: "Hand settlement", browserReplay: "Event replay", browserPrev: "Previous event", browserNext: "Next event", browserReset: "Latest event", browserReplayState: "Table state", browserLocalAI: "Ask local AI for a hint", browserLocalAIPending: "Requesting local AI…", browserLocalAIUnavailable: "Local AI service unavailable. Start ai_advisor_server.py first." });
Object.assign(TEXT.ja, { browserGameTitle: "ブラウザ対局（試験版）", browserGameCopy: "固定シードで保存・再生できるブラウザ対局。Basic / Advanced AI v1 を選択できます。", browserStart: "ブラウザ対局を開始", browserSave: "セーブをダウンロード", browserLoad: "セーブを読み込む", browserHand: "あなたの手牌", browserStatus: "対局状態", browserNoGame: "対局は未開始です", browserDiscard: "捨てる牌を選択", browserSaved: "セーブをダウンロードしました", browserLoaded: "セーブを読み込みました", browserRiver: "捨て牌", browserRiichi: "リーチ", browserTsumo: "ツモ", browserRon: "ロン", browserPon: "ポン", browserChi: "チー", browserKan: "カン", browserCall: "鳴き", browserPass: "見逃す", browserNextHand: "次の局へ", browserFinal: "対局終了", browserSettlement: "局の精算", browserReplay: "イベント再生", browserPrev: "前のイベント", browserNext: "次のイベント", browserReset: "最新へ", browserReplayState: "卓の状態", browserLocalAI: "ローカル AI に提案を依頼", browserLocalAIPending: "ローカル AI に問い合わせ中…", browserLocalAIUnavailable: "ローカル AI サービスが利用できません。先に ai_advisor_server.py を起動してください。" });
let currentLanguage = "zh";
const t = (key) => TEXT[currentLanguage]?.[key] ?? TEXT.zh[key] ?? key;
const BACKGROUND_STORAGE_KEY = "mahjong-card-reader-web-background-v1";
const BACKGROUND_ASSETS = {
  "asset-1": "assets/backgrounds/background-1.jpg",
  "asset-2": "assets/backgrounds/background-2.jpg",
  "asset-3": "assets/backgrounds/background-3.jpg",
};
const BACKGROUND_PRESETS = {
  default: "linear-gradient(180deg, #edf3ef 0, #f8f5ed 46rem)",
  felt: "linear-gradient(180deg, #edf3ef 0, #f8f5ed 46rem)",
};
const BROWSER_SAVE_KEY = "mahjong-card-reader-browser-match-v1";
let browserMatch = null;
let replayIndex = -1;

function playBrowserSound(kind = "action") {
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;
  try {
    const context = new AudioContextClass();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = kind === "win" ? 880 : kind === "call" ? 660 : 520;
    gain.gain.setValueAtTime(0.035, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.12);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.12);
    oscillator.addEventListener("ended", () => context.close());
  } catch {
    // Audio is an enhancement; browsers may block it until a user gesture.
  }
}

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

function applyBackground(value) {
  value = value === "felt" ? "default" : value;
  if (!BACKGROUND_PRESETS[value] && !BACKGROUND_ASSETS[value] && value !== "uploaded") {
    value = "default";
  }
  document.body.style.backgroundAttachment = "scroll";
  const preset = BACKGROUND_PRESETS[value];
  if (preset) {
    document.body.style.backgroundImage = preset;
    document.body.style.backgroundSize = "auto";
    return;
  }
  const asset = BACKGROUND_ASSETS[value];
  if (asset) {
    document.body.style.backgroundImage = `linear-gradient(rgba(8, 39, 31, .18), rgba(8, 39, 31, .18)), url("${asset}")`;
    document.body.style.backgroundSize = "cover";
    document.body.style.backgroundAttachment = "fixed";
    return;
  }
  const uploaded = localStorage.getItem(BACKGROUND_STORAGE_KEY);
  if (uploaded) {
    document.body.style.backgroundImage = `linear-gradient(rgba(8, 39, 31, .18), rgba(8, 39, 31, .18)), url("${uploaded}")`;
    document.body.style.backgroundSize = "cover";
    document.body.style.backgroundAttachment = "fixed";
    return;
  }
  document.body.style.backgroundImage = BACKGROUND_PRESETS.default;
  document.body.style.backgroundSize = "auto";
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
    background: $("#background-setting").value,
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
  const savedBackground = saved.background === "felt" ? "default" : saved.background;
  $("#background-setting").value = ["default", "asset-1", "asset-2", "asset-3", "uploaded"].includes(savedBackground)
    ? savedBackground : "default";
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

function handleBackgroundFile(event) {
  const [file] = event.target.files || [];
  if (!file || !file.type.startsWith("image/")) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    localStorage.setItem(BACKGROUND_STORAGE_KEY, String(reader.result));
    applyBackground("uploaded");
    $("#background-setting").value = "uploaded";
    saveSettings();
  });
  reader.readAsDataURL(file);
}

function tileBacks(count) {
  return Array.from({ length: count }, () => {
    const back = document.createElement("span");
    back.className = "back";
    back.setAttribute("aria-hidden", "true");
    return back;
  });
}

function browserTileButton(tile, index) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "browser-tile-button tile";
  button.textContent = tileLabel(tile);
  button.setAttribute("aria-label", `${t("browserDiscard")}: ${tileLabel(tile)}`);
  button.disabled = !browserMatch || browserMatch.phase !== "player-discard";
  button.addEventListener("click", () => {
    try {
      browserMatch.discard(index);
      playBrowserSound("action");
      localStorage.setItem(BROWSER_SAVE_KEY, browserMatch.save());
      renderBrowserMatch();
    } catch (error) {
      $("#browser-match-status").textContent = error instanceof Error ? error.message : String(error);
    }
  });
  return button;
}

async function requestBrowserAI() {
  if (!browserMatch) return;
  const status = $("#browser-match-status");
  status.textContent = t("browserLocalAIPending");
  try {
    const snapshot = browserMatch.publicSnapshot();
    const response = await fetch("http://127.0.0.1:8766/recommend", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hand: snapshot.players[0].hand, snapshot, legal_actions: snapshot.pending?.options || [] }),
    });
    if (!response.ok) throw new Error("local service error");
    const data = await response.json();
    const recommendation = data.recommendation || data.message || "—";
    status.textContent = `${t("browserStatus")} · ${recommendation}`;
  } catch {
    status.textContent = t("browserLocalAIUnavailable");
  }
}

function renderBrowserMatch() {
  const status = $("#browser-match-status");
  const hand = $("#browser-hand");
  const rivers = $("#browser-rivers");
  const actions = $("#browser-actions");
  const settlement = $("#browser-settlement");
  if (!browserMatch) {
    status.textContent = t("browserNoGame");
    hand.replaceChildren();
    rivers.replaceChildren();
    actions.replaceChildren();
    settlement.replaceChildren();
    $("#browser-replay-list").replaceChildren();
    return;
  }
  const snapshot = browserMatch.publicSnapshot();
  const pendingLabels = { riichi: t("browserRiichi"), tsumo: t("browserTsumo"), ron: t("browserRon"), call: t("browserCall"), next_hand: t("browserNextHand"), discard: t("browserDiscard") };
  status.textContent = `${t("browserStatus")} · ${pendingLabels[snapshot.pending?.type] || snapshot.phase} · ${t("wall")} ${snapshot.live_wall_count}`;
  hand.replaceChildren(...snapshot.players[0].hand.map((tile, index) => browserTileButton(tile, index)));
  rivers.replaceChildren(...snapshot.players.slice(1).map((player) => {
    const row = document.createElement("div");
    row.className = "browser-river-row";
    row.textContent = `${player.name}: ${player.river.map(tileLabel).join(" ") || "—"}`;
    return row;
  }));
  actions.replaceChildren();
  const aiButton = document.createElement("button");
  aiButton.type = "button";
  aiButton.className = "secondary";
  aiButton.textContent = t("browserLocalAI");
  aiButton.disabled = snapshot.phase !== "player-discard";
  aiButton.addEventListener("click", requestBrowserAI);
  actions.append(aiButton);
  if (snapshot.pending?.options) {
    for (const option of snapshot.pending.options) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = option === "pass" ? "secondary" : "primary";
      const actionKind = option.split(":", 1)[0];
      button.textContent = option === "next" ? t("browserNextHand") : actionKind === "riichi" ? t("browserRiichi") : actionKind === "tsumo" ? t("browserTsumo") : actionKind === "ron" ? t("browserRon") : actionKind === "pon" ? t("browserPon") : actionKind === "chi" ? `${t("browserChi")} ${option.slice(4)}` : actionKind === "kan" ? t("browserKan") : t("browserPass");
      button.addEventListener("click", () => {
        browserMatch.respond(option);
        playBrowserSound(option === "tsumo" || option === "ron" ? "win" : option === "pon" || option.startsWith("chi") || option === "kan" ? "call" : "action");
        localStorage.setItem(BROWSER_SAVE_KEY, browserMatch.save());
        renderBrowserMatch();
      });
      actions.append(button);
    }
  }
  settlement.replaceChildren();
  if (snapshot.settlement) {
    const details = snapshot.settlement;
    settlement.textContent = details.win_type === "draw" ? `${t("browserSettlement")} · ${t("browserFinal")}` : `${t("browserSettlement")} · ${details.win_type} · ${details.han} han / ${details.fu} fu · ${details.points} points · ${details.yaku.join(", ")}`;
  }
  renderReplay();
}

function renderReplay() {
  const list = $("#browser-replay-list");
  if (!list || !browserMatch) return;
  if (replayIndex < 0 || replayIndex >= browserMatch.events.length) replayIndex = browserMatch.events.length - 1;
  list.replaceChildren(...browserMatch.events.slice(0, replayIndex + 1).slice(-18).map((event) => {
    const row = document.createElement("li");
    row.textContent = `#${event.sequence} ${event.kind} ${JSON.stringify(event.payload)}`;
    return row;
  }));
  const stateBox = $("#browser-replay-state");
  if (stateBox) {
    const latest = [...browserMatch.events].slice(0, replayIndex + 1).reverse().find((event) => event.kind === "state.snapshot");
    const snapshot = latest?.payload;
    stateBox.textContent = snapshot
      ? `${t("browserReplayState")} · ${snapshot.round_wind || "E"}${Number(snapshot.round_hand ?? 0) + 1} · ${t("wall")} ${snapshot.live_wall_count} · ${t("browserHand")}: ${(snapshot.players?.[0]?.hand || []).map(tileLabel).join(" ")}`
      : t("browserReplayState");
  }
  const table = $("#browser-replay-table");
  if (table) {
    const latest = [...browserMatch.events].slice(0, replayIndex + 1).reverse().find((event) => event.kind === "state.snapshot");
    const snapshot = latest?.payload;
    table.replaceChildren();
    for (const player of snapshot?.players || []) {
      const row = document.createElement("div");
      row.className = "replay-player-row";
      const label = document.createElement("strong");
      label.textContent = `${player.name} · ${player.seat_wind || "E"} · ${player.points}`;
      const hand = document.createElement("span");
      hand.className = "replay-row-tiles";
      const tiles = player.seat === 0 && player.hand ? player.hand : Array.from({ length: player.concealed_count || 0 }, () => "back");
      hand.replaceChildren(...tiles.map((tile) => {
        const item = document.createElement("span");
        item.className = tile === "back" ? "back mini" : "tile mini";
        item.textContent = tile === "back" ? "" : tileLabel(tile);
        return item;
      }));
      const river = document.createElement("small");
      river.textContent = `${t("browserRiver")}: ${(player.river || []).map(tileLabel).join(" ") || "—"}`;
      row.append(label, hand, river);
      table.append(row);
    }
  }
  $("#browser-replay-position").textContent = `${Math.max(0, replayIndex + 1)} / ${browserMatch.events.length}`;
}

function moveReplay(delta) {
  if (!browserMatch) return;
  replayIndex = Math.max(0, Math.min(browserMatch.events.length - 1, (replayIndex < 0 ? browserMatch.events.length - 1 : replayIndex) + delta));
  renderReplay();
}

function startBrowserMatch() {
  const settings = settingsSnapshot();
  browserMatch = new BrowserMatch({ seed: settings.seed, ai: settings.ai, temperature: settings.temperature, match: settings.match });
  replayIndex = browserMatch.events.length - 1;
  localStorage.setItem(BROWSER_SAVE_KEY, browserMatch.save());
  playBrowserSound("action");
  renderBrowserMatch();
}

function downloadBrowserSave() {
  if (!browserMatch) return;
  const blob = new Blob([browserMatch.save()], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `mahjong-browser-${browserMatch.seed}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  $("#browser-match-status").textContent = t("browserSaved");
}

function loadBrowserSave(event) {
  const [file] = event.target.files || [];
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      browserMatch = BrowserMatch.fromJSON(String(reader.result));
      replayIndex = browserMatch.events.length - 1;
      localStorage.setItem(BROWSER_SAVE_KEY, browserMatch.save());
      renderBrowserMatch();
      $("#browser-match-status").textContent = t("browserLoaded");
    } catch (error) {
      $("#browser-match-status").textContent = error instanceof Error ? error.message : String(error);
    }
  });
  reader.readAsText(file);
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
  applyBackground(settings.background);
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
  renderBrowserMatch();
}

$("#analyze-button").addEventListener("click", analyze);
$("#clear-button").addEventListener("click", () => {
  $("#hand-input").value = "";
  $("#hand-tiles").replaceChildren();
  $("#analysis-result").hidden = true;
  $("#effective-result").hidden = true;
  $("#analysis-error").textContent = "";
  $("#analysis-status").textContent = t("waiting");
});
$("#preview-button").addEventListener("click", renderTable);
$("#share-settings-button").addEventListener("click", shareSettings);
$("#background-file").addEventListener("change", handleBackgroundFile);
$("#browser-start-button").addEventListener("click", startBrowserMatch);
$("#browser-save-button").addEventListener("click", downloadBrowserSave);
$("#browser-load-input").addEventListener("change", loadBrowserSave);
$("#browser-replay-prev").addEventListener("click", () => moveReplay(-1));
$("#browser-replay-next").addEventListener("click", () => moveReplay(1));
$("#browser-replay-reset").addEventListener("click", () => {
  if (!browserMatch) return;
  replayIndex = browserMatch.events.length - 1;
  renderReplay();
});
try {
  const savedBrowserMatch = localStorage.getItem(BROWSER_SAVE_KEY);
  if (savedBrowserMatch) {
    browserMatch = BrowserMatch.fromJSON(savedBrowserMatch);
    replayIndex = browserMatch.events.length - 1;
  }
} catch {
  localStorage.removeItem(BROWSER_SAVE_KEY);
}
$$(".settings-panel input, .settings-panel select").forEach((element) => {
  const persistSetting = () => {
    saveSettings();
    if (element.id === "language-setting") applyLanguage();
    if (element.id === "background-setting") applyBackground(element.value);
  };
  element.addEventListener("change", persistSetting);
  element.addEventListener("input", persistSetting);
});

loadSettings();
applyLanguage();
renderTable();
analyze();

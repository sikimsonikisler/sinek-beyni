const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");
const html = fs.readFileSync(require("path").join(__dirname, "..", "index.html"), "utf8");
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => { if (!/Could not load link|stylesheet/i.test(e.message)) errors.push("jsdomError: " + e.message); });
vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));
const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true, url: "https://sinek.test/", virtualConsole: vc,
  beforeParse(win) {
    const noop = () => {};
    const makeCtx = () => new Proxy({}, {
      get(t, p) { if (p in t) return t[p]; if (p === "createRadialGradient" || p === "createLinearGradient") return () => ({ addColorStop: noop }); if (p === "measureText") return () => ({ width: 10 }); return noop; },
      set(t, p, v) { t[p] = v; return true; },
    });
    win.HTMLCanvasElement.prototype.getContext = function () { return this.__ctx || (this.__ctx = makeCtx()); };
    win.Element.prototype.getBoundingClientRect = function () {
      const h = this.id === "raster" ? 300 : this.id === "trace" ? 70 : 600, w = this.id === "dish" ? 600 : 400;
      return { width: w, height: h, left: 0, top: 0, right: w, bottom: h };
    };
    win.addEventListener("error", (e) => errors.push("window error: " + ((e.error && e.error.stack) || e.message)));
  },
});
const w = dom.window, $ = (id) => w.document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  await sleep(600);
  const G = w.__sinek;
  if (!G) throw new Error("oyun başlamadı");
  console.log("beyin N", G.brain.N, "| 0,6 s sonra adım", G.brain.t, "| başlangıç yiyecek", G.S.foods.length);
  $("startBtn").click(); await sleep(150);
  console.log("oyun:", G.S.playing, "| overlay gizli:", $("overlay").hidden, "| yiyecek", G.S.foods.length);
  const sugar = G.S.foods.find((f) => f.type === "seker");
  G.S.target = { x: sugar.x, y: sugar.y }; await sleep(1800);
  console.log(`varış: temas ${G.S.contact && G.S.contact.type} | MN9 ${G.brain.mn9Rate.toFixed(0)} Hz | durum "${$("mn9State").textContent}"`);
  await sleep(4500);
  console.log(`süre ${G.S.time.toFixed(1)} s | temas ${G.S.contact && G.S.contact.type} | MN9 ${G.brain.mn9Rate.toFixed(0)} Hz | hortum ${G.S.fly.ext.toFixed(2)} | enerji ${G.S.energy.toFixed(1)} | yenen ${G.S.eaten} | durum "${$("mn9State").textContent}" | beyin hızı ${G.S.speed.toFixed(2)}`);
  const x0 = G.S.fly.x;
  w.dispatchEvent(new w.KeyboardEvent("keydown", { key: "ArrowLeft" })); await sleep(400);
  w.dispatchEvent(new w.KeyboardEvent("keyup", { key: "ArrowLeft" }));
  console.log("klavye: x", x0.toFixed(3), "->", G.S.fly.x.toFixed(3));
  const lr = $("lesRoundup"); lr.checked = true; lr.dispatchEvent(new w.Event("change"));
  console.log("Roundup lezyonu:", G.brain.lesions.roundup, "| susturulan nöron", G.brain.silenced.reduce((a, b) => a + b, 0), "| bal var mı:", G.S.foods.some((f) => f.type === "bal"));
  lr.checked = false; lr.dispatchEvent(new w.Event("change"));
  $("modeLab").click(); await sleep(1500);
  console.log(`lab tatlı 160: MN9 ${G.brain.mn9Rate.toFixed(0)} Hz, "${$("mn9State").textContent}" | lab paneli görünür: ${!$("labPanel").hidden} | görevler gizli: ${$("missionPanel").hidden}`);
  const sb = $("sBitter"); sb.value = "100"; sb.dispatchEvent(new w.Event("input")); await sleep(1500);
  console.log(`lab tatlı 160 + acı 100: MN9 ${G.brain.mn9Rate.toFixed(0)} Hz, "${$("mn9State").textContent}", etiket ${$("oBitter").textContent}`);
  const lb = $("lesBrake"); lb.checked = true; lb.dispatchEvent(new w.Event("change")); await sleep(1500);
  console.log(`lab acı freni susturuldu: MN9 ${G.brain.mn9Rate.toFixed(0)} Hz`);
  $("modeGame").click(); $("startBtn").click(); await sleep(100); G.S.energy = 0.3; await sleep(500);
  console.log("açlık testi: oyun", G.S.playing, "| overlay gizli", $("overlay").hidden, "| başlık", $("ovTitle").textContent, "|", $("ovText").textContent);
  console.log("görev satırı", w.document.querySelectorAll("#missions li").length, "| tamamlanan", w.document.querySelectorAll("#missions li.done").length, "| referans satırı", w.document.querySelectorAll("#refTable tr").length);
  console.log("HATALAR:", errors.length ? "\n" + errors.slice(0, 6).join("\n") : "yok");
  w.close(); process.exit(0);
})().catch((e) => { console.log("TEST BAŞARISIZ", e.stack, "\n" + errors.slice(0, 6).join("\n")); process.exit(1); });

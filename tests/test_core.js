const { FlyBrain } = require("../game/brain_core.js");
const D = require("../game/brain_data.json");
const br = new FlyBrain(D);
const TRIALS = 6;
let steps = 0, t0 = Date.now(), worst = 0;
console.log("koşul".padEnd(46), "Python MN9", "  JS MN9");
for (const c of D.reference) {
  const r = [];
  for (let k = 0; k < TRIALS; k++) {
    br.reset(); br.lesions = {};
    br.setLesion("roundup", c.lesion === "roundup" || c.lesion === "both");
    br.setLesion("brake", c.lesion === "brake" || c.lesion === "both");
    br.setTaste("sugar", c.sugar); br.setTaste("bitter", c.bitter); br.setTaste("water", c.water);
    br.runMs(1000); r.push(br.mn9Count); steps += 10000;
  }
  const m = r.reduce((a, b) => a + b) / TRIALS;
  const sd = Math.sqrt(r.reduce((a, b) => a + (b - m) ** 2, 0) / TRIALS);
  const z = Math.abs(m - c.mn9_mean) / Math.sqrt((sd / Math.sqrt(TRIALS)) ** 2 + c.mn9_sem ** 2 + 1e-9);
  worst = Math.max(worst, Math.abs(m - c.mn9_mean));
  console.log(c.name.padEnd(46), (c.mn9_mean.toFixed(1) + " Hz").padStart(9), (m.toFixed(1) + " ± " + (sd / Math.sqrt(TRIALS)).toFixed(1) + " Hz").padStart(16), z > 3 ? "  <-- FARK" : "");
}
const sec = (Date.now() - t0) / 1000;
console.log(`en büyük fark: ${worst.toFixed(1)} Hz | hız: ${(steps / 10000 / sec).toFixed(1)}x gerçek zaman (Node, tek çekirdek)`);

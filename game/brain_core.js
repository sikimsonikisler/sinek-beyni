/* FlyBrain: Shiu et al. (2024) LIF modelinin tarayıcı sürümü.
   Brian2 semantiği: spike sonrası 2,2 ms integrasyon/eşik yok ve bu sürede gelen sinaptik girdiler yok sayılır. */
(function (root) {
  function b64ToU8(b64) {
    if (typeof atob === "function") {
      const s = atob(b64), u = new Uint8Array(s.length);
      for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
      return u;
    }
    return Uint8Array.from(Buffer.from(b64, "base64"));
  }
  class FlyBrain {
    constructor(D) {
      const N = (this.N = D.N);
      const ip = b64ToU8(D.indptr), ix = b64ToU8(D.indices), wc = b64ToU8(D.counts);
      this.indptr = new Uint32Array(ip.buffer, 0, ip.byteLength >> 2);
      this.indices = new Uint16Array(ix.buffer, 0, ix.byteLength >> 1);
      const counts = new Int16Array(wc.buffer, 0, wc.byteLength >> 1);
      this.w = new Float32Array(counts.length);
      for (let e = 0; e < counts.length; e++) this.w[e] = counts[e] * 0.275; // sinaps sayısı x işaret x 0,275 mV
      this.groups = D.groups;
      this.v = new Float32Array(N); this.g = new Float32Array(N); this.last = new Int32Array(N);
      this.noRef = new Uint8Array(N); this.silenced = new Uint8Array(N); this.rate = new Float32Array(N);
      this.spiked = new Uint8Array(N); this.spk = new Int32Array(N);
      this.RING = 19; this.D = 18; this.REF = 22;
      this.buf = new Float32Array(this.RING * N);
      const dt = (this.dt = 0.1);
      this.a = Math.exp(-dt / 20); this.c = Math.exp(-dt / 5);
      this.b = (5 / (5 - 20)) * (Math.exp(-dt / 5) - Math.exp(-dt / 20));
      const grn = [...D.groups.sugar, ...D.groups.bitter, ...(D.groups.water || [])];
      this.stimIdx = Int32Array.from(grn);
      for (const i of grn) this.noRef[i] = 1;
      this.mn9 = D.groups.mn9[0];
      this.mn9Decay = Math.exp(-dt / 200); // 200 ms pencereli hız tahmini
      this.watch = new Int16Array(N).fill(-1);
      this.onSpike = null;
      this.lesions = {};
      this.reset();
    }
    reset() {
      this.v.fill(-52); this.g.fill(0); this.last.fill(-1000000); this.buf.fill(0); this.spiked.fill(0);
      this.t = 0; this.mn9Rate = 0; this.mn9Count = 0;
    }
    setTaste(name, hz) { for (const i of this.groups[name] || []) this.rate[i] = hz; }
    setLesion(name, on) {
      this.lesions[name] = !!on;
      this.silenced.fill(0);
      for (const k in this.lesions) if (this.lesions[k]) for (const i of this.groups[k]) this.silenced[i] = 1;
    }
    step() {
      const N = this.N, v = this.v, g = this.g, last = this.last, noRef = this.noRef;
      const spiked = this.spiked, spk = this.spk, buf = this.buf;
      const t = this.t, REF = this.REF, a = this.a, b = this.b, c = this.c;
      for (let i = 0; i < N; i++) {
        if (noRef[i] === 1 || t - last[i] >= REF) { v[i] = -52 + (v[i] + 52) * a + g[i] * b; g[i] *= c; }
      }
      let ns = 0;
      for (let i = 0; i < N; i++) {
        if (v[i] > -45 && (noRef[i] === 1 || t - last[i] >= REF)) { spk[ns++] = i; spiked[i] = 1; }
      }
      const base = (t % this.RING) * N;
      for (let i = 0; i < N; i++) {
        const x = buf[base + i];
        if (x !== 0) {
          buf[base + i] = 0;
          if (spiked[i] === 0 && (noRef[i] === 1 || t - last[i] >= REF)) g[i] += x;
        }
      }
      const sidx = this.stimIdx, rate = this.rate, p = this.dt / 1000;
      for (let k = 0; k < sidx.length; k++) {
        const i = sidx[k], r = rate[i];
        if (r > 0 && spiked[i] === 0 && Math.random() < r * p) v[i] += 68.75;
      }
      this.mn9Rate *= this.mn9Decay;
      const tb = ((t + this.D) % this.RING) * N, ip = this.indptr, ix = this.indices, w = this.w;
      const sil = this.silenced, watch = this.watch, mn9 = this.mn9;
      for (let k = 0; k < ns; k++) {
        const s = spk[k];
        v[s] = -52; g[s] = 0; last[s] = t; spiked[s] = 0;
        if (sil[s] === 0) for (let e = ip[s], end = ip[s + 1]; e < end; e++) buf[tb + ix[e]] += w[e];
        if (s === mn9) { this.mn9Rate += 5; this.mn9Count++; }
        if (watch[s] >= 0 && this.onSpike) this.onSpike(watch[s], t);
      }
      this.t = t + 1;
    }
    runMs(ms) { const n = Math.round(ms / this.dt); for (let k = 0; k < n; k++) this.step(); }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { FlyBrain };
  else root.FlyBrain = FlyBrain;
})(this);

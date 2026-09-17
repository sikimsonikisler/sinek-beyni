"""FlyWire bağlantı verisinden oyunun beyin devresini çıkarır ve game/brain_data.json dosyasına yazar.

Depo kökünden:
    cd kopru && pip install -r requirements.txt && ./setup_data.sh && cd ..
    python3 game/export_brain.py
Tohumlar sabit olduğu için depodaki brain_data.json dosyasının aynısını üretir.
"""
import base64, json, re, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kopru"))
from kopru import neurons as nr            # noqa: E402
from kopru.experiment import Lab          # noqa: E402
from kopru.lif import Stim, simulate       # noqa: E402

DATA = ROOT / "kopru" / "data" / "shiu_repo"
OUT = ROOT / "game" / "brain_data.json"
# Köprü deneyinde (tohum 0) kurallarla seçilen okuma nöronları; oyunda sadece panelde gösteriliyor
EARLY_IDS = [720575940622695448, 720575940629888530, 720575940627383685, 720575940626191306, 720575940638103349]
LATE_IDS = [720575940621586854, 720575940633185567, 720575940619877396, 720575940631918649, 720575940615671106]


def main():
    t0 = time.time()
    nb = json.load(open(DATA / "figures.ipynb"))
    src = "\n".join("".join(c["source"]) for c in nb["cells"])
    water_ids = [int(x) for x in re.findall(r"\d{15,}", re.search(r"neu_water\s*=\s*\[(.*?)\]", src, re.S).group(1))]
    lab = Lab(str(DATA), "630", seed=0, log=lambda m: None)
    C = lab.C
    sug, bit, mn9L, mn9R, pm, roundup = lab.sugar, lab.bitter, lab.mn9, C.id2idx[nr.MN9_RIGHT], lab.premotor, lab.lesion
    water = C.idx(water_ids)[0]
    early, late = C.idx(EARLY_IDS)[0], C.idx(LATE_IDS)[0]

    # 1) Acı freni: acıyla ateşleyen ve tatlı->MN9 yoluna toplamda -30 mV'tan güçlü baskılayıcı çıkış veren nöronlar
    conds = [(0, 200), (160, 0), (160, 100)]
    reps = 2
    s = np.repeat([c[0] for c in conds], reps)
    b = np.repeat([c[1] for c in conds], reps)
    R = simulate(C.W, len(s), 600.0, stims=[Stim(sug, s), Stim(bit, b)], seed=5)["rates"].reshape(3, reps, -1).mean(1)
    bitter_only, sugar_only, _ = R
    path = np.union1d(np.setdiff1d(np.flatnonzero(sugar_only > 20), sug), [mn9L])
    cand = np.setdiff1d(np.flatnonzero(bitter_only > 10), np.concatenate([sug, bit]))
    inh = np.asarray(C.W[path][:, cand].minimum(0).sum(0)).ravel()
    brake = cand[inh < -30]
    print(f"acı freni: {len(brake)} nöron")

    # 2) Keşif: oyundaki tüm tat ve lezyon kombinasyonlarında spike atan ya da eşiğe yaklaşan nöronlar
    lesions = {"none": [], "roundup": [roundup], "brake": [brake], "both": [roundup, brake]}
    stims = [(200, 0, 0), (0, 200, 0), (200, 200, 0), (160, 100, 0), (0, 0, 200), (200, 0, 200), (0, 200, 200)]
    conds = [(s_, b_, w_, L) for L in lesions for (s_, b_, w_) in stims]
    B = len(conds)
    sil = np.zeros((B, C.N), bool)
    for j, c in enumerate(conds):
        for arr in lesions[c[3]]:
            sil[j, arr] = True
    out = simulate(C.W, B, 400.0, stims=[Stim(sug, [c[0] for c in conds]), Stim(bit, [c[1] for c in conds]),
                                          Stim(water, [c[2] for c in conds])], silence=sil, seed=21, record_vmax=True)
    hot = np.flatnonzero((out["rates"].max(0) > 0) | (out["vmax"].max(0) > -50))
    groups_full = dict(sugar=sug, bitter=bit, water=water, early=early, late=late, brake=brake, roundup=roundup,
                       premotor=[pm], mn9=[mn9L, mn9R])
    keep = np.unique(np.concatenate([hot] + [np.asarray(v) for v in groups_full.values()]))
    Ws, keep = C.subgraph(keep)
    pos = np.full(C.N, -1)
    pos[keep] = np.arange(len(keep))
    print(f"alt devre: {len(keep)} nöron, {Ws.nnz} bağlantı")

    def run(W, mp, cs, reps, t_ms, seed):
        Bn, N = len(cs) * reps, W.shape[0]
        cc = [c for c in cs for _ in range(reps)]
        sl = np.zeros((Bn, N), bool)
        for j, c in enumerate(cc):
            for arr in lesions[c[3]]:
                sl[j, mp(arr)] = True
        o = simulate(W, Bn, t_ms, stims=[Stim(mp(sug), [c[0] for c in cc]), Stim(mp(bit), [c[1] for c in cc]),
                                         Stim(mp(water), [c[2] for c in cc])], silence=sl, seed=seed)
        return o["rates"][:, mp([mn9L])[0]].reshape(len(cs), reps)

    # 3) Doğrulama: aynı tohumla tam beyin ve alt devre aynı MN9 sonucunu vermeli
    chk = [(160, 100, 0, "none"), (160, 100, 0, "brake"), (0, 0, 160, "none"), (160, 0, 0, "roundup")]
    full = run(C.W, lambda a: np.asarray(a), chk, 1, 400.0, 77).ravel()
    subr = run(Ws, lambda a: pos[np.asarray(a)], chk, 1, 400.0, 77).ravel()
    print("tam beyin / alt devre MN9:", full.tolist(), subr.tolist())
    assert np.abs(full - subr).max() == 0, "alt devre tam beyinle uyuşmuyor"

    # 4) Referans değerler (tarayıcı motorunu test etmek için)
    refs = [("Şeker (tatlı 160)", 160, 0, 0, "none"), ("Bal (tatlı 200)", 200, 0, 0, "none"),
            ("Acılı tatlı (160+60)", 160, 60, 0, "none"), ("Tatlı 160 + acı 100", 160, 100, 0, "none"),
            ("Acı ot (acı 200)", 0, 200, 0, "none"), ("Su (160)", 0, 0, 160, "none"),
            ("Tatlı 160, Roundup susturuldu", 160, 0, 0, "roundup"),
            ("Tatlı 160 + acı 100, acı freni susturuldu", 160, 100, 0, "brake"),
            ("Acı 200, acı freni susturuldu", 0, 200, 0, "brake")]
    rr = run(Ws, lambda a: pos[np.asarray(a)], [r[1:] for r in refs], 6, 1000.0, 5)
    ref_out = [dict(name=r[0], sugar=r[1], bitter=r[2], water=r[3], lesion=r[4], mn9_mean=float(row.mean()),
                    mn9_sem=float(row.std() / np.sqrt(len(row)))) for r, row in zip(refs, rr)]

    counts = np.rint(Ws.data / 0.275).astype(np.int64)
    assert np.abs(counts).max() < 32767 and np.allclose(counts * 0.275, Ws.data, atol=1e-3)
    enc = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
    D = dict(N=int(len(keep)), nnz=int(Ws.nnz),
             indptr=enc(Ws.indptr.astype("<u4")), indices=enc(Ws.indices.astype("<u2")), counts=enc(counts.astype("<i2")),
             groups={k: [int(pos[i]) for i in np.atleast_1d(v)] for k, v in groups_full.items()},
             ids={k: [str(C.ids[i]) for i in np.atleast_1d(v)] for k, v in groups_full.items()},
             names={k: [lab.name_of.get(int(i), "") for i in np.atleast_1d(v)] for k, v in groups_full.items()},
             reference=ref_out, source="FlyWire v630 · Shiu et al. 2024 LIF modeli")
    json.dump(D, open(OUT, "w"))
    print(f"yazıldı: {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()

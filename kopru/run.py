"""Köprü: sanal sinek beyninde nöroprotez deneyi.

Kullanım:
    python run.py validate                  # simülatörü Shiu et al.'ın kayıtlı Brian2 çıktılarıyla karşılaştır
    python run.py all                       # tam deney, 3 tohum
    python run.py all --quick --seeds 0     # hızlı deneme
    python run.py summary --seeds 0 1 2     # ayrı koşturulmuş tohumları birleştir
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

DATA = "data/shiu_repo"
OUT = Path("results")
REF_LABELS = {"noise_floor": "Sağlam beyin, bağımsız tekrar (gürültü tabanı)",
              "lesioned": "Lezyonlu, implantsız"}


def log(msg):
    print(msg, flush=True)


def cmd_validate(args):
    import pandas as pd
    from kopru import neurons as nr
    from kopru.connectome import Connectome
    from kopru.lif import Stim, simulate

    C = Connectome(DATA, "630")
    sug = C.idx(nr.SUGAR_GRN, strict=True)[0]
    rows = []
    for fname, hz in [("sugarR.parquet", 200), ("sugarR_100Hz.parquet", 100)]:
        df = pd.read_parquet(Path(DATA) / "results" / "example" / fname)  # Brian2, 30 deneme x 1 s
        ref = df.groupby("flywire_id").size() / (df.trial.nunique() * 1.0)
        t = time.time()
        B = 4 if args.quick else 10
        out = simulate(C.W, B, 1000.0, stims=[Stim(sug, [hz] * B)], seed=7)
        mine = pd.Series(out["rates"].mean(0), index=C.ids)
        common = ref.index.union(mine[mine > 0].index)
        common = common[~np.isin(common, nr.SUGAR_GRN)]
        a = ref.reindex(common).fillna(0).to_numpy()
        b = mine.reindex(common).fillna(0).to_numpy()
        row = dict(stim_hz=hz, n_trials=B, pearson_r=float(np.corrcoef(a, b)[0, 1]),
                   mn9_brian2=float(ref.get(nr.MN9_LEFT, 0)), mn9_kopru=float(mine[nr.MN9_LEFT]),
                   active_brian2=int((ref.drop(nr.SUGAR_GRN, errors="ignore") > 0).sum()),
                   active_kopru=int((mine.drop(nr.SUGAR_GRN, errors="ignore") > 0).sum()),
                   seconds=time.time() - t)
        rows.append(row)
        log(f"  tatlı {hz} Hz: r = {row['pearson_r']:.3f} | MN9 Brian2 {row['mn9_brian2']:.1f} Hz, "
            f"Köprü {row['mn9_kopru']:.1f} Hz | aktif nöron {row['active_brian2']} / {row['active_kopru']} "
            f"| {row['seconds']:.0f} s")
    OUT.mkdir(exist_ok=True)
    (OUT / "validation.json").write_text(json.dumps(rows, indent=2))


def run_seed(lab, seed, quick, full_check):
    from kopru.experiment import bitter_bias, bitter_preservation
    lab.seed = seed
    t0 = time.time()
    log(f"\n=== Tohum {seed} ===")
    log("1) Alt ağ keşfi (tam beyin)")
    lab.build_subgraph(write_groups=[np.array([lab.mn9]), np.array([lab.premotor])],
                       t_ms=300.0 if quick else 500.0)
    reps = 4 if quick else 8

    log("2) Sağlam ve lezyonlu beyin")
    intact = lab.evaluate(lesion=False, reps=reps)
    target = np.array(intact["dose_mean"])
    rmse = lambda r: float(np.sqrt(((np.array(r["dose_mean"]) - target) ** 2).mean()))
    noise = lab.evaluate(lesion=False, reps=reps, seed_shift=777)
    lesioned = lab.evaluate(lesion=True, reps=reps)
    for r, lab_ in ((noise, "noise_floor"), (lesioned, "lesioned")):
        r.update(rmse=rmse(r), bitter_preservation=bitter_preservation(intact, r),
                 bitter_bias=bitter_bias(intact, r), label=REF_LABELS[lab_])
    log(f"   sağlam MN9      : {np.round(target, 1).tolist()}")
    log(f"   lezyonlu MN9    : {np.round(lesioned['dose_mean'], 1).tolist()}  (hata {lesioned['rmse']:.1f} Hz)")
    log(f"   gürültü tabanı  : hata {noise['rmse']:.1f} Hz, acı-koruma {noise['bitter_preservation']:.2f}")

    log("3) Okuma/yazma yerlerinin seçimi (kurallarla)")
    rate, hop, drive, bmi = lab.characterize(reps=4 if quick else 6)
    designs, site_info = lab.select_designs(rate, hop, drive, bmi)
    for k in ("early", "late"):
        log(f"   {k}: " + ", ".join(f"{d['id']}({d['name'] or '-'}, {d['hop']} adım, {d['sugar_hz']:.0f} Hz, "
                                      f"acı-baskı {d['bmi']:.2f})" for d in site_info[k]))

    if quick:
        gains, offsets = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0], [-20.0, 0.0, 20.0, 40.0, 80.0, 120.0]
    else:
        gains = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0]
        offsets = [-40.0, -20.0, 0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0]

    res = dict(seed=seed, intact=intact, noise_floor=noise, lesioned=lesioned, designs={},
               site_info=site_info)
    log("4) İmplant eğitimi (sadece tatlı) + acı testi (eğitimde yok)")
    for d in designs:
        t = time.time()
        tr = lab.train(d, gains, offsets, reps=2, t_ms=400.0 if quick else 600.0, target=target,
                       refine=not quick)
        ev = lab.evaluate(d, tr["gain"], tr["offset"], lesion=True, reps=reps)
        ev.update(rmse=rmse(ev), bitter_preservation=bitter_preservation(intact, ev),
                  bitter_bias=bitter_bias(intact, ev), label=d.label,
                  gain=tr["gain"], offset=tr["offset"], train_rmse=tr["rmse"],
                  coarse_at_boundary=tr["coarse_at_boundary"],
                  read_ids=lab.fid(d.read), write_ids=lab.fid(d.write))
        res["designs"][d.key] = ev
        log(f"   {d.label:40s} kazanç={tr['gain']:<6g} eşik={tr['offset']:<6g} "
            f"tatlı-hata={ev['rmse']:5.1f} Hz  acı-koruma={ev['bitter_preservation']:.2f}  yön={ev['bitter_bias']:+.2f}  ({time.time() - t:.0f} s)")

    if full_check:
        log("5) Tam beyin doğrulaması (aynı tohum, alt ağ varsayımı)")
        s = np.array([0, 160, 160, 0], dtype=float)
        bt = np.array([0, 0, 100, 100], dtype=float)
        les = np.ones(4, dtype=bool)
        checks = {}
        for d in designs:
            ev = res["designs"][d.key]
            g, o = np.full(4, ev["gain"]), np.full(4, ev["offset"])
            fb = lab.run(s, bt, les, implant=d, gains=g, offsets=o, t_ms=500.0, seed=999, full_brain=True)
            sb = lab.run(s, bt, les, implant=d, gains=g, offsets=o, t_ms=500.0, seed=999, full_brain=False)
            diff = float(np.abs(fb - sb).max())
            checks[d.key] = dict(max_abs_diff_hz=diff, full=fb.tolist(), sub=sb.tolist())
            log(f"   {d.key:16s} tam beyin {np.round(fb, 1).tolist()} | alt ağ {np.round(sb, 1).tolist()} | fark {diff:.2f} Hz")
        res["full_brain_check"] = checks
    res.update(subgraph_size=int(len(lab.keep)), seconds=time.time() - t0, quick=quick)
    return res


def aggregate(runs):
    def item(r, k):
        return r[k] if k in ("intact", "noise_floor", "lesioned") else r["designs"][k]
    keys = ["noise_floor", "lesioned"] + list(runs[0]["designs"].keys())
    table, curves = {}, {}
    for k in ["intact"] + keys:
        its = [item(r, k) for r in runs]
        dose = np.array([i["dose_mean"] for i in its])
        bit = np.array([i["bitter_mean"] for i in its])
        ratio = bit / np.maximum(bit[:, :1], 1e-9)
        curves[k] = dict(dose_mean=dose.mean(0).tolist(), dose_sd=dose.std(0).tolist(),
                         ratio_mean=ratio.mean(0).tolist(), ratio_sd=ratio.std(0).tolist())
        if k == "intact":
            continue
        rm = np.array([i["rmse"] for i in its])
        bp = np.array([i["bitter_preservation"] for i in its])
        bb = np.array([i["bitter_bias"] for i in its])
        table[k] = dict(label=its[0]["label"], rmse_mean=float(rm.mean()), rmse_sd=float(rm.std()),
                        bp_mean=float(bp.mean()), bp_sd=float(bp.std()),
                        bias_mean=float(bb.mean()), bias_sd=float(bb.std()),
                        rmse_all=rm.tolist(), bp_all=bp.tolist())
    gate = 0.5 * table["lesioned"]["rmse_mean"]
    for k, t in table.items():
        t["task_ok"] = bool(k != "lesioned" and t["rmse_mean"] < gate)
    return dict(table=table, curves=curves, task_gate_hz=gate)


def cmd_all(args):
    from kopru.experiment import BITTER_LEVELS, SUGAR_FOR_BITTER_TEST, SUGAR_LEVELS, Lab
    from kopru.report import make_figure, make_report
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    lab = Lab(DATA, "630", seed=args.seeds[0], log=log)
    log(f"MN9={lab.fid(lab.mn9)[0]} | premotor={lab.fid(lab.premotor)[0]} | lezyon(Roundup)={lab.fid(lab.lesion)}")
    runs = []
    for s in args.seeds:
        r = run_seed(lab, s, args.quick,
                     full_check=(s == args.full_check_seed and not args.skip_full_check))
        runs.append(r)
        (OUT / f"seed_{s}.json").write_text(json.dumps(r, indent=2, ensure_ascii=False))
    write_summary(runs)
    log(f"\nBitti: {time.time() - t0:.0f} s -> results/RAPOR.md, results/kopru_sonuc.png")


def write_summary(runs):
    from kopru.experiment import BITTER_LEVELS, SUGAR_FOR_BITTER_TEST, SUGAR_LEVELS
    from kopru.report import make_figure, make_report
    if len({r["quick"] for r in runs}) > 1:
        raise SystemExit("Hızlı ve tam mod sonuçları karıştırılamaz.")
    summary = aggregate(runs)
    summary.update(sugar_levels=SUGAR_LEVELS, bitter_levels=BITTER_LEVELS,
                   sugar_for_bitter_test=SUGAR_FOR_BITTER_TEST, seeds=[r["seed"] for r in runs],
                   quick=runs[0]["quick"], seconds=float(sum(r["seconds"] for r in runs)))
    OUT.mkdir(exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    make_figure(summary, OUT / "kopru_sonuc.png")
    make_report(summary, runs, OUT / "RAPOR.md")


def cmd_summary(args):
    """Önceden kaydedilmiş tohum sonuçlarını birleştirir (tohumları ayrı ayrı koşturduysan)."""
    runs = [json.loads((OUT / f"seed_{s}.json").read_text()) for s in args.seeds]
    write_summary(runs)
    log(f"Birleştirildi: tohumlar {args.seeds} -> results/RAPOR.md, results/kopru_sonuc.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["validate", "all", "summary"])
    ap.add_argument("--quick", action="store_true", help="az tekrar, küçük ızgara")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--skip-full-check", action="store_true", help="tam beyin doğrulamasını atla")
    ap.add_argument("--full-check-seed", type=int, default=0, help="tam beyin doğrulaması hangi tohumda yapılsın")
    args = ap.parse_args()
    {"validate": cmd_validate, "all": cmd_all, "summary": cmd_summary}[args.command](args)

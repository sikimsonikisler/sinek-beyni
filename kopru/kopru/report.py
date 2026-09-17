"""Sonuç grafiği ve otomatik rapor (tohumlar üzerinden ortalama ± standart sapma)."""
import numpy as np

STYLE = {
    "intact": dict(color="black", lw=2.6, label="Sağlam beyin", zorder=5),
    "lesioned": dict(color="#8a8a8a", lw=2, ls="--", label="Lezyonlu, implantsız"),
    "erken_mn9": dict(color="#D85A30", lw=1.8, label="Erken okuma → MN9"),
    "erken_premotor": dict(color="#EF9F27", lw=1.8, label="Erken okuma → premotor"),
    "gec_mn9": dict(color="#185FA5", lw=1.8, label="Geç okuma → MN9"),
    "gec_premotor": dict(color="#1D9E75", lw=1.8, label="Geç okuma → premotor"),
    "sahte_mn9": dict(color="#993556", lw=1.6, ls=":", label="Sahte okuma → MN9 (kontrol)"),
}


def make_figure(summ, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    S, Bl, cur = summ["sugar_levels"], summ["bitter_levels"], summ["curves"]
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8))
    for key, st in STYLE.items():
        if key not in cur:
            continue
        c = cur[key]
        ax[0].errorbar(S, c["dose_mean"], yerr=c["dose_sd"], marker="o", ms=4, capsize=2, **st)
        ax[1].errorbar(Bl, c["ratio_mean"], yerr=c["ratio_sd"], marker="o", ms=4, capsize=2, **st)
    ax[0].set(xlabel="Tatlı nöron uyarımı (Hz)", ylabel="MN9 hızı (Hz)",
              title="Eğitim görevi: tatlıya tepki")
    ax[1].set(xlabel=f"Acı nöron uyarımı (Hz), tatlı sabit {summ['sugar_for_bitter_test']} Hz",
              ylabel="MN9 / acısızken MN9", title="Test (eğitimde yok): acı baskılaması")
    ax[1].axhline(1, color="#cccccc", lw=0.8, zorder=0)
    ax[0].legend(fontsize=8, loc="upper left", framealpha=0.9)
    n = len(summ["seeds"])
    fig.suptitle(f"Köprü: sanal sinek beyninde nöroprotez  ·  {n} tohum, hata çubukları = std", fontsize=11)
    for a in ax:
        a.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def make_report(summ, runs, path):
    T = summ["table"]
    L = ["# Köprü deney raporu (otomatik üretildi)\n",
         f"Tohumlar: {summ['seeds']} · hızlı mod: {summ['quick']} · toplam süre: {summ['seconds'] / 60:.1f} dk\n",
         "## Ana tablo\n",
         f"Görev başarısı ölçütü: tatlı eğrisi hatası, implantsız lezyonlu beynin hatasının yarısından "
         f"küçük olmalı (< {summ['task_gate_hz']:.1f} Hz). Acı-koruma skoru yalnızca görevi geçen "
         f"koşullar için yorumlanır; görevi geçemeyen bir implant, beynin kendi kalan acı devresi yüzünden "
         f"yüksek skor alabilir.\n",
         "| Koşul | Tatlı eğrisi hatası (Hz) | Görev | Acı-koruma (0-1) | Yön (+ az, − fazla baskılama) | Tohum başına acı-koruma |",
         "|---|---|---|---|---|---|"]
    for k, t in T.items():
        ok = "referans" if k == "noise_floor" else ("geçti" if t["task_ok"] else "geçemedi")
        bp = f"{t['bp_mean']:.2f} ± {t['bp_sd']:.2f}"
        if k not in ("noise_floor",) and not t["task_ok"]:
            bp += " (yorumlanamaz)"
        L.append(f"| {t['label']} | {t['rmse_mean']:.1f} ± {t['rmse_sd']:.1f} | {ok} | {bp} | "
                 f"{t['bias_mean']:+.2f} ± {t['bias_sd']:.2f} | {', '.join(f'{x:.2f}' for x in t['bp_all'])} |")
    L.append("\nAcı-koruma: sağlam beyindeki acı baskılamasının ne kadarının korunduğu. "
             "1 = sağlam beyinle aynı, 0 = tamamen kayıp. Hem eksik hem aşırı baskılama puanı düşürür. "
             "Yön: acılı koşullarda (MN9 oranı implant − MN9 oranı sağlam) ortalaması; + ise implant acıyı "
             "az duyuyor, − ise fazla duyuyor.\n")

    L.append("## Acı altında MN9 oranı (tohum ortalaması)\n")
    Bl = summ["bitter_levels"]
    L.append("| Koşul | " + " | ".join(f"acı {b} Hz" for b in Bl) + " |")
    L.append("|---" * (len(Bl) + 1) + "|")
    for k in ["intact"] + list(T.keys()):
        name = "Sağlam beyin" if k == "intact" else T[k]["label"]
        L.append(f"| {name} | " + " | ".join(f"{x:.2f}" for x in summ["curves"][k]["ratio_mean"]) + " |")

    L.append("\n## Tohum başına ayrıntı\n")
    for r in runs:
        si = r["site_info"]
        L.append(f"### Tohum {r['seed']} · alt ağ {r['subgraph_size']} nöron · {r['seconds']:.0f} s\n")
        L.append(f"Lezyon: {si['lesion']} · premotor: {si['premotor'][0]} (MN9'a {si['premotor_weight_mV']:.0f} mV) · MN9: {si['mn9'][0]}\n")
        for kk, title in (("early", "Erken okuma"), ("late", "Geç okuma")):
            L.append(f"{title}: " + ", ".join(f"{d['id']} ({d['name'] or '-'}, {d['hop']} adım, "
                                              f"{d['sugar_hz']:.0f} Hz, acı-baskı {d['bmi']:.2f})" for d in si[kk]) + "\n")
        L.append(f"Sahte okuma: {si['sham']}\n")
        L.append("| Tasarım | Kazanç | Eşik (Hz) | Tatlı hatası | Acı-koruma | Yön | Kaba ızgara sınırında mı |")
        L.append("|---|---|---|---|---|---|---|")
        for k, d in r["designs"].items():
            L.append(f"| {d['label']} | {d['gain']:g} | {d['offset']:g} | {d['rmse']:.1f} | "
                     f"{d['bitter_preservation']:.2f} | {d['bitter_bias']:+.2f} | {'evet' if d['coarse_at_boundary'] else 'hayır'} |")
        if "full_brain_check" in r:
            L.append("\nTam beyin doğrulaması (aynı tohum, 4 koşul):\n")
            for k, c in r["full_brain_check"].items():
                L.append(f"- {k}: en büyük MN9 farkı {c['max_abs_diff_hz']:.2f} Hz")
        L.append("")
    path.write_text("\n".join(L), encoding="utf-8")

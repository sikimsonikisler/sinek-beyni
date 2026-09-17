"""Köprü deneyleri: lezyon, implant tasarımları, eğitim ve eğitimde görülmemiş test.

Akış:
  1) Alt ağ keşfi (tam beyin)      -> hızlı simülasyon için aktif nöronlar
  2) Hedef eğri (sağlam beyin)     -> tatlıya karşı MN9 tepkisi
  3) Lezyon                        -> Roundup nöronlarının çıkışı kapatılır
  4) Okuma/yazma yerlerinin seçimi -> kurallarla, elle seçim yok
  5) İmplant eğitimi               -> SADECE tatlı eğrisiyle ızgara araması
  6) Test                          -> acı tadın baskılaması (eğitimde hiç yok)
  7) Tam beyin doğrulaması         -> alt ağ varsayımı kontrolü
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

from . import neurons as nr
from .connectome import Connectome
from .lif import Implant, Stim, simulate

SUGAR_LEVELS = [0, 40, 80, 120, 160, 200]      # Hz, eğitim koşulları
BITTER_LEVELS = [0, 25, 50, 100, 200]          # Hz, test koşulları
SUGAR_FOR_BITTER_TEST = 160                    # Hz
LESION_TYPES = ["roundup"]                     # Shiu et al. isimlendirmesi
N_READ = 5                                     # okuma grubu büyüklüğü


@dataclass
class Design:
    key: str
    label: str
    read: np.ndarray    # tam beyin indeksleri
    write: np.ndarray


class Lab:
    def __init__(self, data_dir="data/shiu_repo", version="630", seed=0, log=print):
        self.log = log
        self.seed = seed
        self.C = C = Connectome(data_dir, version)
        self.sugar = C.idx(nr.SUGAR_GRN, strict=True)[0]
        self.bitter = C.idx(nr.BITTER_GRN, strict=True)[0]
        self.mn9 = C.id2idx[nr.MN9_LEFT]
        sez = nr.sez_named_neurons(data_dir)
        self.types = {n: C.idx(ids)[0] for n, ids in sez.items()}
        self.name_of = {int(i): n for n, v in self.types.items() for i in v}
        self.lesion = np.concatenate([self.types[t] for t in LESION_TYPES])
        self.premotor = self._strongest_excitatory_input(self.mn9, exclude=self.lesion)
        self.keep = None

    # ------------------------------------------------------------------ yardımcılar
    def _strongest_excitatory_input(self, target, exclude):
        row = self.C.W[target, :].tocsc()
        cols = np.flatnonzero(np.diff(row.indptr) > 0)
        w = np.asarray(row[:, cols].todense()).ravel()
        order = cols[np.argsort(-w)]
        return int(next(c for c in order if c not in set(exclude.tolist())))

    def fid(self, idx):
        return [int(self.C.ids[i]) for i in np.atleast_1d(idx)]

    # ------------------------------------------------------------------ 1) alt ağ
    def build_subgraph(self, write_groups, t_ms=500.0, margin_mv=-50.0):
        """Tam beyinde, deneyde olabilecek tüm uç koşulları simüle eder; spike atan
        veya eşiğe margin_mv kadar yaklaşan her nöronu alt ağa alır."""
        C = self.C
        conds = []  # (sugar_hz, bitter_hz, lesion, write_group_index or -1)
        for les in (False, True):
            for s, b in [(200, 0), (0, 200), (200, 200)]:
                conds.append((s, b, les, -1))
            for k in range(len(write_groups)):
                for s, b in [(0, 0), (200, 0), (200, 200)]:
                    conds.append((s, b, les, k))
        B = len(conds)
        stims = [Stim(self.sugar, [c[0] for c in conds]),
                 Stim(self.bitter, [c[1] for c in conds])]
        for k, w in enumerate(write_groups):
            stims.append(Stim(w, [200.0 if c[3] == k else 0.0 for c in conds]))
        sil = np.zeros((B, C.N), dtype=bool)
        for j, c in enumerate(conds):
            if c[2]:
                sil[j, self.lesion] = True
        self.log(f"  keşif: tam beyin, {B} koşul x {t_ms:.0f} ms")
        out = simulate(C.W, B, t_ms, stims=stims, silence=sil, seed=self.seed + 101,
                       record_vmax=True)
        hot = (out["rates"].max(0) > 0) | (out["vmax"].max(0) > margin_mv)
        must = [self.sugar, self.bitter, [self.mn9], self.lesion] + list(write_groups)
        keep = np.unique(np.concatenate([np.flatnonzero(hot)] + [np.asarray(m) for m in must]))
        self.W_sub, self.keep = C.subgraph(keep)
        self.pos = np.full(C.N, -1, dtype=np.int64)
        self.pos[self.keep] = np.arange(len(self.keep))
        self.log(f"  alt ağ: {len(self.keep)} nöron, {self.W_sub.nnz} bağlantı "
                 f"(tam beyin: {C.N} / {C.W.nnz})")

    def add_to_subgraph(self, idx):
        idx = np.asarray(idx)
        if np.all(self.pos[idx] >= 0):
            return
        keep = np.union1d(self.keep, idx)
        self.W_sub, self.keep = self.C.subgraph(keep)
        self.pos = np.full(self.C.N, -1, dtype=np.int64)
        self.pos[self.keep] = np.arange(len(self.keep))

    # ------------------------------------------------------------------ simülasyon
    def run(self, sugar_hz, bitter_hz, lesion, implant=None, gains=None, offsets=None,
            t_ms=1000.0, seed=0, full_brain=False, return_all=False):
        """Batch koşusu. sugar_hz/bitter_hz/lesion: (B,) diziler. MN9 hızlarını döner."""
        sugar_hz = np.asarray(sugar_hz, dtype=float)
        B = len(sugar_hz)
        if full_brain:
            W, m = self.C.W, (lambda i: np.asarray(i))
            N = self.C.N
        else:
            W, m = self.W_sub, (lambda i: self.pos[np.asarray(i)])
            N = len(self.keep)
        stims = [Stim(m(self.sugar), sugar_hz), Stim(m(self.bitter), bitter_hz)]
        sil = np.zeros((B, N), dtype=bool)
        sil[np.asarray(lesion, dtype=bool)[:, None] & np.isin(np.arange(N), m(self.lesion))[None, :]] = True
        imp = None
        if implant is not None:
            imp = Implant(m(implant.read), m(implant.write), gains, offsets)
        out = simulate(W, B, t_ms, stims=stims, silence=sil, implant=imp, seed=seed)
        mn9 = out["rates"][:, m([self.mn9])[0]]
        return (mn9, out) if return_all else mn9

    # ------------------------------------------------------------------ 2) hedef + karakterizasyon
    def characterize(self, reps=6, t_ms=1000.0):
        """Lezyonlu beyinde her nöronun tatlı sürüşünü ve acı baskılanmasını ölçer."""
        conds = [(0, 0), (SUGAR_FOR_BITTER_TEST, 0), (SUGAR_FOR_BITTER_TEST, 100), (0, 100)]
        s = np.repeat([c[0] for c in conds], reps)
        b = np.repeat([c[1] for c in conds], reps)
        _, out = self.run(s, b, np.ones(len(s), bool), t_ms=t_ms, seed=self.seed + 7,
                          return_all=True)
        R = out["rates"].reshape(len(conds), reps, -1).mean(1)
        rate = dict(none=R[0], sugar=R[1], sugar_bitter=R[2], bitter=R[3])
        # tatlı GRN'lerden (uyarıcı kenarlarla) sinaptik adım sayısı
        Wp = self.W_sub.copy()
        Wp.data[Wp.data < 0] = 0
        Wp.eliminate_zeros()
        hop = np.full(len(self.keep), 99)
        dq = deque()
        for i in self.pos[self.sugar]:
            hop[i] = 0
            dq.append(i)
        while dq:
            u = dq.popleft()
            for v in Wp.indices[Wp.indptr[u]:Wp.indptr[u + 1]]:
                if hop[v] == 99:
                    hop[v] = hop[u] + 1
                    dq.append(v)
        drive = rate["sugar"] - rate["none"]
        bmi = np.where(rate["sugar"] > 0, 1 - rate["sugar_bitter"] / np.maximum(rate["sugar"], 1e-9), 0.0)
        return rate, hop, drive, bmi

    def select_designs(self, rate, hop, drive, bmi):
        """Okuma/yazma yerlerini kurallarla seçer (elle seçim yok, tekrar üretilebilir)."""
        n = len(self.keep)
        banned = np.zeros(n, dtype=bool)
        banned[self.pos[np.concatenate([self.sugar, self.bitter, self.lesion, [self.mn9, self.premotor]])]] = True

        # ERKEN: GRN'den 1 adım, güçlü tatlı sürüşü, acıdan etkilenmiyor (saf tatlı bilgisi)
        early = np.flatnonzero(~banned & (hop == 1) & (drive > 50) & (np.abs(bmi) < 0.05) & (rate["bitter"] < 5))
        early = early[np.argsort(-rate["sugar"][early])][:N_READ]
        # GEÇ: tatlı sürüyor ama acı gelince susuyor (tatlı-acı hesabı zaten yapılmış)
        late = np.flatnonzero(~banned & (hop >= 2) & (drive > 30) & (bmi > 0.9) & (rate["bitter"] < 5))
        late = late[np.argsort(-rate["sugar"][late])][:N_READ]
        # SAHTE: hiçbir koşulda spike atmayan nöronlar (bilgi taşımayan okuma)
        silent = np.flatnonzero(~banned & (rate["sugar"] == 0) & (rate["bitter"] == 0) & (rate["sugar_bitter"] == 0))
        rng = np.random.default_rng(self.seed + 3)
        sham = rng.choice(silent, size=N_READ, replace=False)

        full = lambda sub_idx: self.keep[sub_idx]
        mn9 = np.array([self.mn9])
        pm = np.array([self.premotor])
        designs = [
            Design("erken_mn9", "Erken okuma -> MN9'a yaz (kestirme)", full(early), mn9),
            Design("erken_premotor", "Erken okuma -> premotora yaz", full(early), pm),
            Design("gec_mn9", "Geç okuma -> MN9'a yaz", full(late), mn9),
            Design("gec_premotor", "Geç okuma -> premotora yaz", full(late), pm),
            Design("sahte_mn9", "Sahte okuma -> MN9'a yaz (kontrol)", full(sham), mn9),
        ]
        info = dict(
            early=[dict(id=self.fid(i)[0], name=self.name_of.get(int(i), ""), hop=int(hop[self.pos[i]]),
                        sugar_hz=float(rate["sugar"][self.pos[i]]), bmi=float(bmi[self.pos[i]])) for i in full(early)],
            late=[dict(id=self.fid(i)[0], name=self.name_of.get(int(i), ""), hop=int(hop[self.pos[i]]),
                       sugar_hz=float(rate["sugar"][self.pos[i]]), bmi=float(bmi[self.pos[i]])) for i in full(late)],
            sham=self.fid(full(sham)),
            mn9=self.fid(mn9), premotor=self.fid(pm),
            premotor_weight_mV=float(self.C.W[self.mn9, self.premotor]),
            lesion=self.fid(self.lesion),
        )
        return designs, info

    # ------------------------------------------------------------------ 5) eğitim
    def _grid(self, design, gains, offsets, reps, t_ms, target, seed_shift):
        grid = [(g, o) for g in gains for o in offsets]
        G, L = len(grid), len(SUGAR_LEVELS)
        s = np.tile(np.repeat(SUGAR_LEVELS, reps), G)
        gg = np.repeat([p[0] for p in grid], L * reps)
        oo = np.repeat([p[1] for p in grid], L * reps)
        mn9 = self.run(s, np.zeros(len(s)), np.ones(len(s), bool), implant=design,
                       gains=gg, offsets=oo, t_ms=t_ms, seed=self.seed + seed_shift)
        curves = mn9.reshape(G, L, reps).mean(2)
        loss = np.sqrt(((curves - target[None, :]) ** 2).mean(1))
        best = int(np.argmin(loss))
        return grid[best], float(loss[best]), loss

    def train(self, design, gains, offsets, reps=2, t_ms=600.0, target=None, refine=True):
        """İki aşamalı ızgara araması; kayıp = tatlı eğrisinin sağlam beyinden RMSE farkı.
        Acı koşulları burada HİÇ yok."""
        (g0, o0), l0, loss = self._grid(design, gains, offsets, reps, t_ms, target, 11)
        gi, oi = gains.index(g0), offsets.index(o0)
        out = dict(gain=float(g0), offset=float(o0), rmse=l0,
                   coarse_at_boundary=bool(gi in (0, len(gains) - 1) or oi in (0, len(offsets) - 1)),
                   coarse_loss=loss.reshape(len(gains), len(offsets)).tolist())
        if refine:
            fg = np.unique(np.round(np.linspace(gains[max(gi - 1, 0)], gains[min(gi + 1, len(gains) - 1)], 5), 3)).tolist()
            fo = np.unique(np.round(np.linspace(offsets[max(oi - 1, 0)], offsets[min(oi + 1, len(offsets) - 1)], 5), 2)).tolist()
            (g1, o1), l1, _ = self._grid(design, fg, fo, reps, t_ms, target, 13)
            out.update(gain=float(g1), offset=float(o1), rmse=l1)
        return out

    # ------------------------------------------------------------------ 6) test
    def evaluate(self, design=None, gain=0.0, offset=0.0, lesion=True, reps=8, t_ms=1000.0,
                 full_brain=False, seed_shift=0):
        """Tatlı eğrisi (eğitim koşulları) + acı testi (eğitimde görülmemiş)."""
        s = np.concatenate([np.repeat(SUGAR_LEVELS, reps),
                            np.full(len(BITTER_LEVELS) * reps, SUGAR_FOR_BITTER_TEST)])
        b = np.concatenate([np.zeros(len(SUGAR_LEVELS) * reps), np.repeat(BITTER_LEVELS, reps)])
        B = len(s)
        mn9 = self.run(s, b, np.full(B, lesion), implant=design,
                       gains=np.full(B, gain), offsets=np.full(B, offset),
                       t_ms=t_ms, seed=self.seed + 1000 + seed_shift, full_brain=full_brain)
        k = len(SUGAR_LEVELS) * reps
        dose = mn9[:k].reshape(len(SUGAR_LEVELS), reps)
        bit = mn9[k:].reshape(len(BITTER_LEVELS), reps)
        return dict(dose_mean=dose.mean(1).tolist(), dose_sem=(dose.std(1) / np.sqrt(reps)).tolist(),
                    bitter_mean=bit.mean(1).tolist(), bitter_sem=(bit.std(1) / np.sqrt(reps)).tolist())


def bitter_preservation(intact, other):
    """Acı altında 'hortum uzatma oranı' eğrilerinin benzerliği.
    oran(b) = MN9(tatlı160, acı b) / MN9(tatlı160, acı 0).  1 = sağlam beyinle aynı, 0 = tamamen kayıp."""
    bi = np.asarray(intact["bitter_mean"])
    bo = np.asarray(other["bitter_mean"])
    ri = bi[1:] / max(bi[0], 1e-9)
    ro = bo[1:] / max(bo[0], 1e-9)
    lost = 1 - ri  # sağlam beyindeki baskılama miktarı
    got = 1 - ro
    return float(np.clip(1 - np.abs(lost - got).sum() / max(lost.sum(), 1e-9), 0, 1))


def bitter_bias(intact, other):
    """İşaretli sapma (acılı koşulların ortalaması): oran_implant - oran_sağlam.
    + : acıyı az duyuyor (baskılama eksik)   - : acıyı fazla duyuyor (aşırı baskılama)"""
    bi = np.asarray(intact["bitter_mean"])
    bo = np.asarray(other["bitter_mean"])
    return float((bo[1:] / max(bo[0], 1e-9) - bi[1:] / max(bi[0], 1e-9)).mean())

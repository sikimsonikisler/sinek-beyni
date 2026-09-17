"""FlyWire connectome'unu yükleyip seyrek ağırlık matrisine çevirir.

Ağırlık kuralı Shiu et al. (2024) ile aynı:
    w = (sinaps sayısı) x (+1 uyarıcı / -1 baskılayıcı) x 0.275 mV
Matris CSC formatında: satır = postsinaptik, sütun = presinaptik.
Böylece j nöronu spike attığında etkilediği nöronlar W[:, j] sütunudur.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import sparse

W_SYN_MV = 0.275  # sinaps başına mV (Shiu et al. 2024, serbest parametre)

DATASETS = {
    # Makalede kullanılan ve bu projedeki nöron ID'lerinin tamamının geçerli olduğu sürüm
    "630": ("2023_03_23_completeness_630_final.csv", "2023_03_23_connectivity_630_final.parquet"),
    # Güncel public sürüm; bazı ID'ler değişmiş olabilir (neurons.py uyarı verir)
    "783": ("Completeness_783.csv", "Connectivity_783.parquet"),
}


class Connectome:
    def __init__(self, data_dir="data/shiu_repo", version="630"):
        data_dir = Path(data_dir)
        comp_file, con_file = DATASETS[version]
        comp = pd.read_csv(data_dir / comp_file, index_col=0)
        self.version = version
        self.ids = comp.index.to_numpy(np.int64)
        self.N = len(self.ids)
        self.id2idx = {int(fid): i for i, fid in enumerate(self.ids)}

        cols = ["Presynaptic_Index", "Postsynaptic_Index", "Excitatory x Connectivity"]
        tb = pq.read_table(data_dir / con_file, columns=cols)
        pre = tb.column(0).to_numpy().astype(np.int32)
        post = tb.column(1).to_numpy().astype(np.int32)
        w = tb.column(2).to_numpy().astype(np.float32) * np.float32(W_SYN_MV)
        del tb
        self.W = sparse.csc_matrix((w, (post, pre)), shape=(self.N, self.N), dtype=np.float32)
        del pre, post, w

    # ---------- ID yardımcıları ----------
    def idx(self, flywire_ids, strict=False):
        """FlyWire ID listesini matris indekslerine çevirir, eksikleri atlar."""
        out, missing = [], []
        for f in flywire_ids:
            i = self.id2idx.get(int(f))
            (out if i is not None else missing).append(i if i is not None else f)
        if missing and strict:
            raise KeyError(f"{len(missing)} ID bu sürümde yok: {missing[:3]}...")
        return np.array(out, dtype=np.int64), missing

    # ---------- graf yardımcıları ----------
    def out_neighbors(self, idx):
        """idx nöronlarının doğrudan hedefleri (postsinaptik)."""
        idx = np.asarray(idx)
        sub = self.W[:, idx]
        return np.unique(sub.indices)

    def in_neighbors(self, idx):
        """idx nöronlarına doğrudan girdi veren nöronlar (presinaptik)."""
        idx = np.asarray(idx)
        sub = self.W[idx, :].tocsc()
        return np.flatnonzero(np.diff(sub.indptr) > 0)

    def subgraph(self, keep_idx):
        """Sadece keep_idx nöronlarını içeren alt ağ. (W_sub, keep_idx) döner.

        LIF modelinde bazal aktivite sıfır olduğundan hiç spike atmayan bir nöronun
        ağa etkisi de sıfırdır. Bu yüzden deneyde aktif olan (veya eşiğe yaklaşan)
        nöronları içeren alt ağ, tam beyinle aynı sonucu verir. Bu varsayım
        run_experiments.py içinde tam beyinle ayrıca doğrulanır.
        """
        keep_idx = np.unique(np.asarray(keep_idx, dtype=np.int64))
        W_sub = self.W[keep_idx, :][:, keep_idx].tocsc()
        return W_sub, keep_idx

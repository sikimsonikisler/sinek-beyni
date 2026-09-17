"""İsteğe bağlı: Köprü simülatörünü, Shiu et al.'ın ORİJİNAL Brian2 denklemleriyle birebir karşılaştırır.

    pip install brian2 joblib
    python check_brian2.py

Aynı alt ağda aynı uyarımla iki simülatör koşturulur; nöron hızlarının korelasyonu ve MN9 raporlanır.
Not: Brian2, refrakter dönemde gelen sinaptik girdileri yok sayar ("unless refractory" değişkenleri
için ürettiği kod yalnızca refrakter olmayan hedeflere ekleme yapar). Köprü de aynı kuralı uygular;
bu kural olmadan hızlar ~%24 yüksek çıkıyordu.
"""
import importlib.util
import time

import numpy as np

from kopru import neurons as nr
from kopru.connectome import Connectome
from kopru.lif import Stim, simulate

DATA = "data/shiu_repo"
spec = importlib.util.spec_from_file_location("shiu_model", f"{DATA}/model.py")
shiu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shiu)
P = shiu.default_params

from brian2 import (Hz, Network, NeuronGroup, PoissonInput, SpikeMonitor, Synapses,  # noqa: E402
                    mV, ms, prefs, seed)

prefs.codegen.target = "numpy"
RATE, T_MS, N_KOPRU, N_BRIAN = 200, 1000.0, 8, 4

C = Connectome(DATA, "630")
sug = C.idx(nr.SUGAR_GRN, strict=True)[0]
mn9 = C.id2idx[nr.MN9_LEFT]
out = simulate(C.W, 4, T_MS, stims=[Stim(sug, [RATE] * 4)], seed=3, record_vmax=True)
keep = np.flatnonzero((out["rates"].max(0) > 0) | (out["vmax"].max(0) > -48.0))
keep = np.union1d(np.union1d(keep, sug), [mn9])
Ws, keep = C.subgraph(keep)
pos = {int(k): i for i, k in enumerate(keep)}
sug_s, mn9_s = np.array([pos[int(i)] for i in sug]), pos[mn9]
print(f"Alt ağ: {len(keep)} nöron, {Ws.nnz} bağlantı")

t = time.time()
rk = simulate(Ws, N_KOPRU, T_MS, stims=[Stim(sug_s, [RATE] * N_KOPRU)], seed=11)["rates"].mean(0)
tk = (time.time() - t) / N_KOPRU

coo = Ws.tocoo()


def brian_trial(s):
    seed(s)
    neu = NeuronGroup(len(keep), model=P["eqs"], method="linear", threshold=P["eq_th"],
                      reset=P["eq_rst"], refractory="rfc", namespace=P)
    neu.v, neu.g, neu.rfc = P["v_0"], 0, P["t_rfc"]
    syn = Synapses(neu, neu, "w : volt", on_pre="g += w", delay=P["t_dly"])
    syn.connect(i=coo.col.astype(int), j=coo.row.astype(int))
    syn.w = coo.data.astype(float) * mV
    pois = []
    for i in sug_s:
        pois.append(PoissonInput(target=neu[int(i)], target_var="v", N=1, rate=RATE * Hz,
                                 weight=P["w_syn"] * P["f_poi"]))
        neu[int(i)].rfc = 0 * ms
    mon = SpikeMonitor(neu)
    Network(neu, syn, mon, *pois).run(T_MS * ms)
    return np.bincount(np.asarray(mon.i), minlength=len(keep)) / (T_MS / 1000)


t = time.time()
rb = np.mean([brian_trial(s) for s in range(N_BRIAN)], axis=0)
tb = (time.time() - t) / N_BRIAN
m = ((rb > 0) | (rk > 0))
m[sug_s] = False
print(f"Pearson r (tatlı GRN'ler hariç aktif nöronlar): {np.corrcoef(rb[m], rk[m])[0, 1]:.4f}")
print(f"Medyan hız oranı Köprü/Brian2 (>20 Hz): {np.median(rk[m & (rb > 20)] / rb[m & (rb > 20)]):.3f}")
print(f"MN9: Brian2 {rb[mn9_s]:.1f} Hz | Köprü {rk[mn9_s]:.1f} Hz")
print(f"Deneme başına süre: Brian2 {tb:.1f} s | Köprü {tk:.2f} s")

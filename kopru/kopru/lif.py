"""Batched leaky integrate-and-fire simülatörü (Brian2 gerektirmez).

Dinamikler Shiu et al. (2024) modelinin yeniden yazımı:
    dv/dt = (v0 - v + g) / tau_m     (refrakter dönemde durur)
    dg/dt = -g / tau_syn
    v > v_th  ->  spike, v = v_reset, g = 0
    presinaptik spike -> 1.8 ms sonra hedefte g += w

Hız için iki fikir:
1) "Batch": B bağımsız deneme/koşul aynı anda simüle edilir. Durum dizileri B x N
   boyutundadır ve düz (flat) tutulur. Farklı batch elemanları farklı uyarım hızı,
   farklı susturma maskesi veya farklı implant parametresi kullanabilir. Böylece bir
   parametre taraması tek bir simülasyonda yapılır.
2) "Olay tabanlı iletim": sadece o adımda spike atan nöronların CSC sütunları okunur,
   iletimler bekleyen olaylar kuyruğuna yazılır. Tam matris çarpımı yoktur.
"""
import numpy as np

DEFAULT_PARAMS = dict(
    dt=0.1,            # ms
    v0=-52.0,          # mV, dinlenme
    v_reset=-52.0,     # mV
    v_th=-45.0,        # mV
    tau_m=20.0,        # ms
    tau_syn=5.0,       # ms
    t_ref=2.2,         # ms
    t_delay=1.8,       # ms
    poisson_kick=0.275 * 250,  # mV, Shiu: w_syn * f_poi (tek olay spike'a yeter)
)


class Stim:
    """Bir nöron grubuna Poisson uyarımı. rates_hz: her batch elemanı için bir hız (B,)."""

    def __init__(self, idx, rates_hz):
        self.idx = np.asarray(idx, dtype=np.int64)
        self.rates = np.atleast_1d(np.asarray(rates_hz, dtype=np.float64))


class Implant:
    """Nöroprotez: okuma nöronlarının ortalama hızına bakıp yazma nöronlarını uyarır.

    Her `window_ms` sonunda:
        r      = okuma grubunun son penceredeki ortalama spike hızı (Hz)
        stim   = clip(gain * (r - offset), 0, max_rate)
    Sonraki pencere boyunca yazma nöronlarına `stim` hızında Poisson uyarımı verilir.
    gain/offset batch başına farklı olabilir (B,), böylece ızgara taraması tek koşuda yapılır.

    Kapasite bilinçli olarak küçük tutuldu (2 parametre, tek skaler okuma). Eğitilebilir
    arayüz ne kadar güçlü olursa, çalışmayan bir beyni de o kadar "çalışıyormuş gibi"
    gösterebilir; bu yüzden implantın gücü sınırlı.
    """

    def __init__(self, read_idx, write_idx, gain, offset, window_ms=10.0, max_rate=200.0):
        self.read_idx = np.asarray(read_idx, dtype=np.int64)
        self.write_idx = np.asarray(write_idx, dtype=np.int64)
        self.gain = np.atleast_1d(np.asarray(gain, dtype=np.float64))
        self.offset = np.atleast_1d(np.asarray(offset, dtype=np.float64))
        self.window_ms = float(window_ms)
        self.max_rate = float(max_rate)


def simulate(W, n_batch, t_ms, stims=(), silence=None, implant=None, seed=0,
             params=None, record_vmax=False):
    """W: scipy CSC (satır=post, sütun=pre, mV). Dönüş: dict(rates=(B,N) Hz, ...)."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    N = W.shape[0]
    B = int(n_batch)
    BN = B * N
    rng = np.random.default_rng(seed)

    dt = p["dt"]
    n_steps = int(round(t_ms / dt))
    a = np.float32(np.exp(-dt / p["tau_m"]))
    c = np.float32(np.exp(-dt / p["tau_syn"]))
    b = np.float32(p["tau_syn"] / (p["tau_syn"] - p["tau_m"])
                   * (np.exp(-dt / p["tau_syn"]) - np.exp(-dt / p["tau_m"])))
    v0 = np.float32(p["v0"])
    v_th = np.float32(p["v_th"])
    v_reset = np.float32(p["v_reset"])
    kick = np.float32(p["poisson_kick"])
    D = int(round(p["t_delay"] / dt))
    # Brian2 semantiği: spike'tan sonraki 21 adım integrasyon ve eşik yok;
    # spike adımı dahil 22 adım boyunca gelen sinaptik girdiler YOK SAYILIR.
    R = max(int(round(p["t_ref"] / dt)) - 1, 1)
    ring = D + 1

    v = np.full(BN, v0, dtype=np.float32)
    g = np.zeros(BN, dtype=np.float32)
    counts = np.zeros(BN, dtype=np.int32)
    vmax = np.full(BN, v0, dtype=np.float32) if record_vmax else None
    pending = [[] for _ in range(ring)]  # her slot: [(flat_idx, w), ...]

    indptr = W.indptr.astype(np.int64)
    indices = W.indices.astype(np.int64)
    data = W.data.astype(np.float32)

    batch_base = (np.arange(B, dtype=np.int64) * N)[:, None]

    # Uyarılan nöronlarda refrakter dönem yok (Shiu modelindeki gibi)
    no_ref = np.zeros(N, dtype=bool)
    stim_groups = []
    for s in stims:
        rates = np.broadcast_to(s.rates, (B,)).astype(np.float64)
        prob = rates * dt / 1000.0
        if np.any(prob > 0):
            no_ref[s.idx] = True
            stim_groups.append((batch_base + s.idx[None, :], prob[:, None]))
    ref_hist = [np.empty(0, dtype=np.int64) for _ in range(R)]
    is_ref = np.zeros(BN, dtype=bool)  # ref_hist'teki girdilerin maskesi

    sil = None
    if silence is not None:
        sil = np.broadcast_to(np.asarray(silence, dtype=bool), (B, N)).reshape(-1).copy()

    if implant is not None:
        is_read = np.zeros(N, dtype=bool)
        is_read[implant.read_idx] = True
        w_flat = batch_base + implant.write_idx[None, :]
        gain = np.broadcast_to(implant.gain, (B,))
        offset = np.broadcast_to(implant.offset, (B,))
        win_steps = max(int(round(implant.window_ms / dt)), 1)
        win_counts = np.zeros(B, dtype=np.float64)
        imp_prob = np.zeros((B, 1))
        n_read = max(len(implant.read_idx), 1)
        stim_log = []

    for t in range(n_steps):
        # --- 1) integrasyon (refrakter olanlar hariç) ---
        ref_idx = np.concatenate(ref_hist)
        if ref_idx.size:
            v_saved = v[ref_idx]
            g_saved = g[ref_idx]
        v -= v0
        v *= a
        v += v0
        v += g * b
        g *= c
        if ref_idx.size:
            v[ref_idx] = v_saved
            g[ref_idx] = g_saved
        if vmax is not None:
            np.maximum(vmax, v, out=vmax)

        # --- 2) eşik ---
        spk = np.flatnonzero(v > v_th)
        if spk.size and ref_idx.size:
            spk = spk[~is_ref[spk]]

        # --- 3) sinaptik iletim (gecikmeli olaylar) + Poisson uyarımları ---
        slot = t % ring
        if spk.size:
            is_ref[spk] = True  # bu adımda spike atanlar da girdi almaz
        if pending[slot]:
            flat = np.concatenate([x[0] for x in pending[slot]])
            ww = np.concatenate([x[1] for x in pending[slot]])
            ok = ~is_ref[flat]
            np.add.at(g, flat[ok], ww[ok])
            pending[slot] = []
        for flat_idx, prob in stim_groups:
            ev = rng.random(flat_idx.shape) < prob
            if ev.any():
                tgt = flat_idx[ev]
                v[tgt[~is_ref[tgt]]] += kick
        if implant is not None and imp_prob.any():
            ev = rng.random(w_flat.shape) < imp_prob
            if ev.any():
                tgt = w_flat[ev]
                v[tgt[~is_ref[tgt]]] += kick

        # --- 4) reset + kayıt + yayılım ---
        old = ref_hist[t % R]
        if old.size:
            is_ref[old] = False
        if spk.size:
            v[spk] = v_reset
            g[spk] = 0.0
            counts[spk] += 1
            jj = spk % N
            is_ref[spk] = False
            new_ref = spk[~no_ref[jj]]
            ref_hist[t % R] = new_ref
            is_ref[new_ref] = True
            if implant is not None:
                m = is_read[jj]
                if m.any():
                    np.add.at(win_counts, spk[m] // N, 1.0)
            sp = spk if sil is None else spk[~sil[spk]]
            if sp.size:
                jj = sp % N
                starts = indptr[jj]
                lens = indptr[jj + 1] - starts
                tot = int(lens.sum())
                if tot:
                    offs = np.repeat(starts - np.cumsum(lens) + lens, lens) + np.arange(tot)
                    flat = np.repeat((sp // N) * N, lens) + indices[offs]
                    pending[(t + D) % ring].append((flat, data[offs]))
        else:
            ref_hist[t % R] = np.empty(0, dtype=np.int64)

        # --- 5) implant penceresi ---
        if implant is not None and (t + 1) % win_steps == 0:
            r_read = win_counts / (n_read * implant.window_ms / 1000.0)
            stim = np.clip(gain * (r_read - offset), 0.0, implant.max_rate)
            imp_prob = (stim * dt / 1000.0)[:, None]
            win_counts[:] = 0.0
            stim_log.append(stim.copy())

    out = dict(rates=(counts.reshape(B, N) / (t_ms / 1000.0)))
    if vmax is not None:
        out["vmax"] = vmax.reshape(B, N)
    if implant is not None:
        out["implant_stim"] = np.array(stim_log)  # (pencere, B)
    return out

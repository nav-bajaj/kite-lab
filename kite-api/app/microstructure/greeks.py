"""Stage 1 — measured options math (Black-Scholes, spot underlying, q=0).

Assumption set (documented, versioned — tasks/microstructure_engine/PLAN.md):
flat r, no dividend yield, expiry cutoff 15:30 IST, T in calendar/365.
IV is inverted with vectorized bisection — slower than Newton per
iteration but monotone-safe for deep ITM/OTM where vega vanishes.
All array functions are numpy-vectorized; NaN means "not computable"
(below intrinsic, expired, missing inputs) and is never interpolated.
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timezone, timedelta
from typing import Dict

import numpy as np

ENGINE_VERSION = "bs-spot-q0-v1"

IST = timezone(timedelta(hours=5, minutes=30))
# Expiry cutoff for T. F&O now TRADES to 15:40 (NSE change 2026-08),
# but index-option settlement is anchored to the underlying's close
# (equity session, 15:30) — so T runs to 15:30 pending confirmation
# from the circular. Expiry-day bars after 15:30 therefore get T=0 ->
# IV NULL (honest). First extended expiry (2026-08-04) will show
# empirically whether premium persists 15:30-15:40; revisit then.
EXPIRY_CUTOFF = time(15, 30)

_erf = np.frompyfunc(math.erf, 1, 1)


def _cdf(x):
    return 0.5 * (1.0 + _erf(x / math.sqrt(2.0)).astype(np.float64))


def _pdf(x):
    return np.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def t_years(ts: datetime, expiry: date) -> float:
    """Year fraction to the 15:30 IST expiry cutoff; 0 at/after cutoff."""
    exp_dt = datetime.combine(expiry, EXPIRY_CUTOFF, tzinfo=IST)
    return max(0.0, (exp_dt - ts).total_seconds()) / (365.0 * 86400.0)


def _d1_d2(S, K, T, r, sigma):
    srt = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma * sigma) * T) / srt
    return d1, d1 - srt


def bs_price_vec(S, K, T, r, sigma, is_call):
    """Vectorized BS price; T==0 returns intrinsic."""
    S, K, T, sigma = (np.asarray(a, dtype=float) for a in (S, K, T, sigma))
    is_call = np.asarray(is_call)
    out = np.where(is_call, np.maximum(S - K, 0.0), np.maximum(K - S, 0.0)).astype(float)
    live = T > 0
    if np.any(live):
        d1, d2 = _d1_d2(S[live], K[live], T[live], r, sigma[live])
        disc = np.exp(-r * T[live])
        call = S[live] * _cdf(d1) - K[live] * disc * _cdf(d2)
        put = K[live] * disc * _cdf(-d2) - S[live] * _cdf(-d1)
        out[live] = np.where(is_call[live], call, put)
    return out


def bs_price(S: float, K: float, T: float, r: float, sigma: float, kind: str) -> float:
    return float(bs_price_vec([S], [K], [T], r, [sigma], [kind == "CE"])[0])


def _bisect_iv(price_fn, price, U, K, T, r, is_call, disc_intrinsic, lo=0.005, hi=5.0, iters=64):
    """Monotone-safe vectorized bisection shared by both pricing models."""
    valid = (T > 0) & (price > np.maximum(disc_intrinsic, 0.0) + 1e-9) & np.isfinite(price) & (price > 0)
    lo_a = np.full(price.shape, lo)
    hi_a = np.full(price.shape, hi)
    for _ in range(iters):
        mid = 0.5 * (lo_a + hi_a)
        pm = price_fn(U, K, T, r, mid, is_call)
        too_low = pm < price
        lo_a = np.where(too_low, mid, lo_a)
        hi_a = np.where(too_low, hi_a, mid)
    iv = 0.5 * (lo_a + hi_a)
    attainable = price_fn(U, K, T, r, np.full(price.shape, hi), is_call) >= price
    return np.where(valid & attainable, iv, np.nan)


def implied_vol(price, S, K, T, r, kind):
    """Spot Black-Scholes IV. NaN = not computable (never interpolated)."""
    price, S, K, T = (np.asarray(a, dtype=float) for a in (price, S, K, T))
    is_call = np.asarray(kind) == "CE"
    disc_intrinsic = np.where(is_call, S - K * np.exp(-r * T), K * np.exp(-r * T) - S)
    return _bisect_iv(bs_price_vec, price, S, K, T, r, is_call, disc_intrinsic)


# -- Black-76 on the futures-implied forward ---------------------------------
#
# The observable forward embeds dividends, so pricing off it removes the
# q=0 error that splits same-strike CE/PE IVs under the spot model.

def forward_from_futures(fut_price: float, t_fut: float, t_opt: float, r: float) -> float:
    """De-carry the futures price from its own expiry back to the option's:
    F_opt = F_fut * e^{-r (t_fut - t_opt)}. Dividend flow between the two
    expiries is NOT observable here — acceptable for near-dated options."""
    return fut_price * math.exp(-r * (t_fut - t_opt))


def b76_price_vec(F, K, T, r, sigma, is_call):
    F, K, T, sigma = (np.asarray(a, dtype=float) for a in (F, K, T, sigma))
    is_call = np.asarray(is_call)
    disc = np.exp(-r * T)
    out = disc * np.where(is_call, np.maximum(F - K, 0.0), np.maximum(K - F, 0.0))
    live = T > 0
    if np.any(live):
        srt = sigma[live] * np.sqrt(T[live])
        d1 = (np.log(F[live] / K[live]) + 0.5 * sigma[live] ** 2 * T[live]) / srt
        d2 = d1 - srt
        call = disc[live] * (F[live] * _cdf(d1) - K[live] * _cdf(d2))
        put = disc[live] * (K[live] * _cdf(-d2) - F[live] * _cdf(-d1))
        out[live] = np.where(is_call[live], call, put)
    return out


def b76_price(F: float, K: float, T: float, r: float, sigma: float, kind: str) -> float:
    return float(b76_price_vec([F], [K], [T], r, [sigma], [kind == "CE"])[0])


def implied_vol_b76(price, F, K, T, r, kind):
    price, F, K, T = (np.asarray(a, dtype=float) for a in (price, F, K, T))
    is_call = np.asarray(kind) == "CE"
    disc = np.exp(-r * T)
    disc_intrinsic = disc * np.where(is_call, F - K, K - F)
    return _bisect_iv(b76_price_vec, price, F, K, T, r, is_call, disc_intrinsic)


def greeks_b76(F, K, T, r, sigma, kind) -> Dict[str, np.ndarray]:
    """Forward-space Greeks (delta/gamma wrt F). theta per YEAR."""
    F, K, T, sigma = (np.asarray(a, dtype=float) for a in (F, K, T, sigma))
    is_call = np.asarray(kind) == "CE"
    out = {k: np.full(F.shape, np.nan) for k in ("delta", "gamma", "vega", "theta")}
    live = (T > 0) & np.isfinite(sigma)
    if not np.any(live):
        return out
    Fl, Kl, Tl, sl, cl = F[live], K[live], T[live], sigma[live], is_call[live]
    srt = sl * np.sqrt(Tl)
    d1 = (np.log(Fl / Kl) + 0.5 * sl * sl * Tl) / srt
    d2 = d1 - srt
    disc = np.exp(-r * Tl)
    pdf1 = _pdf(d1)
    out["delta"][live] = np.where(cl, disc * _cdf(d1), disc * (_cdf(d1) - 1.0))
    out["gamma"][live] = disc * pdf1 / (Fl * srt)
    out["vega"][live] = disc * Fl * pdf1 * np.sqrt(Tl)
    price_now = np.where(cl, disc * (Fl * _cdf(d1) - Kl * _cdf(d2)), disc * (Kl * _cdf(-d2) - Fl * _cdf(-d1)))
    out["theta"][live] = -(disc * Fl * pdf1 * sl) / (2.0 * np.sqrt(Tl)) + r * price_now
    return out


def greeks(S, K, T, r, sigma, kind) -> Dict[str, np.ndarray]:
    """delta / gamma / vega / theta (theta per YEAR; caller may rescale).
    NaN propagates wherever sigma is NaN or T == 0."""
    S, K, T, sigma = (np.asarray(a, dtype=float) for a in (S, K, T, sigma))
    is_call = np.asarray(kind) == "CE"
    out = {k: np.full(S.shape, np.nan) for k in ("delta", "gamma", "vega", "theta")}
    live = (T > 0) & np.isfinite(sigma)
    if not np.any(live):
        return out
    Sl, Kl, Tl, sl = S[live], K[live], T[live], sigma[live]
    cl = is_call[live]
    d1, d2 = _d1_d2(Sl, Kl, Tl, r, sl)
    pdf1 = _pdf(d1)
    disc = np.exp(-r * Tl)
    out["delta"][live] = np.where(cl, _cdf(d1), _cdf(d1) - 1.0)
    out["gamma"][live] = pdf1 / (Sl * sl * np.sqrt(Tl))
    out["vega"][live] = Sl * pdf1 * np.sqrt(Tl)
    theta_common = -(Sl * pdf1 * sl) / (2.0 * np.sqrt(Tl))
    out["theta"][live] = np.where(
        cl,
        theta_common - r * Kl * disc * _cdf(d2),
        theta_common + r * Kl * disc * _cdf(-d2),
    )
    return out

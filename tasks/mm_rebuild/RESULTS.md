# Results — every run counted; in-sample only until §4

Harness: `tasks/om25_rebuild/lib` (same engine, store, slippage 20 bps,
price return). IS 2010-01-01 → 2015-12-31; runs end 2015-12-31 so nothing
past it is simulated. Mechanics for §1: 25 positions, exit buffer 20,
monthly entry and exit, no stop, fully invested, no filter.

## §1 — score × lookback × universe (12 trials) — IS 2010-2015

Monthly entry and exit, 25 / 20, no stop, no filter. CAGR / Sharpe / MaxDD;
trades per year, hit rate, mean holding days. NIFTY 100 did 7.8% over the window.

| Universe | Score | 6m (126) | 9m (189) | 12m (252) |
|---|---|---|---|---|
| Nifty 250 | absolute | 13.3% / 0.45 / −31% | 14.6% / 0.54 / −35% | 15.2% / 0.59 / −31% |
| Nifty 250 | vol-adjusted | 17.3% / 0.78 / −30% | 17.9% / 0.80 / −30% | **19.6% / 0.96 / −22%** |
| NSE 500 | absolute | 24.4% / 0.90 / −31% | 18.8% / 0.66 / −36% | 18.7% / 0.69 / −32% |
| NSE 500 | vol-adjusted | **24.1% / 1.05 / −28%** | 22.8% / 0.99 / −27% | 21.7% / 0.97 / −27% |

Trades per year 78-167 (longer lookback, fewer trades); hit rate 43-54%;
holds 108-230 days.

Read: **volatility adjustment wins every cell**, by 0.2-0.4 of Sharpe and
with the shallower drawdown, and it is the only version whose hit rate
clears 50%. Lookback splits by universe exactly as it did for OM25 (§3k
there): Nifty 250 wants 12 months, NSE 500 wants 6, and NSE 500's
absolute-momentum row is the noisy one (0.90 at 6m, 0.66 at 9m). Against
the OM25 capture-ratio book on the same window and mechanics (23.7% / 1.50
on Nifty 250, 23.6% / 1.44 on NSE 500) the raw momentum book is 0.4-0.5 of
Sharpe behind before any filter or device; that is the gap §2-§3 have to
close. Deflation for 12 near-identical cells is small; reported at the
close of §3.

Note: §1 ran on the founder's explicit instruction before the gates were
signed; the gate values were proposed before the run and are unchanged.

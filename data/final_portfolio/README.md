# Final Momentum Portfolio (Tracked)

This folder contains the canonical, versioned artifacts for the current “final” momentum portfolio.

- `final_top24_signals.csv`: The latest built signals file (weekly rebalance schedule, ranks/scores).
- `final_portfolio_24.csv`: The latest holdings snapshot intended for execution (labeled by effective order date, with `signal_date` preserved).

These files are updated by `python scripts/run_final_momentum_portfolio.py`.

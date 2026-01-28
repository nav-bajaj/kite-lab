# Kite-Lab Improvements TODO

This document outlines improvements to enhance code quality, testing, and maintainability.

**Created:** 2026-01-28
**Status:** Pending
**Recommended order:** #4 → #2 → #1 → #3

---

## Task #1: Expand Test Coverage for Signal Generation Logic

Add comprehensive tests for the momentum signal generation pipeline.

### Sub-tasks

- [ ] **1.1 Test `build_momentum_signals_flexible.py` core logic**
  - Test momentum calculation with known price data
  - Test volatility floor clipping behavior
  - Test cross-sectional z-score normalization
  - Test ranking logic on rebalance dates
  - Test skip window application (0, 10, 21 days)

- [ ] **1.2 Test edge cases in signal generation**
  - Stocks with missing price data (NaN handling)
  - Stocks with zero or negative prices
  - Single stock in universe (degenerate case)
  - All stocks with identical momentum (tie-breaking)

- [ ] **1.3 Test rebalance frequency logic**
  - Weekly (1-week) rebalance dates
  - Bi-weekly (2-week) rebalance dates
  - Monthly (4-week) rebalance dates
  - Verify correct Thursday/Friday detection

- [ ] **1.4 Test parameter variations**
  - Different lookback periods (L6, L9, L12)
  - Different vol_floor values (0.01-0.10)
  - Different top-N values (10, 24, 50)
  - Different vol_power values

- [ ] **1.5 Integration tests**
  - End-to-end signal generation from price files
  - Verify output CSV format and columns
  - Compare against known good signal file

---

## Task #2: Add Type Hints to Core Scripts

Add Python type annotations to improve code quality and IDE support.

### Sub-tasks

- [ ] **2.1 Add type hints to data_pipeline modules**
  - `price_client.py`: PriceClient class methods
  - `symbol_resolver.py`: find_instrument function
  - `storage.py`: save_dataframe, load_dataframe
  - `qa.py`: validate_prices function

- [ ] **2.2 Add type hints to core scripts**
  - `build_momentum_signals_flexible.py`: main functions
  - `backtest_momentum.py`: simulation functions
  - `report_backtests.py`: report generation functions

- [ ] **2.3 Add type hints to utility scripts**
  - `history_utils.py`: shared download functions
  - `utils.py`: helper utilities

- [ ] **2.4 Create common type definitions**
  - Create `types.py` or use TypedDict for:
    - Price DataFrame structure
    - Signal DataFrame structure
    - Trade record structure
    - Metrics dictionary structure

- [ ] **2.5 Add mypy configuration**
  - Create `mypy.ini` or `pyproject.toml` section
  - Configure strictness level
  - Add to pre-commit hooks (optional)

- [ ] **2.6 Validate type hints**
  - Run mypy on annotated files
  - Fix any type errors discovered
  - Document any intentional `type: ignore` comments

---

## Task #3: Set Up CI/CD Pipeline with GitHub Actions

Create automated testing and validation pipeline using GitHub Actions.

### Sub-tasks

- [ ] **3.1 Create basic test workflow**
  - `.github/workflows/test.yml`
  - Run on push to main and pull requests
  - Set up Python 3.9+ environment
  - Install dependencies from requirements.txt
  - Run pytest with coverage reporting

- [ ] **3.2 Create requirements.txt if not exists**
  - List all production dependencies
  - Pin versions for reproducibility
  - Separate dev dependencies (pytest, mypy, etc.)

- [ ] **3.3 Add linting workflow**
  - Run flake8 or ruff for style checks
  - Run mypy for type checking (after type hints added)
  - Run black/isort for formatting checks (optional)

- [ ] **3.4 Add data validation workflow**
  - Validate static data files (universes, indices lists)
  - Check CSV formats and required columns
  - Verify no sensitive data in commits

- [ ] **3.5 Create pre-commit configuration**
  - `.pre-commit-config.yaml`
  - Local hooks for linting, formatting
  - Prevent committing .env or access tokens

- [ ] **3.6 Add status badges to README**
  - Test status badge
  - Coverage badge (optional)
  - Python version badge

- [ ] **3.7 Consider additional workflows**
  - Dependabot for dependency updates
  - Security scanning (optional)
  - Documentation build (if using Sphinx/MkDocs)

---

## Task #4: Make Hardcoded Paths Configurable

Replace hardcoded `/Users/navdeep/` paths with configurable options.

### Sub-tasks

- [ ] **4.1 Audit all hardcoded paths**
  - Search for `/Users/navdeep/` in all files
  - Search for absolute paths in scripts
  - Document all occurrences and their purposes

- [ ] **4.2 Create centralized configuration**
  - Add path settings to `.env` file:
    - `DATA_BACKUP_DIR` (external backup location)
    - `PROJECT_ROOT` (base directory)
    - `PRICE_DATA_DIR` (nse500_data location)
  - Create `config.py` to load and validate paths

- [ ] **4.3 Update sync_data_backup.py**
  - Read backup destination from environment
  - Fall back to sensible default if not set
  - Add validation that target directory exists

- [ ] **4.4 Update run_daily_pipeline.py**
  - Use relative paths where possible
  - Read external paths from config
  - Add --backup-dir CLI argument as override

- [ ] **4.5 Update other affected scripts**
  - Review all scripts that reference external paths
  - Update to use config module
  - Test with different path configurations

- [ ] **4.6 Add path configuration to documentation**
  - Document required environment variables
  - Add example `.env.example` file
  - Update CLAUDE.md with new configuration options

- [ ] **4.7 Handle cross-platform compatibility**
  - Use pathlib.Path for path operations
  - Avoid hardcoded path separators
  - Test on macOS (current) and document Linux/Windows considerations

---

## Notes

- **Task #4 first**: Fixes path issues that could cause test failures on other machines
- **Task #2 before #1**: Type hints make test code cleaner and catch errors earlier
- **Task #3 last**: CI/CD benefits most when tests and types are already in place

## Quick Commands

```bash
# Run existing tests
pytest tests/

# Check for hardcoded paths
grep -r "/Users/navdeep" scripts/ data_pipeline/

# Run mypy (after adding type hints)
mypy data_pipeline/ scripts/
```

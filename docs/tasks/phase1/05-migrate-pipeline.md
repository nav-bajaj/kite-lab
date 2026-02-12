# Task 5: Migrate Data Pipeline Modules from kite-lab

**Status**: `completed`
**Blocked By**: #1 (Backend Setup)
**Blocks**: None (parallel work)

## Objective

Copy and adapt the data pipeline modules from kite-lab to the new backend structure.

## Tasks

- [ ] Migrate `data_pipeline/symbol_resolver.py`
- [ ] Migrate `data_pipeline/price_client.py`
- [ ] Migrate `data_pipeline/storage.py`
- [ ] Migrate `data_pipeline/qa.py`
- [ ] Copy static data files (universe CSVs)
- [ ] Update imports to work in new structure
- [ ] Create `__init__.py` files

## Files to Migrate

| Source | Destination |
|--------|-------------|
| `kite-lab/data_pipeline/symbol_resolver.py` | `kite-api/app/engine/data_pipeline/symbol_resolver.py` |
| `kite-lab/data_pipeline/price_client.py` | `kite-api/app/engine/data_pipeline/price_client.py` |
| `kite-lab/data_pipeline/storage.py` | `kite-api/app/engine/data_pipeline/storage.py` |
| `kite-lab/data_pipeline/qa.py` | `kite-api/app/engine/data_pipeline/qa.py` |

## Static Data Files

| Source | Destination |
|--------|-------------|
| `kite-lab/data/static/nse500_universe.csv` | `kite-api/data/static/nse500_universe.csv` |
| `kite-lab/data/static/nifty100_universe.csv` | `kite-api/data/static/nifty100_universe.csv` |
| `kite-lab/data/static/nifty250_universe.csv` | `kite-api/data/static/nifty250_universe.csv` |
| `kite-lab/data/instruments_full.csv` | `kite-api/data/instruments_full.csv` |
| `kite-lab/data/benchmarks/nifty100.csv` | `kite-api/data/benchmarks/nifty100.csv` |

## Directory Structure After Migration

```
kite-api/app/engine/
├── __init__.py
├── data_pipeline/
│   ├── __init__.py
│   ├── symbol_resolver.py
│   ├── price_client.py
│   ├── storage.py
│   └── qa.py
└── scripts/              # Migrated in later phases
    └── __init__.py

kite-api/data/
├── static/
│   ├── nse500_universe.csv
│   ├── nifty100_universe.csv
│   └── nifty250_universe.csv
├── benchmarks/
│   └── nifty100.csv
└── instruments_full.csv
```

## Import Updates

Original (kite-lab):
```python
from data_pipeline.symbol_resolver import find_instrument
from data_pipeline.price_client import PriceClient
```

New (kite-api):
```python
from app.engine.data_pipeline.symbol_resolver import find_instrument
from app.engine.data_pipeline.price_client import PriceClient
```

## __init__.py Files

`app/engine/__init__.py`:
```python
# Engine module - migrated kite-lab scripts
```

`app/engine/data_pipeline/__init__.py`:
```python
from .symbol_resolver import find_instrument
from .price_client import PriceClient
from .storage import save_dataframe, load_dataframe
from .qa import validate_price_data

__all__ = [
    "find_instrument",
    "PriceClient",
    "save_dataframe",
    "load_dataframe",
    "validate_price_data",
]
```

## Migration Script

```bash
#!/bin/bash
# Run from kite-lab root

# Create directories
mkdir -p kite-api/app/engine/data_pipeline
mkdir -p kite-api/data/static
mkdir -p kite-api/data/benchmarks

# Copy data pipeline modules
cp data_pipeline/symbol_resolver.py kite-api/app/engine/data_pipeline/
cp data_pipeline/price_client.py kite-api/app/engine/data_pipeline/
cp data_pipeline/storage.py kite-api/app/engine/data_pipeline/
cp data_pipeline/qa.py kite-api/app/engine/data_pipeline/

# Copy static data
cp data/static/nse500_universe.csv kite-api/data/static/
cp data/static/nifty100_universe.csv kite-api/data/static/
cp data/static/nifty250_universe.csv kite-api/data/static/
cp data/instruments_full.csv kite-api/data/
cp data/benchmarks/nifty100.csv kite-api/data/benchmarks/

# Create __init__.py files
touch kite-api/app/engine/__init__.py
touch kite-api/app/engine/data_pipeline/__init__.py

echo "Migration complete!"
```

## Verification

```python
# Test imports work
cd kite-api
python -c "from app.engine.data_pipeline import find_instrument, PriceClient; print('OK')"
```

## Notes

- `instruments_full.csv` is ~12MB - consider adding to .gitignore and fetching on startup
- Price data (nse500_data/) is NOT migrated - it will be synced separately or fetched on demand
- KiteConnect credentials may not be needed on Railway if data is synced from local

---

*Last updated: February 2026*

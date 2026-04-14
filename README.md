# Trade Bot Pipeline Notes

This repo trains sequence models in `nn.py` and deploys them to `live.mq5` via ONNX. The data export scripts are MQL5 scripts that run inside MT5 and save tick CSVs into `data/<SYMBOL>/ticks.csv`.

## Gold Profiles

Two gold profiles are available:

1. `-gold`
   - Replicates the old LSTM + multihead attention + GAP classifier pattern.
   - Fixed 27-tick bars.
   - Caps the bar count to `14,856` (the old training bar count derived from 2,160,000 ticks at 144 ticks/bar).
   - Uses current pipeline labeling and leakage-safe splits.

2. `-gold-new`
   - CNN + GRU + attention pooling (recency + learned pooling).
   - Fixed 27-tick bars.
   - Uses current pipeline labeling and leakage-safe splits.

Both profiles require USDX and USDJPY context. The input CSV must contain `usdx_bid` and `usdjpy_bid`, and `nn.py` now fails loudly if those columns are missing or empty.

## Data Export

Default export (no auxiliary symbols):
```
python export_data.py --symbol XAUUSD
```

Gold export (includes USDX + USDJPY):
```
python export_data.py --symbol XAUUSD --profile gold
```

Both exports write to `data/<SYMBOL>/ticks.csv`.

## Training Examples

Gold legacy:
```
python nn.py -gold --symbol XAUUSD --data-file data/XAUUSD/ticks.csv
```

Gold new:
```
python nn.py -gold-new --symbol XAUUSD --data-file data/XAUUSD/ticks.csv
```

Notes:
- `-gold` forces fixed-tick bars with `PRIMARY_TICK_DENSITY=27` and caps to 14,856 bars.
- `-gold-new` uses fixed-tick bars but does not cap bars unless you pass `--max-bars`.
- The live EA now computes the base sequence features, the extended sequence feature pack, and USDX/USDJPY return features for the gold profiles.
- `14,856` is the old final bar count derived from `2,160,000` ticks at `144` ticks/bar. Reusing that cap at `27` ticks/bar matches the old bar/window count, but not the old raw tick span.

## Key Files

- `nn.py` — Training pipeline and CLI.
- `sequence_models.py` — Model implementations (including gold legacy and gold new).
- `live.mq5` — Live trading EA.
- `data.mq5` — Standard tick exporter.
- `data_gold.mq5` — Gold exporter with USDX/USDJPY alignment.
- `export_data.py` — Automates MQL5 export.

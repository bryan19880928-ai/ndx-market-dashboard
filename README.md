# NDX Market Dashboard

Public GitHub Pages dashboard for Nasdaq-100, selected technology stocks, VIX, RSI, and US 10Y yield.

## How it works

- `index.html` is a static GitHub Pages app.
- `.github/workflows/update-data.yml` runs every 5 minutes during US market hours and updates `data/market.json`.
- The browser refreshes `data/market.json` every 60 seconds.
- Symbols are configured in `data/symbols.json`.

## Local preview

```bash
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173/`.

## Notes

This is a market monitoring tool, not investment advice.

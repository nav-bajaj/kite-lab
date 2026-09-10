# Sector / industry history for the NSE 500 all-ever universe

Built 2026-09-10 for `tasks/mm_rebuild`. Nothing here is guessed: every
label is copied verbatim from an NSE/NSE Indices constituent file (local
or retrieved from the Wayback Machine) or from the local Zerodha sector
file. Symbols with no such label are listed, not filled.

## Files

| file | what |
|---|---|
| `industry_history.csv` | one row per (symbol, industry, scheme, source); see columns below |
| `missing_symbols.csv` | the 757 all-ever symbols that had no label in the local files before this work |
| `unmatched_symbols.csv` | the 167 symbols still without any label, with a reason code and membership window |
| `raw/` | the 26 archived constituent CSVs exactly as served by web.archive.org (gzip bodies decompressed) |

`industry_history.csv` columns: `symbol`, `company_name` (as printed in
the source), `industry` (verbatim), `source`, `as_of` (latest snapshot date
carrying this symbol+industry), `as_of_first` (earliest such snapshot),
`n_snapshots`, `scheme`, `match` (`symbol` = exact symbol hit;
`name->archived symbol X` = matched on normalised company name from the
membership note to a different historical symbol X). Sources are
`local:<file>` for the repo's `data/static/*.csv` and
`wayback:<index>|<index>` for archived lists. A symbol usually has several
rows, one per scheme and per label change; pick by `scheme`/`as_of` as
needed.

## Coverage

- All-ever NSE 500 symbols in `data/master/membership/nse500.csv`: **1260**
- Labelled before (local `*_universe.csv` + `zerodha_sectors.csv`): **503**; missing: **757**
- Labelled now: **1093** (86.7%); still unlabelled: **167**
- Of the 757 missing, recovered **590** (78%):
  - 549 by exact symbol match in an archived list
  - 41 by normalised company-name match to a different historical symbol (`match` column says which)
- Recovered symbols by scheme available: current 21-sector scheme 181, 2014-2020 macro scheme 384, 2006-2013 fine scheme 324. **149 recovered symbols carry only a fine-scheme label** (they left the index before 2014) and need a mapping to whichever scheme the rebuild uses; 54 carry only a current-scheme label.
- The archived lists also add history (older labels) for 474 of the 503 symbols that were already labelled locally.

### Still unlabelled: 167

- A: member only before first full-500 snapshot (2006-11-08): **81**
- B: member only between full-500 snapshots (2006-2010, 2010-2014, 2015-2018 gaps): **44**
- C: member on a full-500 snapshot date but symbol/name not found (likely traded under an older symbol+name): **21**
- D: entered after latest snapshot (2026-01-07) and local files: **17**
- ambiguous name match: FLUOROCHEM, GUJFLUORO: **1**
- ambiguous name match: FRETAIL, FRL: **1**
- ambiguous name match: GUJGASLTD, GUJRATGAS: **1**
- ambiguous name match: MAX, MAXINDIA: **1**

Reason A is structurally unreachable from index constituent files (the
earliest archived list is 2006-11-08). Reason B are short-lived members
between full-500 snapshots; only partial lists (CNX Midcap 2011, CNX 100
2012/2013) exist for 2011-2013 and nothing for 2016-2017. Reason C are
mostly rename chains where the membership note carries only the latest
company name (e.g. `ACCELYA` was Kale Consultants, `BBOX` was Tata
Telecom/Avaya GlobalConnect) so neither symbol nor name matches the old
list; an ISIN-keyed match would resolve most of these but the membership
file has no ISIN column. Reason D are the 2026 entrants that post-date
both the local files and the last archived list.

Ambiguous name matches deliberately left out (two archived symbols share
the normalised name; both are the same corporate lineage but a human
should pick):
- `FEL` (Future Retail Ltd.): archived lists carry both `FRETAIL` and `FRL` under that normalised name
- `GFLLIMITED` (Gujarat Fluorochemicals Ltd.): archived lists carry both `FLUOROCHEM` and `GUJFLUORO` under that normalised name
- `GUJENERGY` (Gujarat Gas Ltd.): archived lists carry both `GUJGASLTD` and `GUJRATGAS` under that normalised name
- `MAXIND` (Max India Ltd.): archived lists carry both `MAX` and `MAXINDIA` under that normalised name

## Sources

### Worked (Wayback Machine, `http://web.archive.org/web/<ts>id_/https://<url>`)

| snapshot | as_of | rows | scheme |
|---|---|---|---|
| cnx100 | 2006-11-06 | 100 | fine (~72 industries) |
| cnx500 | 2006-11-08 | 500 | fine (~72 industries) |
| cnxmidcap | 2006-11-08 | 100 | fine (~72 industries) |
| cnx500 | 2010-01-02 | 500 | fine (~72 industries) |
| cnxmidcap | 2010-01-02 | 100 | fine (~72 industries) |
| cnxmidcap | 2011-10-20 | 100 | fine (~72 industries) |
| cnx100 | 2012-01-20 | 100 | fine (~72 industries) |
| cnx100 | 2013-01-19 | 100 | fine (~72 industries) |
| cnx500 | 2014-01-22 | 500 | macro v1 (18-19, UPPERCASE) |
| cnx500 | 2014-07-09 | 500 | macro v1 (18-19, UPPERCASE) |
| cnx500 | 2015-03-25 | 500 | macro v1 (18-19, UPPERCASE) |
| niftysmallcap250 | 2018-03-09 | 250 | macro v1 (18-19, UPPERCASE) |
| nifty500 | 2018-10-04 | 501 | macro v1 (18-19, UPPERCASE) |
| nifty500 | 2019-02-01 | 501 | macro v1 (18-19, UPPERCASE) |
| niftymidcap150 | 2019-02-01 | 150 | macro v1 (18-19, UPPERCASE) |
| niftysmallcap250 | 2019-02-02 | 250 | macro v1 (18-19, UPPERCASE) |
| nifty100 | 2019-05-17 | 101 | macro v1 (18-19, UPPERCASE) |
| nifty500 | 2020-07-25 | 501 | macro v1 (18-19, UPPERCASE) |
| nifty500 | 2022-05-04 | 501 | macro v2 (21, current) |
| nifty500 | 2022-10-09 | 501 | macro v2 (21, current) |
| nifty500 | 2023-04-04 | 501 | macro v2 (21, current) |
| niftymidcap150 | 2023-08-08 | 150 | macro v2 (21, current) |
| nifty500 | 2024-02-07 | 501 | macro v2 (21, current) |
| niftysmallcap250 | 2024-07-08 | 251 | macro v2 (21, current) |
| nifty500 | 2025-06-16 | 503 | macro v2 (21, current) |
| nifty500 | 2026-01-07 | 501 | macro v2 (21, current) |

URL patterns by index: 
- `cnx500`: nseindia.com/content/indices/ind_cnx500list.csv
- `nifty500`: niftyindices.com/IndexConstituent/ind_nifty500list.csv (2018-19, 2024-26), www1.nseindia.com/content/indices/ind_nifty500list.csv (2020), archives.nseindia.com/content/indices/ind_nifty500list.csv (2022-23)
- `cnxmidcap`: nseindia.com/content/indices/ind_cnxmidcaplist.csv
- `cnx100`: nseindia.com/content/indices/ind_cnx100list.csv
- `niftymidcap150`: niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv
- `niftysmallcap250`: niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv
- `nifty100`: nseindia.com/content/indices/ind_nifty100list.csv

Example: `http://web.archive.org/web/20100102131654id_/https://nseindia.com/content/indices/ind_cnx500list.csv`.
Snapshot inventory came from the CDX API
(`http://web.archive.org/cdx/search/cdx?url=<url>&filter=statuscode:200`).
Total Wayback content requests: 45 (26 succeeded; a burst of connection
failures mid-run was retried once after a pause; CNX 100 2010-01-02 was
dropped as redundant with CNX 500 on the same day). The 2006 and 2010
CNX 500 files have two title lines before the header; the 2022/2023
`archives.nseindia.com` captures are gzip bodies.

### Did not work / not available

- `archives.nseindia.com/content/indices/ind_cnx500list.csv`: no captures.
- `nseindia.com/content/indices/ind_cnxsmallcaplist.csv`, `ind_niftymidcap150list.csv`, `ind_niftysmallcap250list.csv`, `ind_niftymidcap100list.csv`, `ind_niftysmallcap100list.csv`, `ind_niftytotalmarket_list.csv`: no captures on nseindia.com.
- `niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv`, `ind_niftytotalmarket_list.csv`: no captures.
- Full-500 list gaps in the archive: 2007-2009, 2011-2013, 2016-2017, 2021.
- Not tried (budget): NSE press-release PDFs, BSE classification, Zerodha/other vendor archives.

## Classification schemes (three, not two)

1. **Fine scheme, 2006-2013** (`nse_fine_2006_2011`): ~72 uppercase industries in the CNX 500 (e.g. `COMPUTERS - SOFTWARE`, `FINANCE - HOUSING`, `AUTOMOBILES - 2 AND 3 WHEELERS`, `CASTINGS/FORGINGS`). Still in use in the CNX 100 (2012, 2013) and CNX Midcap (2011) lists, so the switch happened between 2013-01 and 2014-01, not around 2021.
2. **Macro v1, 2014-2020** (`nse_macro_2014_2020`): 18 uppercase sectors (`AUTOMOBILE`, `CEMENT & CEMENT PRODUCTS`, `CONSUMER GOODS`, `ENERGY`, `FERTILISERS & PESTICIDES`, `IT`, `PHARMA`, `HEALTHCARE SERVICES`, `PAPER`, `SERVICES`, ...). The 2020-07 file already splits `ENERGY` into `OIL & GAS` and `POWER` (19 labels), which is why ADANIPOWER/BPCL/GAIL etc. show two labels inside this scheme.
3. **Macro v2, 2022-present** (`nse_macro_2022_current`): 21 title-case sectors matching the local `*_universe.csv` files (`Automobile and Auto Components`, `Capital Goods`, `Construction Materials`, `Fast Moving Consumer Goods`, `Oil Gas & Consumable Fuels`, `Forest Materials`, ...). The nearest snapshots bracketing the change are 2020-07-25 (v1) and 2022-05-04 (v2).

The schemes are not nested: v1 `CONSUMER GOODS` splits into v2 `Fast Moving Consumer Goods` / `Consumer Durables` / `Consumer Services`; v1 `INDUSTRIAL MANUFACTURING` mostly becomes `Capital Goods`; v1 `PHARMA` + `HEALTHCARE SERVICES` merge into `Healthcare`; v1 `CEMENT & CEMENT PRODUCTS` becomes `Construction Materials`; v1 `SERVICES` scatters across `Services`, `Consumer Services`, `Diversified`. No cross-scheme mapping is applied in this file.

Within-scheme label changes (genuine reclassifications, kept as separate rows): 61 symbol-scheme pairs, e.g. ABREL Forest Materials/Realty; ADANIGREEN ENERGY/POWER; ADANIPOWER ENERGY/POWER; BALMLAWRIE INDUSTRIAL MANUFACTURING/SERVICES; BHARATFORG Automobile and Auto Components/Capital Goods; BOMDYEING CONSTRUCTION/TEXTILES.

Symbol-match rows where the archived company name differs from the membership note are all renames of the same company (BHARATFIN/SKS Microfinance, DCBBANK/Development Credit Bank, RBA/Burger King, RNAVAL/Pipavav Defence, EPL/Essel Propack, DHANI/Indiabulls Ventures, EPIGRAL/Meghmani Finechem); no case of a symbol reused by an unrelated company was found.

Zerodha sector rows (`scheme=zerodha`) are included only because the brief counted them as local coverage; they add 2 symbols not in the NSE files and use Zerodha's own labels.

# QA report, master store

- calendar: 2519 files checked, 0 with non-midnight, duplicate or off-calendar dates
- bad prints: 9700 one-day spike-and-revert rows with no corporate action nearby; Kite shows the same move on 2403 (a real move, not a print), disagrees on 73 (a print on one side), no Kite on 7224
- stale tails: 0 files end >20 sessions before 2026-09-09 without a delisted_on flag
- identity overlaps: 0
- coverage (membership vs price files, min % per year):

index  nifty100  nifty250  nifty50  nse500
yr                                        
2006       99.0      98.0    100.0    98.0
2007       99.0      98.0     98.0    98.4
2008       99.0      98.0    100.0    98.6
2009      100.0      98.8    100.0    98.2
2010      100.0      99.6    100.0    99.4
2011       99.0      98.8     98.0    98.8
2012       99.0      98.4     98.0    98.8
2013      100.0      99.2    100.0    98.4
2014      100.0      99.6    100.0    99.2
2015      100.0     100.0    100.0    99.2
2016      101.0     100.0    102.0    98.8
2017      101.0     100.0    100.0    98.6
2018      101.0     100.0    100.0    99.4
2019      101.0     100.4    100.0    99.6
2020      100.0     100.0    100.0   100.0
2021      100.0     100.0    100.0   100.2
2022      100.0     100.0    100.0   100.2
2023      100.0     100.0    100.0   100.2
2024      100.0     100.0    100.0   100.0
2025      100.0     100.0    100.0    99.8
2026      100.0     100.0      NaN   100.0

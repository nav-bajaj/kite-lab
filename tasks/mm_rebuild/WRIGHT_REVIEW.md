# Wright Research — Alpha Prime and Momentum: what the sources state, what can be inferred, what we can test

Written 2026-09-10 against RESULTS.md §7, §8, §8b. Purpose: our NSE 500
momentum book captures the upside (up-capture 1.09 vs MidSmall 400) but gives
back 1.11-1.37 of the index's down months; Wright Momentum gives back 0.90
with up-capture 1.11 and made 91% in calendar 2021 against the index's 51%.
This memo collects everything Wright's own material says about how the two
products are built, so the difference can be tested rather than guessed at.

Sources read (all on 2026-09-10):

| Tag | Source |
|---|---|
| A-PDF | `/Users/navdeep/Downloads/alpha_wright.pdf`, 5 pages (Alpha Prime factsheet; grid to Aug-2026) |
| M-PDF | `/Users/navdeep/Downloads/momentum_wright.pdf`, 4 pages (Momentum factsheet; grid to Aug-2026) |
| A-WEB | https://www.wrightresearch.in/portfolio/alpha/ (rendered in Playwright; tabs Overview / Why should you invest? / How is the portfolio made? / Risk Management / Key Information; FAQ accordion; "All About" long text behind Show More) |
| M-WEB | https://www.wrightresearch.in/portfolio/momentum/ (same structure) |
| A-BLOG | https://www.wrightresearch.in/blog/alpha-prime-new-concentrated-momentum-portfolio/ (Siddharth Singh Bhaisora, published 09 Jul 2023) |
| M-GUIDE | https://www.wrightresearch.in/blog/complete-guide-to-momentum-investing-and-the-wright-momentum-portfolio/ (Bhaisora, published 05 Jul 2023, updated 09 Sep 2026) |
| M-LAUNCH | https://www.wrightresearch.in/blog/wright-momentum/ (Sonam Srivastava, 06 Dec 2020 — the launch post) |
| REGIME | https://www.wrightresearch.in/blog/regimemodeling/ (Srivastava, 30 Sep 2021) |
| RISK | https://www.wrightresearch.in/blog/risk-management/ (Srivastava, 01 Oct 2021, updated 07 Sep 2023) |
| PHIL | https://www.wrightresearch.in/investment-philosophy/ |
| HELP | https://help.wrightresearch.in/support/solutions/articles/82000900520-what-is-the-rebalancing-frequency- and .../82000524971-how-is-the-fee-charged-for-aum-based-portfolios- |

Did not load: the two SSRN papers the philosophy page links as its regime
and momentum references (abstract_id 3711487 and 3144169) — Cloudflare
"Content Blocked" on fetch. The "Download Report" links on both product
pages require login. The "Login to unlock all metrices" panel and the
"5 year" returns dropdown are behind login. Playwright ran the product
pages; the rest were fetched as server-rendered HTML.

Quotations are verbatim, including Wright's spelling and grammar.

---

## 1. What they state

### 1a. Alpha Prime Momentum Model

| Item | Stated | Source |
|---|---|---|
| Product framing | "Concentrated Trend: High risk, high momentum strategy aiming to generate alpha return with a few stocks" | A-PDF p1; A-WEB |
| Investment objective | "Alpha Prime is defined as the strong predictive power of past returns in influencing future returns. This is a high risk equity strategy to participate in high momentum stocks with a check for volatility. This strategy is specifically build to take advantage of the bull market." | A-PDF p1 |
| Investment mechanism | "Wright Alpha Prime is a data-driven quantitative trend following strategy based on multiple momentum indicators combined using position sizing techniques and market regime modelling using machine learning models. This portfolio is expected to generate consistent high returns over time. The underlying equity themes consist of selecting high quality stocks with high momentum and low volatility." | A-PDF p1 |
| Universe | "A concentrated, 10-stock portfolio hand-picked from the top 500 corporations." / "Careful & precise selection of 10 standout stocks from the top 500 universe" / "Flexicap Strategy: Expands the universe to capturing alpha stocks across high-quality large cap, mid cap and smallcap stocks" / "Wider universe, including high quality smallcap stocks" | A-WEB "Why should you invest?" tab; A-WEB "How is the portfolio made?" tab; A-WEB All About; A-BLOG Key Highlights |
| Number of holdings | "10 specially chosen stocks"; "a curated set of 10 high-potential stocks"; "typically comprising 10 high-potential stocks". The page's generic FAQ accordion contradicts this: "Each portfolio is diversified to and contains 18-22 stocks in it." | A-BLOG; A-WEB tabs and All About; A-WEB FAQ "How many stocks are there in portfolio?" |
| Selection method and factors | "multiple momentum indicators" (A-PDF); "stocks displaying strong earnings momentum and trending opportunities" (A-WEB); "We select 10 standout stocks from the top 500 companies based on a comprehensive evaluation of the company's fundamentals, industry position, and growth potential." (A-BLOG); "high quality stocks with high momentum and low volatility" (A-PDF). No lookback, no formula, no ranking rule stated. | A-PDF p1; A-WEB; A-BLOG |
| Volatility screen | "a check for volatility"; "low volatility". Nothing more specific. | A-PDF p1 |
| Quality / liquidity filters | "high quality stocks" (A-PDF); "high-quality large cap, mid cap and smallcap stocks" (A-WEB). No liquidity rule stated for Alpha specifically. | A-PDF p1; A-WEB All About |
| Position sizing | "position sizing techniques" (A-PDF); "Utilize risk optimization for balanced risk-reward allocations" (A-WEB tab); "Diversification: Even though our portfolio is concentrated, we practice diversification among our chosen 10 stocks to spread the risk - Portfolio remains well-rounded and not overly reliant on any single stock or sector." (A-BLOG). No weighting rule stated. | A-PDF p1; A-WEB; A-BLOG |
| Rebalancing frequency | Factsheet and page header: "Rebalancing Frequency Weekly". Page long-text and blog: "frequent bi-weekly rebalancing"; "a high portfolio churn requiring bi-weekly rebalancing". "Weekly portfolio rebalancing & high portfolio churn to seize fresh trending & emerging opportunities." | A-PDF p1; A-WEB header; A-WEB All About; A-BLOG; A-WEB "Why should you invest?" tab |
| Rebalancing rules | "Through frequent portfolio reviews & weekly rebalancing, we concentrate on portfolio optimization and risk mitigation." Live rebalance note on page (Next Rebalance 2026-09-07): "A lot happening in the market! We are reducing exposure to Adani group, cutting some banking exposure and adding Metals and IT." | A-WEB Risk Management tab; A-WEB Rebalancing block |
| Market-regime model | "market regime modelling using machine learning models" (A-PDF); "Leverage AI technology for advanced market forecasting and regime modeling." and "Systematic deallocation in risky markets to mitigate risk exposure" (A-WEB tab); "We use predictive machine learning models and AI technology, combining fast-moving macroeconomic variables and technical indicators over the index, to predict future market events. This highly accurate predictive model enables us to adapt our participation in various strategies dynamically." and "Systematic De-Allocation: In high-risk market scenarios, we systematically de-allocate our investments to mitigate risk exposure." (A-BLOG). "Wright Alpha is actively managed investments by using quantitative models & AI to forecast market events." (A-WEB Risk tab) | A-PDF p1; A-WEB; A-BLOG |
| Cash or hedge in bear | "de-allocate" only. Whether to cash, bonds or partial exposure is not stated for Alpha. | A-BLOG |
| Sector / market-cap caps | "not overly reliant on any single stock or sector" — no numbers. | A-BLOG |
| Stated performance | Inception 25.4% (BSE 500 11.6); MTD 3.5 / 1M -2.9 / 3M 3.2 / 6M 0.2 / 1Y 6.0 / 2Y 2.9 / 3Y 18.4 / YTD 3.5 (BSE 500: -0.6 / -0.2 / 3.4 / 0.8 / 3.8 / -1.4 / 10.7 / -2.2). Page: "3Y CAGR 25.6 %"; "₹1 Lac invested for 3 years could have been Portfolio 2,04,530 BSE 500 1,39,350". Blog (Jul 2023): "Alpha Prime has only been live for less than a month where the return has been 9.53%. As per the backtests the portfolio has a long term (10 year) CAGR of 35%+." | A-PDF p1; A-WEB header; A-BLOG |
| "10 Years Expected Performance" table | Alpha vs BSE 500: Annualized Returns 25.4 / 11.6; Annualized Risk 25.0 / 13.9; Sharpe Ratio 101.6 / 83.3; Max Drawdown -28.2 / -19.3; Corr 71.0 / -. | A-PDF p1 |
| Drawdown | -28.2 (table above). | A-PDF p1 |
| Turnover | "high portfolio churn" — no number. | A-WEB; A-BLOG |
| Fees | Page: "Subscription Starting ₹833/month"; "6 Month Rs. 9375 ₹6250; 12 Month Rs. 15000 ₹10000". FAQ: "Except for subscription you will be charged brokerage fee as per your broker." | A-WEB |
| Inception date | Not stated as a date. Grid's first non-zero month is Jun-2023 (4.30); chart axis starts "Jul 2023"; blog dated 09 Jul 2023 says "live for less than a month". | A-PDF p1-2; A-BLOG |
| Minimum investment | Factsheet "Rs. 33069"; page "₹33695" (moves with prices — M-GUIDE explains the minimum is the sum of one share of each constituent). | A-PDF p1; A-WEB; M-GUIDE |
| Backtest / cost disclosure | Chart note: "Live performance includes rebalances. It is a tool to communicate factual return information and should not be seen as advertisement or promotion." Disclosure: "Charts and performance numbers might include backtested/simulated results calculated via a standard methodology and do not include the impact of transaction fee and other related costs." and "Back-tested results are not adjusted to reflect the reinvestment of dividends and other income and, except where otherwise indicated, do not include the effect of back-tested transaction costs." Blog: "But we have to understand that backtest results do not represent real data." | A-PDF p2, p3-4; A-BLOG |
| Key Information tab | "PB Ratio 7.4; PE Ratio 49.0" (chart blurred behind login). | A-WEB |

### 1b. Wright Momentum Model

| Item | Stated | Source |
|---|---|---|
| Product framing | "Momentum investing: Aiming to capitalize on market trends for potential growth." | M-PDF p1; M-WEB |
| Investment objective | "Momentum is defined as the strong predictive power of past returns in influencing future returns. This is a high risk equity strategy to participate in high momentum stocks with a check for volatility. This strategy is specifically build to take advantage of the bull market." (identical wording to Alpha) | M-PDF p1 |
| Investment mechanism | "Wright Momentum is a data-driven quantitative trend following strategy based on multiple momentum indicators combined using position sizing techniques and market regime modelling using machine learning models. ... The underlying equity themes consist of selecting high quality stocks with high momentum and low volatility." (identical to Alpha) | M-PDF p1 |
| Universe | "A diverse, 20-25 stock portfolio, handpicked from the top 300 universe." / "Selection of 20-25 stocks from the top 300 universe, ensuring diversity." / "meticulously selecting 20-25 of the best performing momentum stocks from the top 300 by market capitalization" / "All NSE-listed stocks meeting minimum criteria in daily traded volume and company market capitalization. This translates to nearly 90% of the total market cap trading in India." / "It focuses on stocks from the NSE that meet specific criteria for daily traded volume and market capitalization, ensuring liquidity and stability." | M-WEB tabs; M-WEB All About; M-GUIDE "What is the universe of stocks considered?" |
| Number of holdings | "20-25 stock portfolio". Generic FAQ on the same page: "contains 18-22 stocks". | M-WEB; M-WEB FAQ |
| Selection method and factors | Launch post: "There are various ways is which one can construct a momentum portfolio. The most popular being just looking at the past one year returns and picking the top stocks. One can also adjust the previous returns with the risk. There are certain more nuanced technical indicators like Bollinger Band breakouts, Relative Strength Index, etc that are also used. Our methodology is a combination of a few of the momentum factors along with a big focus on keeping the risks low." Guide: "concentrating on those with the highest momentum, based on earnings momentum and price trends"; "a dual focus on earnings momentum and price momentum. Our trend following strategy identifies stocks not just with rising prices but also with solid, improving earnings". Page: "High-quality stocks with strong momentum and low volatility." | M-LAUNCH Methodology; M-GUIDE / M-WEB All About; M-WEB "Why should you invest?" |
| Lookbacks | Not stated. (Launch post lists "past one year returns" as "the most popular" approach, not as its own rule.) | M-LAUNCH |
| Volatility screen | "with a check for volatility"; "low volatility"; "a big focus on keeping the risks low". No rule. | M-PDF p1; M-WEB; M-LAUNCH |
| Quality / liquidity filters | "High-quality stocks"; "minimum criteria in daily traded volume and company market capitalization". No thresholds. | M-WEB; M-GUIDE |
| Position sizing | Launch post (Dec 2020): "We try to size our positions such that no single stock gets more than 10% allocation. We put a limit on sector and industry allocations as well to promote diversification. The position sizing is done using the mean variance optimisation methodology." Guide (2023, updated 2026): "Our proprietary AI & quantitative models assign optimal weights based on a sophisticated multi factor stock selection model. Adopting a weight scoring approach, stocks are weighted according to the rank assigned by the AI & Quantitative models. This rank is reviewed & analysed in depth by our Investment Team & the Investment Advisor approves the stocks into the portfolio." Page: "Utilize risk optimization for balanced risk-reward allocations." | M-LAUNCH Risk Management; M-GUIDE "How are stocks weighted?"; M-WEB |
| Rebalancing frequency | "Rebalancing Frequency Monthly" (factsheet, page, help centre: "Momentum: Monthly"). "Monthly portfolio rebalancing to maintain low turnover." "Historically, the majority of portfolio rebalances have happened on a monthly basis, however this can vary depending on market conditions." "Wright Momentum Portfolio is optimized to be rebalanced once every 1 month." | M-PDF p1; M-WEB; HELP; M-GUIDE |
| Review cadence and exceptional rebalances | "Wright Momentum portfolio is assessed weekly by the Investment Advisor and Investment Team. ... keeping an eye on significant market aspects such as volatility, momentum, and other factors, as well as unexpected news or macroeconomic shifts." "In cases of adverse market conditions or negative developments specific to a stock, regular portfolio reviews allow the Investment Advisor and Investment Team to act quickly ... Rebalances in such exceptional scenarios are immediately implemented". "Portfolio review is different from rebalancing a portfolio." | M-GUIDE "How do you manage risk?" and rebalancing FAQ |
| Handling of winners | "Any stock that is retained in the portfolio means the stock has potential to grow. ... let's say a stock ... is up 50%+. It continues to be in the portfolio, this means as a subscriber it should be bought per the constituent weight assigned in the portfolio". Holding periods cited: Tata Elxsi 06 Dec 2020 to 02 Oct 2022 (+315.13%); Tata Motors 06 Dec 2020 to 31 May 2023 (+197.57%); Deepak Nitrite 06 Dec 2020 to 13 Feb 2022 (+130.06%); Tata Power 28 Mar 2021 to 31 Oct 2022 (+119.88%); Fluorochem 01 Aug 2021 to 31 Jul 2022 (+92.70%); Bank of Baroda 23 Jan 2022 to 31 May 2023 (+88.34%); RVNL 02 Apr 2023 to 31 May 2023 (+83.73%); ITC 15 May 2022 to 31 May 2023 (+80.40%). | M-GUIDE |
| Market-regime model | Guide: "Regime Modeling based Dynamic Adaptiveness - Our philosophy fundamentally incorporates a regime model that leverages Artificial Intelligence to project the market's trajectory over the next month." "Asset Allocation or Diversification - In response to market volatility, we adjust our asset allocation, often opting for safer alternatives like bonds and gold ETFs." "Deallocating in volatile times - We have a policy of reallocating to cash in unstable market conditions to protect our investments." REGIME: "We use a predictive machine learning model that uses fast-moving macroeconomic variables in combination with technical indicators over the index to predict future risk in the market. ... we dynamically adapt our participation in various strategies based on this model." "When the model predicts a high-risk number, the market is in a risky regime. Conversely, the market is trending when the model predicts a low-risk number." RISK: "The core of our ethos contains a regime model that uses Artificial Intelligence to forecast the next month in the market. Is it bullish or bearing?" "We also have a deallocation policy that helps us switch to cash when the markets are precarious." "The Momentum stocks are high risk stocks. They crash when markets are crashing. But with our strong risk management we deallocate and adjust dynamically to minimize losses." | M-GUIDE; REGIME; RISK |
| Regime model — cited episodes | "2020 crash - our model was in risk territory even before the 2020 crash, and our allocation was in safer assets which we further increased as the crash escalated. This made our Balanced multi-factor strategy have a much lower drawdown than the market." "2021 October - our model identified a clear shift in regime in October 2020, which led to us deallocating away from equities then. This was a wise decision as the market volatility lasted for more than a year." (The heading says October 2021, the sentence says October 2020; the post is dated 30 Sep 2021 with the chart referring to "2021 ... 2022", so the dates in this post are internally inconsistent.) | REGIME |
| Regime model — threshold example | "An observed variable crossing a threshold triggers a regime shift. For example, the prices below the 200-day moving average trigger a 'bearish regime' or a downtrend." (given as a category of model, contrasted with their own predictive model) | REGIME |
| Sector / market-cap caps | "We put a limit on sector and industry allocations" (no numbers); "limiting exposure to certain sectors or industries can help lower risk". | M-LAUNCH; M-GUIDE |
| Stated performance | Inception 31.0% (BSE 500 15.9); MTD 8.3 / 1M -3.7 / 3M 0.1 / 6M 6.9 / 1Y -0.6 / 2Y 0.9 / 3Y 17.0 / YTD 8.9 (BSE 500 -0.6 / -0.2 / 3.4 / 0.8 / 3.8 / -1.4 / 10.7 / -2.2). Page: "6Y CAGR 32.1 %"; "₹1 Lac invested for 5 years could have been Portfolio 2,65,995 BSE 500 1,49,107". | M-PDF p1; M-WEB |
| "10 Years Expected Performance" table | Momentum vs BSE 500: Annualized Returns 31.0 / 15.9; Annualized Risk 21.9 / 14.5; Sharpe Ratio 141.7 / 109.6; Max Drawdown -25.6 / -19.3; Corr 80.8 / -. | M-PDF p1 |
| Drawdown | -25.6 (table above). Guide: "The maximum drawdown for the Momentum strategy is less than the Multicap's max drawdown." | M-PDF p1; M-GUIDE |
| Turnover | "low turnover"; "Momentum is typically a high turnover strategy that will require frequent rebalances, however Wright Momentum Portfolio is optimized to be rebalanced once every 1 month." "Wright Momentum Portfolio typically holds stocks for less than 1 year, but a few top-performers can also be held for greater than 1 year." No number. | M-WEB; M-GUIDE |
| Fees | Page: "Subscription Starting ₹600/month"; "6 Month Rs. 6750 ₹4500; 12 Month Rs. 10800 ₹7200". Guide (2023): "3 Month ₹3,000 / ₹2,000; 6 Month ₹5,400 / ₹3,600". Other costs: "anywhere from 0.5% to 1% on average for investors" (brokerage, STT 0.1% each side, DP charges). Help centre, AUM-fee products: "The 1.5% annual fee ... 0.125% every month". | M-WEB; M-GUIDE; HELP |
| Inception date | "launched in 2020" (guide). Launch post dated 06 Dec 2020: "Wright is launching a Momentum basket as a free for all research product for the time being." Factsheet grid starts Oct-2020 (1.70) and chart axis starts "Sep 2021". Page says "6Y CAGR". | M-GUIDE; M-LAUNCH; M-PDF p1-2 |
| Minimum investment | Factsheet "Rs. 59108"; page "₹58883". | M-PDF p1; M-WEB |
| Benchmark | Factsheet: BSE 500. Guide: "its benchmark, Multicap Index"; "benchmarked against relevant multicap indexes". | M-PDF; M-GUIDE |
| Backtest / cost disclosure | Same chart note and disclosure text as Alpha (p1, p3). Launch post: "Here is the historical performance of the portfolio based on the backtest" (chart image, not transcribable). | M-PDF p1, p3; M-LAUNCH |
| Key Information tab | "PB Ratio 5.3; PE Ratio 37.3". | M-WEB |
| Customisation | "Adjust Stock Weightages ... the flexibility to modify the weightages"; "Investors have the leeway to slightly tweak sector exposures". | M-WEB All About |

### 1c. Firm-level statements that apply to both

- PHIL: "We choose the right asset mix for your risk profile in all the market conditions. We add incremental alpha using dynamic allocation to equity factor models." "Regime Modeling: Markets do not stay the same. Our regime models forecast market cycles." "Momentum Investing: Momentum is the strongest factor in India and an important part of our philosophy." "Risk Modeling: Risk Management is at the core of our investing. We have a multi-level approach." "Reinforcement Learning for Portfolio Allocation: Our proprietary sysstem solve complex financial problems without a defined model."
- RISK, three named tools: "Regime Modeling based Dynamic Adaptiveness", "Asset Allocation or Diversification", "Deallocation in extreme events".
- M-GUIDE, generic momentum-risk text (not stated as their rule): "Using a system with a profit target and a stop loss can help avoid stocks prone to shocking downturns." A-BLOG likewise lists "setting stop-loss orders or diversifying within the momentum stocks" as generic ingredients.
- Factsheets: "Unless otherwise stated, the percentage returns displayed on the website or any other marketing materials are Absolute Returns." Both factsheets (A-PDF p3, M-PDF p3).
- Team: Sonam Srivastava, "Founder, Portfolio Manager ... HSBC, Edelweiss, Qplum ... IIT Kanpur graduate, Masters in Financial Engineering Worldquant University"; Dr Miquel Alonso, "Advisor, Machine Learning" (A-PDF p3, M-PDF p2). Launch post: "In a paper I co-authored at qplum on Momentum in the Indian Equity Markets: Positive Convexity and Positive Alpha we did a deep dive into the factor." (SSRN links did not load.)

---

## 2. Alpha factsheet (A-PDF) in detail

Five pages. Page 1: header, objective, mechanism, minimum investment, rebalancing frequency, trailing-return table, "10 Years Expected Performance" table. Page 2: equity-curve chart (axis Jul 2023 to Aug 2026, single line "Alpha Prime Momentum Model", no benchmark line, no y-axis values) and the month-on-month grid. Page 3: team and accolades. Pages 3-4: disclosure. Page 5: footer.

Header: "Alpha Prime Momentum Model — Concentrated Trend: High risk, high momentum strategy aiming to generate alpha return with a few stocks".

Investment Mechanism box: "Minimum Investment Rs. 33069. Rebalancing Frequency Weekly."

Trailing returns (p1):

| | Inception | MTD | 1M | 3M | 6M | 1Y | 2Y | 3Y | YTD |
|---|---|---|---|---|---|---|---|---|---|
| Alpha | 25.4 | 3.5 | -2.9 | 3.2 | 0.2 | 6.0 | 2.9 | 18.4 | 3.5 |
| BSE 500 | 11.6 | -0.6 | -0.2 | 3.4 | 0.8 | 3.8 | -1.4 | 10.7 | -2.2 |

"10 Years Expected Performance" (p1):

| | Alpha | BSE 500 |
|---|---|---|
| Annualized Returns | 25.4 | 11.6 |
| Annualized Risk | 25.0 | 13.9 |
| Sharpe Ratio | 101.6 | 83.3 |
| Max Drawdown | -28.2 | -19.3 |
| Corr | 71.0 | - |

Note: the "Annualized Returns" in this table equal the "Inception" column of the trailing table for both products (25.4 and 11.6 here; 31.0 and 15.9 on M-PDF), so despite the label "10 Years Expected" the table appears to be since-inception live statistics. Sharpe is printed as a percentage-style number (101.6 = 1.016). The factsheet does not say which it is.

Month-on-month performance (p2), percent; zeros are pre-inception months; Sep-Dec 2026 are shaded as not-yet-available:

| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 4.30 | 14.40 | 9.10 | -0.30 | 1.90 | 14.80 | 1.20 |
| 2024 | 14.40 | -5.40 | -2.30 | 3.70 | -1.00 | 7.00 | 4.80 | 10.80 | 3.60 | -2.90 | 1.80 | 4.40 |
| 2025 | -18.60 | -8.40 | 7.60 | 1.40 | 3.20 | 0.60 | -0.10 | -0.60 | -3.50 | 10.30 | 2.70 | -2.40 |
| 2026 | -0.20 | -6.50 | -3.30 | 7.40 | 4.00 | 2.10 | -2.90 | 3.50 | | | | |

Chart note (p2): "Note: Live performance includes rebalances. It is a tool to communicate factual return information and should not be seen as advertisement or promotion."

Holdings, sector mix, weights, turnover, number of names: not printed anywhere in the factsheet. The only portfolio-composition information in any Alpha source is the page's PB 7.4 / PE 49.0 and the 2026-09-07 rebalance note ("reducing exposure to Adani group, cutting some banking exposure and adding Metals and IT").

Arithmetic on the grid (mine, not Wright's; compounding the printed months; MidSmall 400 is our synthetic series from `tasks/om25_rebuild/runs/midsmall400_synthetic.csv`, same `capture` definition as RESULTS §7/§8):

| | Alpha Jul-23 to Aug-26 | Momentum, same 39 months | MidSmall 400, same months |
|---|---|---|---|
| Compound CAGR | 24.7% | 24.5% | 19.5% |
| Annualised monthly vol | 22.6% | 20.9% | 18.8% |
| Max drawdown (month-end) | -25.4% | -21.7% | -22.0% |
| Up-capture / down-capture | 1.00 / 0.79 | 1.06 / 0.94 | — |
| Beats index in up / down months | 42% / 67% | 54% / 50% | — |
| Calendar 2023 (from Jul) / 2024 / 2025 / 2026 YTD | 53.6 / 44.2 / -10.5 / 3.4 | 43.1 / 34.1 / -2.4 / 8.9 | 37.4 / 24.7 / 1.2 / 3.0 |

Grid CAGR 24.7% against the factsheet's 25.4% inception figure: consistent to rounding and to the exact inception day inside June 2023. Alpha's worst stretch is Jan-Feb 2025: -25.4% over two months against the index's -18.2% and Momentum's -18.4%; that is the -28.2 max drawdown in the table.

For reference, Momentum's full grid over Oct-2020 to Aug-2026 reproduces the §7 figures exactly: CAGR 31.2%, up 1.11 / down 0.90, calendar 2021 91.4% vs 51.3%.

Index-down months in the overlap window, percent (Alpha / Momentum / MidSmall 400): Oct-23 1.9 / -2.1 / -3.1; Feb-24 -5.4 / -4.6 / -0.4; Mar-24 -2.3 / -0.1 / -1.8; Oct-24 -2.9 / 1.6 / -5.4; Jan-25 -18.6 / -10.3 / -7.8; Feb-25 -8.4 / -9.0 / -11.3; Jul-25 -0.1 / 0.3 / -3.1; Aug-25 -0.6 / -5.6 / -3.2; Nov-25 2.7 / -0.4 / -0.2; Dec-25 -2.4 / -1.5 / -0.4; Jan-26 -0.2 / -5.9 / -4.2; Mar-26 -3.3 / -10.6 / -10.7. Monthly correlation Alpha-index 0.69, Momentum-index 0.88, Alpha-Momentum 0.74.

---

## 3. What can be inferred, and how confidently

Each item below is an inference, not a statement by Wright.

1. **The two products share one engine and differ in count, universe and cadence.** High confidence. The objective and mechanism paragraphs on the two factsheets are word-for-word identical; the "How is the portfolio made?" tabs differ only in "10 standout stocks from the top 500" vs "20-25 stocks from the top 300" and in the "Systematic deallocation" wording. Rebalance is weekly (Alpha) vs monthly with weekly review (Momentum).

2. **The regime device is a market-level exposure switch, not a stock-level one, and it is forecast-based with a one-month horizon.** High confidence that it is market-level and monthly-horizon: "regime model that leverages Artificial Intelligence to project the market's trajectory over the next month"; inputs "fast-moving macroeconomic variables in combination with technical indicators over the index". Medium confidence on what it does when triggered: for Momentum it "reallocat[es] to cash" and, at the firm level, "switch[es] to safer havens of bonds and gold ETFs"; whether the momentum book goes fully or partially to cash is not stated. The only concrete regime rule they print is the one they attribute to the threshold family (200-DMA), not to themselves.

3. **The down-capture advantage is concentrated in the 2021-22 bear, and it disappears in the 2024-25 unwind.** High confidence, from arithmetic. Over Oct-2020 to Aug-2026 their down-capture is 0.90; restricted to Jul-2023 to Aug-2026 it is 0.94, and in Jan-Feb 2025 they lost -18.4% against the index's -18.2%. The one leg where they clearly did not participate is Oct-21 to Jun-22 (-3.4 vs -12.4), which is the episode the regime post claims ("deallocating away from equities then ... the market volatility lasted for more than a year"). So the sources and the grid agree on where the edge was earned, and it is one episode. This matches our own §8 finding that no exposure device fixes Sep-24 to Feb-25 without giving up the bull legs.

4. **Position weights are not equal-weight.** Medium-high confidence. The 2020 launch post states mean-variance optimisation with a 10% single-name cap and sector/industry limits; the 2023 guide states rank-based "weight scoring". Both are non-equal schemes; the 2023 text may describe a later version. A 10% cap on 20-25 names is only mildly binding (equal weight is 4-5%), so the cap itself is not the lever; the covariance-aware tilt is what would lower beta.

5. **Momentum's universe is closer to our Nifty 250 book than our NSE 500 book.** High confidence for "top 300 by market capitalisation" with a traded-volume floor. Our down-capture problem is far worse on NSE 500 (1.37) than on Nifty 250 (1.11); part of the gap to Wright is universe, not device. Alpha, by contrast, is explicitly "top 500 ... including high quality smallcap".

6. **The selection signal is a composite, includes non-return technicals, and (since at least 2023) an earnings-momentum leg.** Medium confidence. Launch post: "a combination of a few of the momentum factors" after listing 12-month return, risk-adjusted return, Bollinger breakouts and RSI. Guide: "based on earnings momentum and price trends". No weights or lookbacks are given anywhere, and the "low volatility" phrase never comes with a rule.

7. **The 2021 result is unlikely to be explained by any single stated mechanism, and part of the printed 2021 record predates the product.** Medium confidence. The launch post is dated 06 Dec 2020 and calls it "a free for all research product for the time being", the guide's constituent examples all start 06 Dec 2020, but the factsheet grid starts Oct-2020 (1.70, 5.20). The disclosure says charts "might include backtested/simulated results". So Oct-Nov 2020, and possibly early 2021, are model-portfolio or backtest months. Within 2021 they beat the index in most months rather than through one outsized month; the stated ingredients that could produce that are the earnings-momentum leg (2021 was an earnings-upgrade year) and mean-variance weighting keeping the book in lower-beta trend names. Neither can be confirmed from the sources.

8. **Alpha (10 names, weekly, top-500) has lower down-capture than Momentum on the overlap window but also lower up-capture, and a worse worst-month.** High confidence, arithmetic. 1.00 / 0.79 vs 1.06 / 0.94; Jan-2025 -18.6 vs -10.3. This is the same shape as our §8 "concentrate in bear" cells: concentration removes the tail of the rank list in ordinary down months and does nothing in a momentum-crash month.

9. **The "10 Years Expected Performance" tables are since-inception live numbers, not 10-year backtests.** Medium-high confidence: the Annualized Returns row equals the Inception column on both factsheets, and the Alpha "10 year" CAGR quoted in the launch blog (35%+) differs from the table's 25.4.

10. **Numbers are gross of costs.** High confidence: disclosure text on both factsheets; guide estimates investor-side frictions at "0.5% to 1% on average". Subscription fees (Rs 7,200-10,000 per year) are additional and, on the stated minimum investments, are a large percentage; they are not in the returns.

11. **Discretion sits on top of the model.** High confidence: "This rank is reviewed & analysed in depth by our Investment Team & the Investment Advisor approves the stocks into the portfolio"; exceptional rebalances "in cases of adverse market conditions or negative developments specific to a stock"; the live Alpha rebalance note reads as a manager's call ("reducing exposure to Adani group"). Any replication is of the systematic core only.

---

## 4. Hypotheses we can test

Ranked by how directly the sources support the mechanism and how plausibly it addresses the down-capture gap. All post-OOS by construction; judge on both legs as in §8.

1. **Forecast-style regime gate with a one-month horizon, driven by index technicals plus a fast macro/risk proxy, deallocating to cash.** Config: weekly evaluation (their "reviewed weekly"); risk score from NIFTY 500 (or 100) distance from 200-DMA, 21-day realised vol, and India VIX level/change (the fastest "macro" series we hold); regime = risky when score exceeds its trailing 1-year 75th percentile for 2 consecutive weeks; exposure 100% / 50% / 0% by score tercile; re-enter on the next non-risky week. Reason: the only episode in which their down-capture edge is earned (Oct-21 to Jun-22) is the one they attribute to "deallocating away from equities". Our §8 overlays used ROC31 and breadth only; a vol-aware, weekly-evaluated switch is the nearest stated analogue. Expect it to do nothing for Sep-24 to Feb-25, which it also did nothing for them.

2. **Mean-variance (or minimum-variance-tilted) position sizing with a 10% single-name cap and sector/industry caps.** Config: weights = argmin w'Σw subject to sum 1, 0 ≤ w ≤ 10%, sector ≤ 25%, with Σ from 126-day daily returns with Ledoit-Wolf shrinkage; cheaper first pass: inverse-vol weights with the same caps. Reason: this is the one position-sizing rule they have ever printed ("mean variance optimisation ... no single stock gets more than 10% ... limit on sector and industry allocations"). It lowers the book's beta without changing the names, which is exactly the shape of a down-capture reduction at unchanged up-capture. Our §8 vol targeting scaled the whole book on index vol; per-name covariance weighting has not been tried.

3. **Top-300 universe with a traded-volume floor, in place of NSE 500.** Config: top 300 by free-float market cap at each reconstitution, median 63-day traded value above a floor (e.g. Rs 5 crore/day), otherwise the §3 base. Reason: "top 300 by market capitalization" and "minimum criteria in daily traded volume"; our down-capture is 1.37 on NSE 500 against 1.11 on Nifty 250, so a large part of the gap to 0.90 is universe beta, which §8 already concluded ("NSE 500's problem is the whole book's beta").

4. **Composite momentum score that mixes 12-month return, risk-adjusted return and a technical-breakout leg, with a low-volatility screen before ranking.** Config: score = mean of z(12-1 return), z(12-1 return / 252-day vol), z(RSI-14 or distance above upper Bollinger band); drop the top vol tercile of the universe before ranking. Reason: "a combination of a few of the momentum factors" after naming exactly these, plus "high momentum stocks with a check for volatility". Our §3g tested other momentum measures singly; a composite with a vol pre-screen has not been run.

5. **Sector cap of 25-30% on the 25-name book.** Config: at each rebalance, if a sector exceeds the cap, replace the lowest-ranked names in that sector with the next-ranked names from other sectors. Reason: "We put a limit on sector and industry allocations"; our Sep-24 to Feb-25 unwind (-25 to -29 across every cell) is the signature of sector-concentrated momentum (PSU/defence/capital goods), and their Jan-Feb 2025 (-18.4) was index-like rather than worse than index.

6. **Monthly rebalance with a weekly exit-only review (stock-level).** Config: names change monthly; weekly, exit any name that has fallen 20% from its peak or has dropped out of the top 50% of the momentum rank, replacement deferred to the monthly date. Reason: "Portfolio review is different from rebalancing"; exceptional rebalances "immediately implemented" for adverse stock-specific events. Our §8 trailing stop (Nifty 250: down 1.11 to 0.99, OOS 0.73 to 0.83) already shows the sign of a weekly exit device on a monthly book.

7. **Earnings-momentum leg in the score.** Config: add z(trailing-quarter EPS surprise or 3-month change in consensus EPS) as a fourth leg of the composite in item 4, or as an eligibility filter (positive earnings revision). Reason: "dual focus on earnings momentum and price momentum"; the 2021 result is the year this would have mattered most. Lowest rank only because we have no fundamentals feed on the honest universe yet (see memory: fundamentals feed is the open thread); it is a data-acquisition task before it is a test.

Not proposed, because the sources do not support it: profit targets, dynamic name count, and vol targeting on index vol (they never state a target; our §8 already showed it cuts up and down together).

---

## Caveats

- Marketing register throughout: "highly accurate predictive model", "proven performance", "AI". None of the pages gives a formula, a lookback, a threshold, or a weight.
- Both factsheets disclose that numbers "might include backtested/simulated results" and exclude transaction costs and dividends; the Momentum grid starts two months before the dated launch post; the Alpha "10 year CAGR of 35%+" in the 2023 blog is a backtest figure by their own statement.
- Internal contradictions: Alpha rebalance is "Weekly" on the factsheet and page header but "bi-weekly" in the page long-text and the launch blog; both product pages carry a generic FAQ saying "18-22 stocks" against the products' stated 10 and 20-25; the regime post's dated episodes disagree with each other by a year.
- Weighting is described two ways two years apart (mean-variance with caps in 2020; rank-based weight scoring in 2023). Treat the 2020 text as the more concrete and the 2023 text as possibly describing a change.
- Discretion is explicit at every stage; a replication tests the systematic core only.
- Pages not read: the SSRN papers (blocked), the login-gated report downloads and metrics panels.
- Grid arithmetic in section 2 uses our synthetic MidSmall 400 series; Wright benchmarks against BSE 500 / "Multicap Index".

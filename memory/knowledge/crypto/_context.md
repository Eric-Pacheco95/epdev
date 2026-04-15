# Crypto Domain Knowledge

Last updated: 2026-04-15

## Domain Overview

Two primary knowledge clusters: (1) automated trading bot technology and market dynamics, and (2) DeFi market structure including MEV and algorithmic opportunities. No sub-domain threshold (3+ articles) met -- all findings consolidated here.

Note: one source article (2026-03-30_geo-strategy-iran-trap.md, domain=geopolitics) is off-domain for crypto synthesis and is excluded below.

## Trading Bot Landscape

- Bot market at $1.6B (2024), projected $5.4B (2032) at 16% CAGR; dominated by commercial SaaS (3Commas, Cryptohopper, Pionex) and open-source (Freqtrade, Hummingbot, Jesse)
- Overfitting is the primary kill factor: ~44% of published strategies fail live; backtested Sharpe ratios have R^2 < 0.025 as a predictor of forward performance
- Standard Python stack is mature: CCXT handles 100+ exchange connectivity; Freqtrade is the primary open-source orchestration layer

## DeFi Market Structure and MEV

- DeFi TVL ~$130-140B in early 2026; MEV extraction exceeds $3B/yr across ETH L2s and Solana -- approximately double 2024 figures
- ETH L1 MEV is fully institutionalized: ~20 entities dominate, average sandwich profit dropped to ~$3, 30% of bots operate at net loss -- not viable for solo operators
- Viable 2026 entry points: cross-chain arbitrage and Solana-native MEV via Jito; 0.5-5% spreads persist for minutes across 50+ chains; Jito infrastructure is accessible to non-institutional actors
- Latency-sensitive DeFi searching requires Rust; Python stack insufficient for competitive MEV

## Cross-Cutting Themes

- Commoditization pressure: infrastructure costs (exchange fees, gas, MEV competition) erode alpha faster than strategies adapt
- Overfitting and data leakage are the dominant failure modes for both CEX bots and DeFi searchers
- Institutional capture: most profitable niches (ETH L1 MEV, HFT arbitrage) are locked; solo operator opportunity concentrates in longer-tail chains and less-liquid DEX pairs
- Tech stack bifurcation: Python (CCXT/Freqtrade) for CEX; Rust for latency-critical DeFi
- Backtesting validity is structurally weak: no published benchmark reliably predicts live alpha

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] Market size figures ($1.6B, $5.4B) rely on third-party TAM methodology; definitions of "trading bot market" vary and likely include SaaS subscription revenue rather than AUM
- [ASSUMPTION] "44% overfitting" rate cited without traceable primary source; likely derived from strategy publication databases that already exhibit survivorship bias
- [ASSUMPTION] MEV profitability data is reconstructed from public blockchain traces; private searcher flow and OTC extraction are excluded, potentially understating institutional dominance
- [ASSUMPTION] "~20 entities dominate" ETH L1 MEV is based on observable searcher addresses, not verified legal entities -- same firm may operate multiple addresses
- [FALLACY] Survivorship bias: published strategies that "look great" in backtests are pre-selected; the failure rate of all attempted strategies is unknown and likely higher than 44%
- [FALLACY] Hasty generalization: "0.5-5% spreads persist for minutes" may reflect cherry-picked market conditions; spread persistence varies by chain congestion and liquidity depth
- [FALLACY] False dichotomy: framing ETH L1 as "not viable" vs. Solana/L2 as "viable" treats a continuous profitability spectrum as binary; some L1 niches may remain accessible
- [FALLACY] Appeal to authority: CCXT described as the "solved" connectivity standard -- does not account for non-EVM chain ecosystems (Solana, Move-based chains) where CCXT coverage is partial
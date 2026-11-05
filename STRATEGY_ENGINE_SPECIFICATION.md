# Options Strategy Engine Specification

> **Document Version**: 2.0  
> **Classification**: Quantitative Strategy Architecture  
> **Module**: Strategy Registry, Leg Resolver, and Explainable Scoring Pipeline

---

## 1. Strategy Evaluation Workflow

```
Incoming Normalized Option Chain
         │
         ▼
┌─────────────────────────────────┐
│ Quantitative Indicators Engine  │ ──> (ATM, Max Pain, PCR, IV Skew, Liquidity)
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ Market Regime Classifier        │ ──> (Directional Bias, Market State)
└────────────────┬────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│ Multi-Strategy Iterator (16 Classical Specifications)  │
│                                                        │
│  1. Leg Resolution: Map abstract offsets to contracts  │
│  2. Expiry Payoff: Calculate net debit/credit, PnL     │
│  3. Risk Solver: Max profit, max loss, breakevens      │
│  4. Friction Model: Calculate brokerage, STT, GST      │
│  5. Confidence Index: 0 to 100 Explainable Score       │
└────────────────┬───────────────────────────────────────┘
                 ▼
Categorized Strategy Candidates: QUALIFIED | WATCHLIST | REJECTED
```

---

## 2. Quantitative Scoring Heuristics (0 - 100 Index)

Each strategy is assigned a transparent, deterministic score out of 100 points:

1. **Directional & Regime Alignment (30 Points)**:
   - Perfect alignment between strategy category and market regime (`+30 pts`).
   - Neutral strategy in consolidating regime (`+18 pts`).
   - Counter-trend strategy (`0 pts` + failed rule log).
2. **Volatility Environment (25 Points)**:
   - Credit spreads and iron condors favored in high IV ($>18\%$) due to rich option premia (`+25 pts`).
   - Breakout debit straddles favored in compressed IV ($<14\%$) (`+25 pts`).
3. **Key Strike Alignment (20 Points)**:
   - Bullish strategy entries positioned with spot safely above major Put OI support (`+20 pts`).
   - Bearish strategy entries positioned with spot safely below major Call OI resistance (`+20 pts`).
4. **Reward-to-Risk & Capital Quality (15 Points)**:
   - Strategy satisfies minimum reward-to-risk threshold (`+15 pts`).
   - Uncapped upside strategies default to (`+15 pts`).
5. **Bid-Ask Liquidity & Execution (10 Points)**:
   - Chain liquidity score $\ge 70/100$ ensures minimal execution slippage (`+10 pts`).

### Classification Thresholds:
* **`QUALIFIED`**: Score $\ge 75.0$
* **`WATCHLIST`**: $50.0 \le \text{Score} < 75.0$
* **`REJECTED`**: $\text{Score} < 50.0$

---

## 3. The 16 Classical Strategy Leg Specifications

### 3.1 Bullish Strategies
1. **Long Call**: $+1 \text{ Call (ATM)}$
2. **Bull Call Spread**: $+1 \text{ Call (ATM)}, -1 \text{ Call (OTM } +1 \text{ step)}$
3. **Bull Put Spread**: $-1 \text{ Put (OTM } -1 \text{ step)}, +1 \text{ Put (OTM } -2 \text{ steps)}$
4. **Call Ratio Spread**: $+1 \text{ Call (ATM)}, -2 \text{ Call (OTM } +2 \text{ steps)}$

### 3.2 Bearish Strategies
5. **Long Put**: $+1 \text{ Put (ATM)}$
6. **Bear Put Spread**: $+1 \text{ Put (ATM)}, -1 \text{ Put (OTM } -1 \text{ step)}$
7. **Bear Call Spread**: $-1 \text{ Call (OTM } +1 \text{ step)}, +1 \text{ Call (OTM } +2 \text{ steps)}$
8. **Put Ratio Spread**: $+1 \text{ Put (ATM)}, -2 \text{ Put (OTM } -2 \text{ steps)}$

### 3.3 Neutral Strategies
9. **Iron Condor**: $+1 \text{ Put (-3)}, -1 \text{ Put (-1)}, -1 \text{ Call (+1)}, +1 \text{ Call (+3)}$
10. **Iron Butterfly**: $+1 \text{ Put (-2)}, -1 \text{ Put (ATM)}, -1 \text{ Call (ATM)}, +1 \text{ Call (+2)}$
11. **Short Straddle**: $-1 \text{ Call (ATM)}, -1 \text{ Put (ATM)}$
12. **Short Strangle**: $-1 \text{ Put (-2 steps)}, -1 \text{ Call (+2 steps)}$

### 3.4 Volatility Strategies
13. **Long Straddle**: $+1 \text{ Call (ATM)}, +1 \text{ Put (ATM)}$
14. **Long Strangle**: $+1 \text{ Put (-2 steps)}, +1 \text{ Call (+2 steps)}$
15. **Calendar Spread**: $-1 \text{ Call (Near ATM)}, +1 \text{ Call (Far ATM)}$
16. **Diagonal Spread**: $-1 \text{ Call (Near OTM } +1), +1 \text{ Call (Far ATM)}$


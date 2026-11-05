# Risk Engine & Greeks Mathematical Specification

> **Document Version**: 2.0  
> **Classification**: Quantitative Mathematical Specification  
> **Module**: Black-Scholes Pricing, Greeks Sensitivities, Breakeven Solver, and Indian Transaction Friction

---

## 1. Black-Scholes-Merton Continuous Dividend Yield Model

European index options on NSE (`NIFTY`, `BANKNIFTY`) are evaluated using the Black-Scholes-Merton (1973) continuous dividend yield adaptation ($q \approx 0.012$):

$$d_1 = \frac{\ln(S / K) + \left(r - q + \frac{\sigma^2}{2}\right)T}{\sigma \sqrt{T}}$$

$$d_2 = d_1 - \sigma \sqrt{T}$$

### Option Pricing Equations:
$$\text{Call Price } (C) = S e^{-q T} N(d_1) - K e^{-r T} N(d_2)$$

$$\text{Put Price } (P) = K e^{-r T} N(-d_2) - S e^{-q T} N(-d_1)$$

Where:
* $S$ = Current underlying spot price
* $K$ = Option strike price
* $T$ = Annualized time to expiration ($\text{days} / 365.0$)
* $r$ = Annualized risk-free interest rate (RBI Repo benchmark $\approx 6.5\%$)
* $q$ = Annualized continuous dividend yield ($\approx 1.2\%$)
* $\sigma$ = Annualized implied volatility
* $N(x)$ = Standard normal cumulative distribution function (CDF)

---

## 2. Quantitative Risk Sensitivities (Greeks)

### 2.1 Delta ($\Delta$)
The first derivative with respect to underlying spot price:
$$\Delta_{\text{Call}} = e^{-q T} N(d_1) \quad (\in [0, 1])$$
$$\Delta_{\text{Put}} = e^{-q T} [N(d_1) - 1] \quad (\in [-1, 0])$$

### 2.2 Gamma ($\Gamma$)
The second derivative with respect to underlying spot price (identical for Call and Put):
$$\Gamma = \frac{e^{-q T} N'(d_1)}{S \sigma \sqrt{T}}$$
Where $N'(x) = \frac{1}{\sqrt{2\pi}} e^{-\frac{x^2}{2}}$ is the standard normal probability density function (PDF).

### 2.3 Theta ($\Theta$)
Calendar time decay per day ($\Theta_{\text{annual}} / 365.0$):
$$\Theta_{\text{Call}} = -\frac{S e^{-q T} N'(d_1) \sigma}{2 \sqrt{T}} - r K e^{-r T} N(d_2) + q S e^{-q T} N(d_1)$$
$$\Theta_{\text{Put}} = -\frac{S e^{-q T} N'(d_1) \sigma}{2 \sqrt{T}} + r K e^{-r T} N(-d_2) - q S e^{-q T} N(-d_1)$$

### 2.4 Vega ($\nu$)
Price sensitivity per 1% absolute shift in implied volatility:
$$\nu = \frac{S e^{-q T} \sqrt{T} N'(d_1)}{100.0}$$

---

## 3. Implied Volatility Root-Finding Algorithm

Given market price $C_{\text{mkt}}$, Implied Volatility is the unique root $\sigma$ satisfying:
$$f(\sigma) = C_{\text{BS}}(\sigma) - C_{\text{mkt}} = 0$$

### Solver Architecture:
1. **Newton-Raphson Step**:
   $$\sigma_{n+1} = \sigma_n - \frac{f(\sigma_n)}{\nu(\sigma_n)}$$
2. **Brent-Decker Bisection Fallback**:
   When $\nu(\sigma_n) < 10^{-6}$ or when iterates diverge outside $[0.01, 3.0]$, the solver automatically drops into bounded bisection down to $10^{-5}$ precision.

---

## 4. Indian Transaction Cost Model (Regulatory Friction)

The risk engine computes gross theoretical payoff as well as **Net Realizable Payoff (Post-Friction)**:

$$\text{Net PnL} = \text{Gross Expiry Payoff} - \text{Total Friction}$$

### Cost Parameter Matrix:
* **Brokerage**: Fixed ₹20 per executed leg order ($2 \times \text{legs} \times ₹20$).
* **Securities Transaction Tax (STT)**: 0.1% on sell-side option premium.
* **Exchange Turnover Fee**: 0.05% on total premium turnover.
* **GST**: 18% on (Brokerage + Exchange Turnover Fee).
* **Stamp Duty**: 0.003% on buy-side turnover.
* **SEBI Turnover Fee**: ₹10 per crore (0.0001%).
* **Slippage**: Configurable 0.2% on market order entry/exit.


# NASDAQ Multi-Timeframe Strategy Backtester

A deterministic, chronological, event-driven backtesting engine engineered specifically for NASDAQ futures (`NQ` / `MNQ`) multi-timeframe strategies.

---

## Strategy Hierarchy

$$\text{1H Reference} \longrightarrow \text{15M Direction} \longrightarrow \text{5M Confirmation} \longrightarrow \text{1M Entry} \longrightarrow \text{Dynamic R-Trailing SL}$$

1. **1H Reference:** Completed 1H bar defines `Reference High` and `Reference Low`.
2. **15M Direction:**
   - `UP_BREAKOUT`: High > 1H High & Close > 1H High $\rightarrow$ LONG
   - `DOWN_BREAKOUT`: Low < 1H Low & Close < 1H Low $\rightarrow$ SHORT
   - `UPSWEEP`: High > 1H High & Close $\le$ 1H High $\rightarrow$ Potential SHORT
   - `DOWNSWEEP`: Low < 1H Low & Close $\ge$ 1H Low $\rightarrow$ Potential LONG
3. **5M Confirmation:** Confirms directional break. *5M sweeps are ignored as independent signals.*
4. **1M Entry:** Executes on the next bar open following confirmation.
5. **Structural SL & Dynamic Trailing:**
   - SL anchored to recent 1M swing/structure.
   - At $+1R$: SL moved to $+1R$ (100% position open, no partial profit).
   - At $+3R$: SL moved to $+3R$.
   - Post-$+3R$: For every additional $+1R$ ($4R, 5R, 6R\dots$), SL advances by $+1R$.
   - No fixed take-profit (TP).

---

## Installation

```bash
# 1. Clone repo & create virtualenv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
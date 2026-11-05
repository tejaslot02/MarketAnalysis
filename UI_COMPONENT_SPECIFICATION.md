# UI Component & Design System Technical Specification

> **Document Version**: 2.0  
> **Classification**: Frontend Architecture & UI Design System  
> **Framework**: Native Vanilla JavaScript (ES6+), HTML5, CSS3 Custom Properties

---

## 1. Multi-Theme Token Matrix

All UI components dynamically inherit colors from CSS custom properties defined in `ui/css/styles.css`.

| Design Token | 🌸 Pastel Day (Default Light) | 🌙 Pastel Dusk (Dark) | 🌑 Classic Dark |
| :--- | :--- | :--- | :--- |
| `--bg-primary` | `#f6f8fd` (Porcelain Slate) | `#151722` (Twilight Slate) | `#07090e` (Obsidian) |
| `--bg-secondary` | `#ffffff` (Pure White Card) | `#1c1f2e` (Velvet Card) | `#0f1422` (Slate 900) |
| `--bg-tertiary` | `#eef2f9` (Subtle Lavender) | `#232738` (Card Highlight) | `#182032` (Dark Highlight) |
| `--text-primary` | `#1e293b` (Deep Slate) | `#f1f5f9` (Bright Slate) | `#f8fafc` (Snow White) |
| `--text-secondary`| `#475569` (Muted Slate) | `#94a3b8` (Muted Twilight)| `#94a3b8` (Slate 400) |
| `--call-accent` | `#059669` / `#7dd3fc` (Mint Call)| `#7dd3fc` (Luminous Sky) | `#38bdf8` (Cyan Blue) |
| `--put-accent` | `#e11d48` / `#fda4af` (Rose Put)| `#fda4af` (Blush Coral) | `#f43f5e` (Crimson Rose) |
| `--accent-gold` | `#d97706` (Amber Accent) | `#fde047` (Pale Amber) | `#f59e0b` (Deep Amber) |
| `--accent-blue` | `#0284c7` (Cobalt Blue) | `#38bdf8` (Electric Blue) | `#38bdf8` (Cyan) |

---

## 2. Reusable Component Hierarchy

```
Body
├── Header (.navbar)
│   ├── Brand (.brand)
│   ├── Quick Index Pills (.symbol-pill)
│   ├── Stock Search (.symbol-search-wrapper)
│   └── Controls: Market Badge, Theme Selector, Auto-Refresh Interval
│
├── Section Navigation (.section-nav)
│   ├── Option Chain Terminal Button ([data-section="view-terminal"])
│   └── Options Intelligence Button ([data-section="view-intelligence"])
│
├── Main Container (.container)
│   ├── View Panel 1: Option Chain Terminal (#view-terminal)
│   │   ├── Executive Metrics Grid (.metrics-grid)
│   │   ├── Insights Banner (.insights-banner)
│   │   ├── Controls Bar (.controls-bar)
│   │   ├── Terminal Tabs Navigation (.tab-nav)
│   │   └── Tab Contents: Matrix, OI Charts, Max Pain, IV Smile, Snapshots
│   │
│   └── View Panel 2: Options Strategy Intelligence (#view-intelligence)
│       ├── Data Mode Compliance Banner (.data-mode-banner)
│       ├── Intelligence Tabs Navigation (.tab-nav)
│       ├── Overview Sub-Tab (#intel-overview)
│       ├── Strategy Scanner Sub-Tab (#intel-scanner)
│       │   ├── Category Pills (.range-pill-group)
│       │   └── Strategy Cards Grid (.strategy-cards-grid)
│       ├── Payoff Simulator Sub-Tab (#intel-simulator)
│       │   ├── Live Stats Grid (.strategy-stats-grid)
│       │   ├── Legs Builder Table (.table-card)
│       │   ├── Payoff Chart (.chart-card)
│       │   └── Multi-Variable Scenario Heatmap
│       ├── Backtesting Sub-Tab (#intel-backtest)
│       └── Alerts Sub-Tab (#intel-alerts)
│
├── Modals (.modal-backdrop)
│   └── Rule Inspection Modal (#rule-inspect-modal)
│
└── Toast Notification Stream (#toast-container)
```

---

## 3. Chart.js Theme Adaptation

Charts instantiate dynamically via `window.getThemeColors()`, ensuring canvas backgrounds, gridlines, labels, and tooltips seamlessly shift palette when users toggle themes without page reloads.

```javascript
// High-level pattern in ui/js/app.js & modules:
function applyTheme(themeName) {
  document.documentElement.setAttribute('data-theme', themeName);
  localStorage.setItem('market_terminal_theme', themeName);
  // Instantly re-render charts with active palette
  renderCharts();
}
```


---
version: alpha
name: Sponge-design-analysis
description: Sponge — a terminal-native agent harness that compresses LLM costs to 1/10 through architecture alone. The surface is a warm near-charcoal canvas, broken only by clean Inter typography, DM Mono for all code surfaces, and a single muted teal accent reserved for savings metrics and the primary CTA. The brand reads as quietly confident — no gradients, no illustrations, no drop shadows. The architecture speaks for itself.

colors:
  # ── Brand accent (used sparingly) ──
  primary: "#2dd4bf"
  primary-deep: "#14b8a6"
  on-primary: "#1a1a2e"

  # ── Surface ──
  canvas: "#1e1e24"
  canvas-soft: "#262630"
  canvas-raised: "#2e2e38"

  # ── Text ──
  ink: "#e4e4e7"
  body: "#a1a1aa"
  body-strong: "#d4d4d8"
  mute: "#71717a"
  mute-soft: "#52525b"

  # ── Hairlines ──
  hairline: "#3f3f46"
  hairline-strong: "#52525b"

  # ── Semantic ──
  savings: "#2dd4bf"
  savings-soft: "#0d3b36"
  warning: "#f59e0b"
  warning-soft: "#3d2e00"
  error: "#ef4444"
  error-soft: "#3b1010"
  info: "#60a5fa"
  info-soft: "#0c1d3b"
  success: "#34d399"
  success-soft: "#0a2e1f"

  # ── Cost-level indicators ──
  cost-low: "#34d399"
  cost-med: "#f59e0b"
  cost-high: "#ef4444"

typography:
  display-xl:
    fontFamily: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif
    fontSize: 48px
    fontWeight: 500
    lineHeight: 56px
    letterSpacing: -1.2px
  display-lg:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 32px
    fontWeight: 500
    lineHeight: 40px
    letterSpacing: -0.8px
  display-md:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 24px
    fontWeight: 500
    lineHeight: 32px
    letterSpacing: -0.4px
  display-sm:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 20px
    fontWeight: 500
    lineHeight: 28px
    letterSpacing: -0.2px
  body-lg:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
  body-md:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
  body-md-strong:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 500
    lineHeight: 24px
  body-sm:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
  body-sm-strong:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
  caption:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
  caption-mono:
    fontFamily: "DM Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 11px
    fontWeight: 400
    lineHeight: 16px
    letterSpacing: 0.5px
    textTransform: uppercase
  code:
    fontFamily: "DM Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
  code-sm:
    fontFamily: "DM Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 12px
    fontWeight: 400
    lineHeight: 18px
  button-md:
    fontFamily: Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
  stat-xl:
    fontFamily: "DM Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 40px
    fontWeight: 400
    lineHeight: 48px
    letterSpacing: -1px
  stat-lg:
    fontFamily: "DM Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 28px
    fontWeight: 400
    lineHeight: 36px
    letterSpacing: -0.5px
  stat-md:
    fontFamily: "DM Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 20px
    fontWeight: 400
    lineHeight: 28px

rounded:
  none: 0px
  xs: 2px
  sm: 4px
  md: 6px
  lg: 8px
  xl: 12px
  pill: 9999px
  full: 9999px

spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  2xl: 32px
  3xl: 48px
  4xl: 64px
  5xl: 96px

components:
  # ── Navigation ──
  nav-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm-strong}"
    height: 48px
    padding: "{spacing.sm} {spacing.lg}"
    borderBottom: "1px solid {colors.hairline}"
  nav-link:
    backgroundColor: transparent
    textColor: "{colors.body}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs} {spacing.sm}"
    hoverTextColor: "{colors.ink}"

  # ── Buttons ──
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.lg}"
    height: 36px
  button-primary-pressed:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.lg}"
    height: 36px
    border: "1px solid {colors.hairline}"
  button-ghost:
    backgroundColor: transparent
    textColor: "{colors.body}"
    typography: "{typography.button-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs} {spacing.sm}"
    hoverBackgroundColor: "{colors.canvas-soft}"
  button-icon:
    backgroundColor: transparent
    textColor: "{colors.body}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
    hoverBackgroundColor: "{colors.canvas-soft}"

  # ── Cards ──
  card-default:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  card-raised:
    backgroundColor: "{colors.canvas-raised}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline-strong}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  card-stat:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
    statTypography: "{typography.stat-xl}"
    labelTypography: "{typography.caption-mono}"

  # ── Terminal / Code Surfaces ──
  terminal-block:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.code}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
    border: "1px solid {colors.hairline}"
  terminal-line:
    typography: "{typography.code}"
    textColor: "{colors.body}"
    promptColor: "{colors.primary}"
  terminal-output:
    typography: "{typography.code-sm}"
    textColor: "{colors.mute}"
  code-block:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.code}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
    border: "1px solid {colors.hairline}"

  # ── Cost & Savings Displays ──
  savings-badge:
    backgroundColor: "{colors.savings-soft}"
    textColor: "{colors.savings}"
    typography: "{typography.caption-mono}"
    rounded: "{rounded.pill}"
    padding: "{spacing.xxs} {spacing.sm}"
  cost-bar:
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.xs}"
    height: 4px
  cost-bar-fill-low:
    backgroundColor: "{colors.cost-low}"
    rounded: "{rounded.xs}"
  cost-bar-fill-med:
    backgroundColor: "{colors.cost-med}"
    rounded: "{rounded.xs}"
  cost-bar-fill-high:
    backgroundColor: "{colors.cost-high}"
    rounded: "{rounded.xs}"
  metric-row:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    padding: "{spacing.sm} 0"
    labelTypography: "{typography.body-sm}"
    valueTypography: "{typography.stat-md}"

  # ── Status Indicators ──
  status-dot-success:
    backgroundColor: "{colors.success}"
    rounded: "{rounded.full}"
    width: 8px
    height: 8px
  status-dot-warning:
    backgroundColor: "{colors.warning}"
    rounded: "{rounded.full}"
    width: 8px
    height: 8px
  status-dot-error:
    backgroundColor: "{colors.error}"
    rounded: "{rounded.full}"
    width: 8px
    height: 8px
  status-dot-idle:
    backgroundColor: "{colors.mute}"
    rounded: "{rounded.full}"
    width: 8px
    height: 8px

  # ── Agent Step Timeline ──
  timeline-step:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    borderLeft: "2px solid {colors.hairline}"
    padding: "{spacing.sm} {spacing.md}"
    stepTypography: "{typography.body-sm}"
    costTypography: "{typography.caption-mono}"
  timeline-step-active:
    borderLeft: "2px solid {colors.primary}"
  timeline-step-completed:
    borderLeft: "2px solid {colors.success}"

  # ── Tags & Pills ──
  pill-tag:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.body}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "{spacing.xxs} {spacing.sm}"
  pill-tag-accent:
    backgroundColor: "{colors.savings-soft}"
    textColor: "{colors.savings}"
    typography: "{typography.caption-mono}"
    rounded: "{rounded.pill}"
    padding: "{spacing.xxs} {spacing.sm}"

  # ── Text Input ──
  text-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.code}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.md}"
    height: 36px
    focusBorderColor: "{colors.primary}"

  # ── Sections ──
  hero-band:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-xl}"
    padding: "{spacing.5xl} {spacing.xl}"
  content-band:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-md}"
    padding: "{spacing.4xl} {spacing.xl}"
  content-band-alt:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.display-md}"
    padding: "{spacing.4xl} {spacing.xl}"
  footer:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.mute}"
    typography: "{typography.body-sm}"
    padding: "{spacing.3xl} {spacing.xl}"
    borderTop: "1px solid {colors.hairline}"

  # ── Data Display ──
  data-table:
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.md}"
    border: "1px solid {colors.hairline}"
  data-table-header:
    backgroundColor: "{colors.canvas-raised}"
    textColor: "{colors.body-strong}"
    typography: "{typography.caption-mono}"
    padding: "{spacing.sm} {spacing.md}"
    borderBottom: "1px solid {colors.hairline-strong}"
  data-table-cell:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    padding: "{spacing.sm} {spacing.md}"
    borderBottom: "1px solid {colors.hairline}"

  # ── Notifications ──
  toast:
    backgroundColor: "{colors.canvas-raised}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.md}"
    border: "1px solid {colors.hairline}"
  toast-success:
    borderLeft: "3px solid {colors.success}"
  toast-warning:
    borderLeft: "3px solid {colors.warning}"
  toast-error:
    borderLeft: "3px solid {colors.error}"

  # ── Empty State ──
  empty-state:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.mute}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.3xl}"
    border: "1px dashed {colors.hairline}"

  # ── Modal ──
  modal-overlay:
    backgroundColor: "rgba(0, 0, 0, 0.6)"
  modal-card:
    backgroundColor: "{colors.canvas-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
    border: "1px solid {colors.hairline}"

---

## Overview

Sponge is a terminal-native agent harness — a CLI tool that orchestrates LLM calls while compressing token costs to 1/10 through architecture alone. It is not a model router or a caching add-on; it is a ground-up agent architecture where every design decision — task decomposition, progressive context loading, sub-agent condensation, memory-based reuse — eliminates wasted tokens.

The design language mirrors this engineering-first posture: a single dark band running the entire page, warmer than pure black (`{colors.canvas}` `#1e1e24` carries a subtle blue-cool undertone for a modern terminal feel), with copy set almost entirely in Inter. The page reads more like a developer's terminal session than a marketing surface.

There is no gradient, no atmospheric backdrop, no illustration system. The decoration is the data: cost breakdowns rendered as DM Mono stat blocks, savings metrics as muted teal badges, agent step timelines as left-border progress indicators. The single chromatic event is **Teal** (`{colors.primary}` `#2dd4bf`) — used exclusively for the primary CTA and savings-positive indicators. Everything else is a calibrated gray ladder.

**Key Characteristics:**
- A single teal accent (`{colors.primary}` `#2dd4bf`), used scarcely — primary CTA + savings indicators. No secondary chromatic accent. Everything else is monochrome.
- Deep dark canvas (`{colors.canvas}` `#1e1e24`) with a subtle blue-cool undertone — warmer than VS Code dark, cooler than Warp's brown-warm. This IS the brand's surface. There is no light mode.
- Terminal-block components as the dominant content container — code surfaces are not decorative; they ARE the interface. DM Mono on every code, stat, and metric surface.
- Tight `{rounded.sm}` 4px button radius — the brand never uses generous pill CTAs.
- Cost-level indicators (low/med/high) mapped to a three-tone green→amber→red scale, always rendered as subtle 4px bars or dots, never as saturated banners.
- Hairline-only depth. No drop shadows — surfaces distinguish via contrast between `{colors.canvas}` / `{colors.canvas-soft}` / `{colors.canvas-raised}`.
- Agent step timeline: a vertical left-border progress indicator, color-coded by step status (active = teal, completed = green, pending = hairline).

## Colors

### Brand & Accent
- **Teal** (`{colors.primary}` — `#2dd4bf`): The single brand accent. Used for the primary CTA button, active state indicators, savings-positive metrics, and the prompt character in terminal blocks. Appears on ~2% of the surface area — scarce enough to register as an event.
- **Teal Deep** (`{colors.primary-deep}` — `#14b8a6`): Pressed-state lift of the primary. Used for button:active and the deepest savings-indicator tone.
- **On Primary** (`{colors.on-primary}` — `#1a1a2e`): Dark text on the teal accent — never white. The teal reads as "lit" with dark type.

### Surface
- **Canvas** (`{colors.canvas}` — `#1e1e24`): The deep dark page background. The default surface for every band. Slightly blue-cool to distinguish from brown-warm terminals and pure-black UIs.
- **Canvas Soft** (`{colors.canvas-soft}` — `#262630`): A slightly lifted dark fill used for cards, code blocks, and content containers. ~8% lighter than canvas.
- **Canvas Raised** (`{colors.canvas-raised}` — `#2e2e38`): The highest elevation surface — used for modals, featured cards, and toast notifications.

### Text
- **Ink** (`{colors.ink}` — `#e4e4e7`): Default text on dark surfaces. Off-white with a hint of cool — never pure white.
- **Body Strong** (`{colors.body-strong}` — `#d4d4d8`): Mid-emphasis body text, used for headings and emphasized labels.
- **Body** (`{colors.body}` — `#a1a1aa`): Default running body text. Secondary copy, descriptions, helper text.
- **Mute** (`{colors.mute}` — `#71717a`): Tertiary text — timestamps, fine print, disabled labels.
- **Mute Soft** (`{colors.mute-soft}` — `#52525b`): Lowest-priority text — placeholders, empty-state captions.

### Hairlines
- **Hairline** (`{colors.hairline}` — `#3f3f46`): 1px solid divider — card borders, table row separators, input borders.
- **Hairline Strong** (`{colors.hairline-strong}` — `#52525b`): Slightly stronger divider — section separators, active table header bottom.

### Semantic
- **Savings** (`{colors.savings}` — `#2dd4bf`): Positive cost reduction indicator. Same as primary — intentionally unified so every green event reads as "saved."
- **Savings Soft** (`{colors.savings-soft}` — `#0d3b36`): Dark teal background for savings badges and positive metric cards.
- **Success** (`{colors.success}` — `#34d399`): Task completion, cache hit, step done. Warmer green than the teal primary to distinguish "done" from "saved."
- **Success Soft** (`{colors.success-soft}` — `#0a2e1f`): Dark green background for success indicators.
- **Warning** (`{colors.warning}` — `#f59e0b`): Amber — cost approaching budget, cache miss, attention needed.
- **Warning Soft** (`{colors.warning-soft}` — `#3d2e00`): Dark amber background.
- **Error** (`{colors.error}` — `#ef4444`): Red — task failure, cost overrun, blocking error.
- **Error Soft** (`{colors.error-soft}` — `#3b1010`): Dark red background.
- **Info** (`{colors.info}` — `#60a5fa`): Blue — neutral informational indicator, used rarely.

### Cost-Level Scale
A dedicated three-tone scale for cost visualization — progress bars, sparklines, metric indicators:
- **Cost Low** (`{colors.cost-low}` — `#34d399`): ≤ 30% of budget consumed. Green.
- **Cost Med** (`{colors.cost-med}` — `#f59e0b`): 30–70% of budget consumed. Amber.
- **Cost High** (`{colors.cost-high}` — `#ef4444`): ≥ 70% of budget consumed. Red.

These should render as thin 4px bars or small dots — never as filled banners or backgrounds.

## Typography

### Font Family
Two faces carry the entire system:

1. **Inter** for every display, body, button, link, and label role. Weights 400 / 500 are the working pair (no weight 600+ — the brand stays quiet).
2. **DM Mono** for all code surfaces, terminal output, stat blocks, and technical labels. Weight 400 only. If unavailable, fall back to JetBrains Mono.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-xl}` | 48px | 500 | 56px | -1.2px | Hero headline ("1/10 the cost. Same model."). |
| `{typography.display-lg}` | 32px | 500 | 40px | -0.8px | Section headlines. |
| `{typography.display-md}` | 24px | 500 | 32px | -0.4px | Sub-section displays, card group titles. |
| `{typography.display-sm}` | 20px | 500 | 28px | -0.2px | Compact section heads. |
| `{typography.body-lg}` | 18px | 400 | 28px | 0 | Lead paragraphs under headlines. |
| `{typography.body-md}` | 16px | 400 | 24px | 0 | Default body. |
| `{typography.body-md-strong}` | 16px | 500 | 24px | 0 | Emphasized inline body. |
| `{typography.body-sm}` | 14px | 400 | 20px | 0 | Secondary body, nav-link text. |
| `{typography.body-sm-strong}` | 14px | 500 | 20px | 0 | Button labels, nav emphasis. |
| `{typography.caption}` | 12px | 400 | 16px | 0 | Captions, fine print. |
| `{typography.caption-mono}` | 11px | 400 | 16px | 0.5px | Uppercase section labels, badge text, metric labels. Uses DM Mono. |
| `{typography.code}` | 13px | 400 | 20px | 0 | Terminal blocks, inline code, command snippets. DM Mono. |
| `{typography.code-sm}` | 12px | 400 | 18px | 0 | Dense terminal output, log lines. DM Mono. |
| `{typography.button-md}` | 14px | 500 | 20px | 0 | Button labels. |
| `{typography.stat-xl}` | 40px | 400 | 48px | -1px | Hero metrics — "89% cache hit rate." DM Mono. |
| `{typography.stat-lg}` | 28px | 400 | 36px | -0.5px | Card-level metrics. DM Mono. |
| `{typography.stat-md}` | 20px | 400 | 28px | 0 | Inline metrics, table values. DM Mono. |

### Principles
- **Display at weight 500.** Mid-weight reads as engineered, not decorative. The brand never goes to 600+.
- **DM Mono for metrics.** Every stat, every cost figure, every cache-hit percentage is set in DM Mono. The typeface signals "this is a measurement, not a claim."
- **Negative tracking on display only.** -1.2px at 48px hero, scaling down. Body and code are at neutral tracking.
- **Caption-mono for all section labels.** 11px uppercase DM Mono at 0.5px tracking — the only uppercase element in the system.
- **Inter for narrative, DM Mono for technical.** Strict role separation — never mix.

### Font Substitutes
Both faces are open-source:
- **Inter** — load from Google Fonts or Vercel CDN.
- **DM Mono** — open-source on Google Fonts. **JetBrains Mono** is the secondary fallback for code surfaces.

## Layout

### Spacing System
- **Base unit**: 4px.
- **Tokens**: `{spacing.xxs}` 2px · `{spacing.xs}` 4px · `{spacing.sm}` 8px · `{spacing.md}` 12px · `{spacing.lg}` 16px · `{spacing.xl}` 24px · `{spacing.2xl}` 32px · `{spacing.3xl}` 48px · `{spacing.4xl}` 64px · `{spacing.5xl}` 96px.
- **Section padding**: hero bands use `{spacing.5xl}` 96px; content bands use `{spacing.4xl}` 64px.
- **Card interior**: default cards sit at `{spacing.lg}` 16px; stat cards at `{spacing.lg}` 16px with tighter internal gaps.
- **Inline gap**: button rows, metric clusters, tag groups use `{spacing.sm}` 8px between siblings.

### Grid & Container
- Content centres at ~1100px max-width — narrower than most marketing sites to keep reading comfortable in terminal-like density.
- Stat card clusters: 3-up at desktop, 2-up at tablet, 1-up at mobile.
- Terminal mockup + explanation: 2-column split at desktop (60/40), stacks at mobile.
- Agent timeline: single-column vertical strip, always 320px wide in sidebars, full-width when stacked.

### Whitespace Philosophy
The dark canvas IS the breathing room. Sections are separated by `{spacing.4xl}` to `{spacing.5xl}` vertical gaps — no decorative dividers, no atmospheric fills. The space between elements is the design. Inside cards, content is tighter (8–16px gaps) — the contrast between tight interiors and generous exterior spacing creates the rhythm.

## Elevation & Depth

The system uses **surface-contrast elevation only**. No drop shadows. No gradients.

| Level | Treatment | Use |
|---|---|---|
| Level 0 — Canvas | `{colors.canvas}` `#1e1e24` | Page background, hero bands, content bands. |
| Level 1 — Soft | `{colors.canvas-soft}` `#262630` + 1px `{colors.hairline}` | Default cards, terminal blocks, code blocks. |
| Level 2 — Raised | `{colors.canvas-raised}` `#2e2e38` + 1px `{colors.hairline-strong}` | Modals, featured cards, toasts. |

The progression from canvas → canvas-soft → canvas-raised (~4% lightness step each) creates enough contrast to distinguish surfaces without shadows. Hairline borders reinforce the separation at each step.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | Full-bleed bands, table edges. |
| `{rounded.xs}` | 2px | Cost bar segments, inline indicators. |
| `{rounded.sm}` | 4px | Default button radius, text inputs, terminal blocks. Tight — the brand signature. |
| `{rounded.md}` | 6px | Cards, modals. |
| `{rounded.lg}` | 8px | Larger feature cards, hero terminal mockups. |
| `{rounded.xl}` | 12px | Rare — oversized modal dialogs. |
| `{rounded.pill}` | 9999px | Savings badges, tag pills, status indicators. |
| `{rounded.full}` | 9999px | Circular status dots (8px × 8px). |

## Components

### Navigation

**`nav-bar`** — The sticky top navigation bar.
- Background `{colors.canvas}`, text `{colors.ink}`, height 48px. 1px solid `{colors.hairline}` bottom border.
- Layout: Sponge wordmark left, primary links center (Docs / Guide / Benchmark), CTA + status right.

**`nav-link`** — Link items in nav.
- Transparent background, text `{colors.body}`, type `{typography.body-sm}`, padding `{spacing.xs} {spacing.sm}`, rounded `{rounded.sm}`. Hover shifts text to `{colors.ink}`.

### Buttons

**`button-primary`** — The teal CTA. The only filled button on the page.
- Background `{colors.primary}`, text `{colors.on-primary}` (dark, not white), type `{typography.button-md}`, padding `{spacing.sm} {spacing.lg}`, height 36px, rounded `{rounded.sm}` 4px. Tight.
- Pressed: `button-primary-pressed` shifts background to `{colors.primary-deep}`.

**`button-secondary`** — Outline alternative.
- Background `{colors.canvas-soft}`, text `{colors.ink}`, 1px `{colors.hairline}` border. Same typography and shape.

**`button-ghost`** — Text-only action.
- Transparent background, text `{colors.body}`, padding `{spacing.xs} {spacing.sm}`. Hover background `{colors.canvas-soft}`.

**`button-icon`** — Icon-only square button.
- Transparent, text `{colors.body}`, padding `{spacing.xs}`, rounded `{rounded.sm}`. Hover `{colors.canvas-soft}`.

### Cards

**`card-default`** — Standard content card.
- Background `{colors.canvas-soft}`, text `{colors.ink}`, 1px solid `{colors.hairline}`, padding `{spacing.lg}`, rounded `{rounded.md}`.

**`card-raised`** — Emphasized card (featured tier, pinned item).
- Background `{colors.canvas-raised}`, 1px `{colors.hairline-strong}` border, otherwise same as `card-default`.

**`card-stat`** — Metric display card. Hosts a DM Mono stat value + an uppercase caption-mono label.
- Same chrome as `card-default`. Value in `{typography.stat-xl}`, label in `{typography.caption-mono}`. Optionally colored via `{colors.savings}` for positive metrics.

### Terminal & Code

**`terminal-block`** — The signature content container. A dark terminal window showing CLI interaction.
- Background `{colors.canvas}`, 1px `{colors.hairline}` border, padding `{spacing.md}`, rounded `{rounded.sm}`. No title bar — just the raw terminal surface.
- Internal: `terminal-line` for command prompts (prompt character in `{colors.primary}`), `terminal-output` for command results (in `{colors.mute}` / `{typography.code-sm}`).

**`code-block`** — Standalone code snippet (YAML config, JSON output, Python example).
- Same chrome as `terminal-block` but without prompt decoration.

### Cost & Savings Displays

**`savings-badge`** — Compact pill showing a savings percentage or cost-reduction metric.
- Background `{colors.savings-soft}`, text `{colors.savings}` in `{typography.caption-mono}`, padding `{spacing.xxs} {spacing.sm}`, rounded `{rounded.pill}`. Example: "−73% TOKENS".

**`cost-bar`** — Thin horizontal progress bar for budget consumption.
- Background `{colors.canvas-soft}`, height 4px, rounded `{rounded.xs}`.
- Fill segments: `cost-bar-fill-low` (green), `cost-bar-fill-med` (amber), `cost-bar-fill-high` (red). Segments are 4px tall, rounded `{rounded.xs}`.

**`metric-row`** — Inline label-value pair for cost breakdowns.
- Transparent background, bottom border `{colors.hairline}`, padding `{spacing.sm} 0`. Label in `{typography.body-sm}`, value in `{typography.stat-md}` (right-aligned, DM Mono).

### Status Indicators

**`status-dot-success`** — Green dot, 8px × 8px, `{rounded.full}`.
**`status-dot-warning`** — Amber dot.
**`status-dot-error`** — Red dot.
**`status-dot-idle`** — Muted gray dot.

Used inline next to labels: "● Cache: 94% hit rate", "● Agent: idle".

### Agent Step Timeline

**`timeline-step`** — Vertical step indicator for agent workflow visualization.
- Transparent background, 2px solid `{colors.hairline}` left border, padding `{spacing.sm} {spacing.md}`. Step label in `{typography.body-sm}`, cost annotation in `{typography.caption-mono}` (right-aligned).

**`timeline-step-active`** — Same, with left border shifted to `{colors.primary}` (teal). Indicates the currently-executing agent step.

**`timeline-step-completed`** — Same, with left border shifted to `{colors.success}` (green). Indicates a completed step.

### Tags & Pills

**`pill-tag`** — Neutral pill for categories, labels, metadata.
- Background `{colors.canvas-soft}`, text `{colors.body}`, type `{typography.caption}`, rounded `{rounded.pill}`, padding `{spacing.xxs} {spacing.sm}`.

**`pill-tag-accent`** — Accented pill for featured/active tags.
- Background `{colors.savings-soft}`, text `{colors.savings}`, type `{typography.caption-mono}`, otherwise same shape.

### Inputs

**`text-input`** — Text input field.
- Background `{colors.canvas}`, text `{colors.ink}`, 1px `{colors.hairline}` border, type `{typography.code}`, padding `{spacing.sm} {spacing.md}`, height 36px, rounded `{rounded.sm}`.
- Focus: border shifts to `{colors.primary}`.

### Sections

**`hero-band`** — The top-of-page hero.
- Background `{colors.canvas}`, text `{colors.ink}`, headline in `{typography.display-xl}`, padding `{spacing.5xl} {spacing.xl}`.

**`content-band`** — Standard content section.
- Background `{colors.canvas}`, section head in `{typography.display-md}`, padding `{spacing.4xl} {spacing.xl}`.

**`content-band-alt`** — Alternating content section on `canvas-soft` for visual rhythm.
- Background `{colors.canvas-soft}`, otherwise same.

**`footer`** — Site footer.
- Background `{colors.canvas}`, text `{colors.mute}`, type `{typography.body-sm}`, padding `{spacing.3xl} {spacing.xl}`, 1px `{colors.hairline}` top border.

### Data Display

**`data-table`** — Structured data container.
- Background `{colors.canvas-soft}`, rounded `{rounded.md}`, 1px `{colors.hairline}` border.

**`data-table-header`** — Table header row.
- Background `{colors.canvas-raised}`, text `{colors.body-strong}` in `{typography.caption-mono}`, padding `{spacing.sm} {spacing.md}`, bottom border `{colors.hairline-strong}`.

**`data-table-cell`** — Table body cell.
- Transparent, text `{colors.ink}` in `{typography.body-sm}`, padding `{spacing.sm} {spacing.md}`, bottom border `{colors.hairline}`.

### Notifications

**`toast`** — Toast notification.
- Background `{colors.canvas-raised}`, 1px `{colors.hairline}` border, padding `{spacing.sm} {spacing.md}`, rounded `{rounded.md}`.
- Variants: `toast-success` / `toast-warning` / `toast-error` — each adds a 3px left border in the corresponding semantic color.

### Modal

**`modal-overlay`** — Semi-transparent backdrop.
**`modal-card`** — Dialog surface.
- Background `{colors.canvas-raised}`, 1px `{colors.hairline}` border, padding `{spacing.xl}`, rounded `{rounded.lg}`.

### Empty State

**`empty-state`** — Placeholder for empty content areas.
- Background `{colors.canvas-soft}`, text `{colors.mute}`, dashed 1px `{colors.hairline}` border, padding `{spacing.3xl}`, rounded `{rounded.md}`.

## Do's and Don'ts

### Do
- Reserve `{colors.primary}` teal for the primary CTA and savings-positive metrics. One accent, used scarcely.
- Render every stat, metric, and cost figure in DM Mono. The typeface signals measurement.
- Use `{rounded.sm}` 4px for all buttons and terminal blocks. Tight radii are the brand signature.
- Keep the dark canvas commitment. There is no light mode — the brand lives in the terminal.
- Use surface-contrast (canvas → canvas-soft → canvas-raised) for elevation. Never drop shadows.
- Set section labels in `{typography.caption-mono}` — 11px uppercase DM Mono at 0.5px tracking.
- Display headlines at weight 500 max. The brand reads as engineered, not billboard.

### Don't
- Don't introduce a second chromatic accent. Teal is the only one.
- Don't use pure white text (`#ffffff`) — `{colors.ink}` (`#e4e4e7`) is the ceiling. Pure white reads as blown-out on dark.
- Don't use white text on the teal button — the brand uses dark `{colors.on-primary}` on teal.
- Don't render display at weight 600+. The brand caps at 500.
- Don't add gradients, atmospheric backdrops, or decorative overlays. The dark canvas IS the decoration.
- Don't use pill-shaped CTAs. The button radius stays at `{rounded.sm}` 4px.
- Don't use drop shadows. Hairlines + surface contrast carry elevation.
- Don't use DM Mono for body text or Inter for code — the role separation is strict.
- Don't saturate the cost-level colors. They should render as thin 4px bars or small dots, never as filled backgrounds.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| Mobile | < 640px | Hero display drops 48→28px; stat cards 1-up; terminal mockups single-pane; nav hamburger. |
| Tablet | 640–1024px | Stat cards 2-up; terminal mockups simplified; nav horizontal but condensed. |
| Desktop | 1024–1280px | Full layout: 3-up stat cards, 2-column terminal splits, full nav. |
| Wide | ≥ 1280px | Content caps at 1100px; bands stretch edge-to-edge in color but content holds width. |

### Touch Targets
- Buttons render at 36px height minimum — meets WCAG AA.
- Form inputs at 36px height.
- Status dots (8px) are decorative only; interactive elements are ≥ 36px.

### Collapsing Strategy
- Nav: full link row at desktop, hamburger at mobile.
- Stat cards: 3-up → 2-up → 1-up.
- Terminal mockups: 2-column split at desktop, single pane at mobile.
- Agent timeline: 320px sidebar at desktop, full-width stacked at mobile.

## Agent Prompt Guide

### Quick Color Reference
```
Background: #1e1e24 (dark canvas)
Card: #262630 (canvas-soft)
Raised: #2e2e38 (canvas-raised)
Text: #e4e4e7 (ink) / #a1a1aa (body) / #71717a (mute)
Teal accent: #2dd4bf (use ~2% of surface)
Borders: #3f3f46 (hairline)
```

### Ready-to-Use Prompts

**"Build a landing page using the Sponge DESIGN.md."**
> Use `{colors.canvas}` #1e1e24 as the page background. Set all body text in Inter. Render the hero headline at 48px Inter weight 500 with -1.2px letter-spacing. Use DM Mono for all stats, metrics, and code surfaces. The only accent color is `{colors.primary}` #2dd4bf — use it for the primary CTA button and savings-positive badges only. Cards use `{colors.canvas-soft}` with 1px hairline borders. No drop shadows, no gradients. Buttons are 4px border-radius, 36px height.

**"Build a cost dashboard using the Sponge DESIGN.md."**
> Use `card-stat` for top-level metrics (DM Mono stat + uppercase caption-mono label). Use `cost-bar` components (4px thin bars) for budget consumption indicators with `cost-low`/`cost-med`/`cost-high` fill colors. Use `data-table` for detailed breakdown rows with `caption-mono` headers. Use `savings-badge` pills for percentage savings. Background `{colors.canvas}`, cards on `{colors.canvas-soft}`.

**"Build a terminal-style CLI reference page."**
> Use `terminal-block` as the primary content container. Command prompts in `{colors.primary}`, output in `{colors.mute}`. All text in DM Mono. Background `{colors.canvas}`. Use `code-block` for config file examples (YAML/TOML). No decorative elements — the terminal surfaces ARE the design.

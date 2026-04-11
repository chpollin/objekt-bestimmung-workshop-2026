# Design-Spezifikation

UI-Referenz für das Browser-Tool. Stand: M3, Inkrement A.

## Designprinzipien

- **Funktional, nicht dekorativ.** Werkzeug für Fachleute, kein Marketing.
- **Hoher Kontrast, große Schrift.** Beamer-tauglich, Workshop-Setting.
- **Bilder dominieren.** Text ist Service.
- **Status sofort sichtbar.** Farbe + Icon, nie nur Farbe (Accessibility).
- **Kein Framework, kein Build.** Vanilla HTML + CSS + JS, direkt aus dem Repo bedienbar.

## Farbpalette

CSS Custom Properties in `style.css` unter `:root`.

| Token | Hex | Verwendung |
|---|---|---|
| `--bg` | `#FFFFFF` | Haupthintergrund |
| `--bg-alt` | `#F5F5F5` | Sidebar, Karten |
| `--bg-panel` | `#FAFAFA` | Detail-Panel |
| `--border` | `#E0E0E0` | Trennlinien |
| `--text` | `#333333` | Body-Text |
| `--text-mute` | `#666666` | Sekundärtext |
| `--accent` | `#009B91` | Teal, Aktionen, Active-States |
| `--accent-strong` | `#00766F` | Hover/Press |
| `--ai-blind` | `#7B61FF` | KI-Blind-Badge |
| `--ai-enriched` | `#3D8BFF` | KI-Enriched-Badge |
| `--ai-judge` | `#1A3A5F` | Judge-Badge (dunkel = stärkere Autorität) |
| `--ground-truth` | `#5B7C99` | Original-Badge |
| `--ok` | `#2E8540` | freigegeben (🟢) |
| `--warn` | `#E08A00` | ungeprüft (🟡) |
| `--err` | `#C8362D` | Konflikt (🔴) |
| `--mute` | `#9E9E9E` | keine KI-Daten (⚪) |

## Typografie

- System-Font-Stack: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`
- Skala: 14 / 16 / 18 / 22 / 28 / 36 px
- Body 16 px, Filterlabels 14 px, Detail-Headings 22 px, Galerie-Titel 18 px

## Layout (Overview)

```
┌───────────────────────────────────────────────────────────────────────┐
│ HEADER  Workshop-Demo: Objekt-Bestimmung   [Export] [GitHub] [About]  │
├────────────┬──────────────────────────────────────────────────────────┤
│ FILTER     │ OVERVIEW · 246 Objekte · 20 Bereiche · 228 Kategorien    │
│            ├──────────────────────────────────────────────────────────┤
│ Suche      │                                                          │
│ [_______]  │  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                     │
│            │  │🟡 │ │🟡 │ │🟢 │ │⚪ │ │🔴 │ │🟡 │                     │
│ Thesaurus  │  └───┘ └───┘ └───┘ └───┘ └───┘ └───┘                     │
│ ▼ Alltag   │   Beutel  Fächer ...                                     │
│ ▶ Handwerk │                                                          │
│ ▶ Religion │  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                     │
│            │  │   │ │   │ │   │ │   │ │   │ │   │                     │
│ Status     │  └───┘ └───┘ └───┘ └───┘ └───┘ └───┘                     │
│ ☑ ungeprüft│                                                          │
│ ☑ Konflikt │                                                          │
│ ☐ freigeg. │                                                          │
└────────────┴──────────────────────────────────────────────────────────┘
```

## Layout (Detail-Drawer)

```
┌───────────────────────────────────────────────────────────────────────┐
│ ← zurück   VK-20440 · Beutel                              [×]         │
├──────────────────────────────┬────────────────────────────────────────┤
│                              │ ◉ ORIGINAL                             │
│                              │ Term: Accessoires                      │
│                              │ Material: Stoff, vernäht               │
│       [GROSSES FOTO]         │ Maße: 17 × 14,5 cm                     │
│                              │ Datierung: —                           │
│                              │                                        │
│                              │ ◉ KI BLIND  [gemini-3.1-flash-lite]    │
│                              │ Term: Accessoires ✓                    │
│                              │ Beschreibung: …                        │
│                              │                                        │
│                              │ ◉ KI ERWEITERT                         │
│                              │ Term: Accessoires ✓                    │
│                              │ Beschreibung: …                        │
│                              │                                        │
│                              │ ◉ JUDGE  [gemini-3.1-pro]              │
│                              │ Verdict: enriched_better               │
│                              │ Begründung: …                          │
├──────────────────────────────┴────────────────────────────────────────┤
│ ✎ EXPERTEN-FREIGABE                                                   │
│ Term:        [Accessoires             ▼]                              │
│ Beschreibung:[________________________________________________]       │
│ Material:    [________________________________]                       │
│ Technik:     [________________________________]                       │
│ Datierung:   [________________________________]                       │
│ Anmerkung:   [________________________________]                       │
│                                                                       │
│   [Verwerfen]  [aus 'blind']  [aus 'erweitert']  [Speichern ✓]        │
└───────────────────────────────────────────────────────────────────────┘
```

## Komponenten (BEM-light)

- `.app-header` — oben, Logo + Titel + Export-Button
- `.filter-sidebar` — links, Filter-Controls
- `.thesaurus-tree`, `.thesaurus-tree__node` — collapsible Tree
- `.gallery` — Grid-Container
- `.gallery__card` — einzelne Objektkarte
- `.status-pill` — Statusanzeige, kombiniert Icon + Farbe
- `.detail-drawer` — Slide-over-Panel
- `.variant-card` — eine Variante im Drawer
- `.variant-card--original` / `--ai-blind` / `--ai-enriched` / `--ai-judge` / `--expert`
- `.editor-form` — das editierbare Experten-Formular

## Interaktion

- Filter wirken **sofort**, kein „Anwenden"-Button. Freitext-Input ist debounced 150 ms.
- Galerie braucht kein virtuelles Scrollen (246 Items sind unkritisch), aber Bilder sind `loading="lazy"`.
- Drawer slide-in mit 200 ms Transition, ESC schließt.
- Pfeil-Tasten ← und → navigieren im Drawer zwischen den aktuell gefilterten Objekten.
- Hover auf Gallery-Card: leichte Elevation (shadow), Cursor Pointer.

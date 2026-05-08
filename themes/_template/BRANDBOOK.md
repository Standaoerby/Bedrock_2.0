# Bedrock Theme Brandbook

How to design a theme that fits Bedrock 2.0 — what the system gives you,
how to use it, and the pitfalls that bit us during the rewrite. Read
`README.md` next to this file for the dry schema reference; this
document explains *why* the schema is shaped the way it is.

---

## 1. Context: what is Bedrock 2.0?

A always-on touchscreen panel for a kid's bedroom (Raspberry Pi 5,
1024×600 fixed display, no DPI scaling). Six screens cycle through:

| Screen | Purpose |
|---|---|
| **Home** | Big clock, date, next alarm, weather glance, scrolling notice. |
| **Alarm** | Configure morning alarm: time picker, weekday repeat, ringtone, fade-in. |
| **School** (Schedule) | Today / Tomorrow lessons, weekly grid mode. |
| **Climate** (Weather) | Forecast vs. room sensors, weekly forecast. |
| **Pigs** | Pet care: Water / Food / Cleaning progress bars. |
| **Settings** | Theme + dark mode toggle + user name + birthday. |

A theme has to look right on **all six** in **both light and dark**.
The user picks light/dark manually or lets `auto_dark_mode` flip with
sunrise/sunset.

---

## 2. Design philosophy

Three principles, in priority order.

### 2.1 Glanceable

The user is across the room, half-asleep, or 6 years old. Big text
beats small text. High contrast beats subtle. A single look should
communicate state — "alarm is ON, weather will be 12 °C in 5 hours,
it's Tuesday."

→ Translate: prefer larger `font_sizes`, saturated `colors.active`,
strong `font_highlight` on section titles.

### 2.2 Unobtrusive when idle

The panel sits in a kid's room. It shouldn't strobe, scroll, blink.
The clock and ambient temp/CO₂ are the default view; everything else
is on demand.

→ Translate: muted backgrounds, soft `panel_bg` alpha, marquee speed
already tuned in code. Don't crank `font_action` saturation higher
than the canonical scale.

### 2.3 Decorative, but text wins

Themes can ship per-screen artwork (`overlay_images`) — Minecraft
mobs, illustrations, etc. The artwork has to *yield* to text on the
panels above it. We learned this the hard way: a wolf overlay through
0.25-alpha panels made "Room Sensors" unreadable.

→ Translate: keep `overlay_opacity` at or below `0.5`; raise
`panel_bg` alpha until you can read every section title without
squinting.

---

## 3. The grid

Everything is on **8 dp**. `theme.layout.grid_unit = 8`.

```
4   8   16   24    ← padding/spacing scale (xs/sm/md/lg)
32  48  64        ← widget heights (sm/md/lg)
```

When you write KV, you don't reach for `"12dp"` — you reach for
`app.ui_metrics["padding_md"]`. The harness loads the layout dict
from your theme into `app.ui_metrics`, runs every value through
`dp()`, and KV reads it as a regular DictProperty. One source of
truth, theme-switchable, density-aware.

If a layout calls for *almost* 16 dp, force the choice: round to 16
or to 24. The visible benefit of one consistent rhythm beats the
"perfect" custom value every time.

### Where each tier earns its keep

- **xs (4 dp)** — between tightly-coupled rows (sensor list, calendar
  cells). Avoid for general spacing — too tight on touch.
- **sm (8 dp)** — between unrelated widgets in the same panel (label
  → input). Default for `spacing` inside forms.
- **md (16 dp)** — panel padding. Between sections of a screen. Your
  default for "I want some air."
- **lg (24 dp)** — between major sibling sections in a busy panel
  (Pigs left column has 3 sub-sections separated by `spacing_lg`).

### Heights

- **widget_height_sm (32)** — compact rows that show data, not
  buttons (sensor row, calendar day cell).
- **widget_height_md (48)** — touch targets. Buttons, spinners,
  inputs, form rows. **This is the default.** Stick with it unless
  you have a reason.
- **widget_height_lg (64)** — section titles (so 28–30 sp text isn't
  cropped at the top of the cell), the Save Settings hero button.

A common rookie mistake: setting a heading row to `widget_height_md`
because "it's just a label." A 30 sp label vertically centered in a
48 dp cell will be clipped on themes with larger fonts (`clean`'s
`section_title` is 30 sp; `widget_height_lg` is the right choice).

---

## 4. Typography

Canonical sizes (`tiny → huge`) + three **semantic aliases**
(`section_title`, `field_label`, `metric_value`). Aliases let you
tune meaning-driven typography per theme without grepping every KV
file.

| Role | Used in | When to override |
|---|---|---|
| `tiny` | weekly schedule day cells | Almost never. |
| `small` | Tomorrow lessons, secondary labels | Bigger if the tiny size is unreadable on your font. |
| `default` | body text, fallback | Sets the "feel" of the typography — bump it 1–2 sp on a humanist font, drop it 1–2 sp on pixel fonts. |
| `medium` | inline labels, button text | Tied to `field_label` by default. |
| `large` | section sub-headings, big numbers | Tied to `section_title` and to some hero values (current temp). |
| `xlarge` | currently unused, reserved for hero metrics | — |
| `huge` | the Home clock | This is where two themes differ most. Minecraft is 120 sp; Clean is 200 sp because Roboto reads thinner than Minecraftia at the same size. |
| **`section_title`** | "Weather Forecast", "Room Sensors", "Today: …" | Equal to `large` by default. Differentiate if your section titles want their own weight. |
| **`field_label`** | "Theme:", "Username:", weekday toggles | Equal to `medium`. |
| **`metric_value`** | sensor values, weather values, schedule rows | Equal to `default`. Keep readable on a moving panel viewed from the doorway. |

### Font choice

Register fonts in `main.py` via `LabelBase.register("Name",
fn_regular="path.ttf")`. The name in `theme.json["font_name"]` must
match the registered name exactly.

We register two fallbacks at startup:

- **Minecraftia** (`assets/fonts/Minecraftia-Regular.ttf`) — pixel
  font, used by the Minecraft theme.
- **Symbols** (`assets/fonts/DejaVuSans.ttf`) — fallback for arrows
  and geometric glyphs Roboto/Minecraftia don't have. Used by the
  weather trend arrow ▲▼ on Home; KV pins `font_name: "Symbols"` on
  that one widget.

If your custom font lacks Cyrillic, IPA, or arrow glyphs, *don't*
work around it in the font — the kid sees the panel in Russian and
English and the trend arrow is a unicode geometric. Either pick a
font with full coverage or pin `Symbols` on the affected widgets.

---

## 5. Color system

Every color in `theme.json["colors"]` is **role-based**, not
appearance-based. KV writes `color_role: "font_highlight"`, not
`color: [1, 0.5, 0, 1]`. This is what makes light/dark switching work
without re-binding every label.

### 5.1 Text colors (`font_*`)

| Role | Use | Light hint | Dark hint |
|---|---|---|---|
| `font_default` | body text | near-black or deep slate | near-white |
| `font_secondary` | helper / de-emphasized | 60–70 % luminance of default | same |
| `font_highlight` | section titles, accents | strong saturated hue (orange in our themes) | usually warmer in dark mode for readability |
| `font_action` | CTA text | a green-ish or accent color | brighter version |
| `font_disabled` | greyed-out | low-saturation grey | low-saturation grey, slightly lighter than disabled-bg |

### 5.2 State colors

`active`, `inactive`, `semi_active` — used by toggles, the alarm
ON/OFF button, the day-of-week chips.

`warning` (amber), `error` (red), `primary` (your accent) round it out.

Convention: in **light** mode `active` is a deeper saturated green;
in **dark** mode it's a lighter green so it pops on the dark panel.
Don't use the *same* RGBA in both — what reads "alive" on cream looks
muddy on charcoal.

### 5.3 Domain-specific

- `trend_up`, `trend_down` — weather arrows on Home. Convention is
  red/orange = up (warming), blue = down (cooling).
- `weekend` (red-ish), `weekday` (blue-ish) — schedule day labels.
- `bar_water` (blue), `bar_food` (orange), `bar_clean` (green) —
  Pigs progress bars. These translate "what is this measuring"
  visually so the kid doesn't read the label.

### 5.4 Chrome backgrounds

- `button_bg` / `button_bg_active` — `ThemedButton` flat fill. In
  dark themes keep this *darker* than `font_default`. We had a bug
  where Minecraft Light's button used a near-white default and the
  cream `font_default` text disappeared on it.
- `input_bg` — `ThemedTextInput` background. Same rule: in dark mode
  this **must** be darker than `font_default`, otherwise typing
  produces invisible text. Our `clean/dark` uses `[0.12, 0.15, 0.2]`.

### 5.5 Shadow

`shadow_light` and `shadow_dark` are the drop shadows for the Home
clock. The widget picks `shadow_light` when `app.theme_mode == "light"`
(typical: dark color with low alpha → cast shadow on pale bg) and
`shadow_dark` in dark mode (typical: white color with low alpha →
faint halo on dark bg).

---

## 6. Component anatomy

### 6.1 ThemedPanel

A rounded BoxLayout that paints a `panel_bg` rectangle behind its
content. Use as the wrapper for any logical section (Forecast,
Sensors, Today's lessons, etc).

```kv
ThemedPanel:
    orientation: "vertical"
    padding: app.ui_metrics["padding_md"]
    spacing: app.ui_metrics["spacing_xs"]

    ThemedLabel:
        text: "Section title"
        size_role: "section_title"
        color_role: "font_highlight"
        size_hint_y: None
        height: app.ui_metrics["widget_height_lg"]
        halign: "left"
        valign: "middle"
        text_size: self.size

    # ... rows
```

Tunable in theme: `panel_bg` (RGBA), `panel_radius` (corner radius).

### 6.2 ThemedLabel / ThemedButton / ThemedSpinner / ThemedTextInput / ThemedToggleButton

Drop-in replacements for the corresponding Kivy widget. They re-paint
on theme switch. Two opt-in properties:

- `color_role` — which `colors[...]` entry to apply. Empty string =
  don't override (KV's per-instance `color:` wins).
- `size_role` — which `font_sizes[...]` entry to apply. Empty = don't
  override.

The Toggle versions and the Spinner additionally pick up
`button_bg` / `active` / `inactive` for their fill states.

### 6.3 ScreenOverlay

The decorative full-bleed PNG behind a screen's panels. Driven by
`overlay_images.<page_key>` and dimmed globally by `overlay_opacity`.

Tip: design overlays with text-safe zones — a strip of mid-tone in
the middle of the image where panels will sit reads cleaner than a
high-contrast subject directly behind a section title.

### 6.4 OverflowColumn

Vertical container that **becomes scrollable when content
overflows**. Drop-in for `BoxLayout(orientation: "vertical")`.

```kv
OverflowColumn:
    spacing: app.ui_metrics["spacing_sm"]
    padding: app.ui_metrics["padding_md"]

    # Children added here go into an inner BoxLayout. If the sum of
    # their heights stays inside the OverflowColumn's height, this
    # behaves identically to a plain BoxLayout. If they overflow, a
    # thin scrollbar appears and the content is scrollable.
    ThemedLabel: …
    ThemedLabel: …
```

When in doubt about whether content might exceed view (long
schedules, sensor lists, settings forms on themes with bigger
fonts) — use `OverflowColumn`. Free safety net.

### 6.5 ShadowLabel + clock

The Home clock is two stacked widgets: a `ShadowLabel` (offset
shadow) and a `ThemedLabel` on top. Both read `font_sizes.huge`.
Keep both font sizes in sync — they're driven by the same theme
key, so they stay in sync automatically.

### 6.6 MarqueeLabel

Bottom-of-Home scrolling notification strip. Width is intentionally
wider than visible — text scrolls horizontally. Don't tune its
height via `widget_height_*`; it's a typographic dimension tied to
the line geometry of the chosen font (currently hardcoded `"56dp"`).

---

## 7. Mode pairs (light / dark)

A theme is **two** files: `themes/<name>/light/theme.json` +
`themes/<name>/dark/theme.json`. The folder name (not the `mode` key
inside) decides which gets loaded.

What changes between modes:

| Token | Light | Dark |
|---|---|---|
| `font_color` / `font_default` | dark slate / near-black | near-white |
| `font_secondary` | mid-grey | mid-grey, slightly lighter |
| `font_highlight` | saturated warm (orange/red) | warmer cream / yellow — needs more luminance to read on dark bg |
| `panel_bg` | usually opaque or near-opaque cream / white | usually opaque or near-opaque dark blue / charcoal |
| `button_bg` | white-ish | dark grey |
| `input_bg` | white | dark blue / charcoal — must contrast with `font_default` |
| `background_image` | day landscape / paper texture | night landscape / dark texture |
| `shadow_*` | unchanged across modes (shadow_light is for light mode, etc) | — |

Layout, font sizes, font name **don't** change between light and dark
of the same theme. Keep them identical so screen layouts don't shift
when the user toggles dark mode.

---

## 8. Reference themes

### 8.1 Minecraft (artistic)

What it demonstrates:

- A **pixel font** (Minecraftia) — bold geometric glyphs that read
  well at low size; `default` is a small 18 sp.
- **Per-screen overlay PNGs** — wolves on Climate, sheep on Home,
  pigs on Pigs. Decoration that sells the theme.
- **Asymmetric `panel_bg`** — semi-transparent black so the overlay
  artwork still reads through panels at low intensity.
- A `font_highlight` bright enough (`[1, 1, 0.7, 1]` in dark mode)
  to lift section titles off the artwork.

### 8.2 Clean (modern)

What it demonstrates:

- A **humanist font** (Roboto, default Kivy) — readable at larger
  sizes. `default` is bumped to 20 sp because Roboto reads thinner
  than Minecraftia at the same nominal size.
- **No overlays** — `overlay_images.*` are all `""`. Background is a
  flat texture; the design relies on typography and color, not
  decoration.
- **High `panel_bg` luminance** in light mode (cream `[1, 1, 1, 0.55]`)
  and **near-opaque dark** in dark mode — panels feel like cards.
- A larger clock (`huge: 200sp`) compensating for Roboto's lighter
  visual weight at the same sp value.

Both themes share the **same `layout` dict** and **same
`overlay_opacity` default** — they only diverge on font, colors, and
artwork. That's the cleanest demonstration of the role-based system.

---

## 9. Step-by-step: creating a new theme

Goal: a `forest` theme with green palette and a hand-drawn forest
overlay.

### Step 1 — Scaffold

```bash
cp -r themes/_template themes/forest
mkdir themes/forest/light themes/forest/dark
mv themes/forest/theme.json themes/forest/light/theme.json
cp themes/forest/light/theme.json themes/forest/dark/theme.json
```

### Step 2 — Pick a font

If you're sticking with Roboto, the `font_name` key stays as-is.
If you're shipping a custom TTF:

1. Drop `assets/fonts/Lora-Regular.ttf` (or whatever).
2. In `main.py`, after the existing `LabelBase.register` calls:
   ```python
   LabelBase.register(name="Lora", fn_regular="assets/fonts/Lora-Regular.ttf")
   ```
3. In both `theme.json` files: `"font_name": "Lora"`.

### Step 3 — Set the palette

Edit `colors` in `forest/light/theme.json`. Start by changing
`primary` and `font_highlight` to your hero hue — the rest can stay
on defaults until you have a feel for the result.

```json
"colors": {
  "primary":        [0.20, 0.55, 0.30, 1],
  "font_highlight": [0.45, 0.65, 0.20, 1],
  "active":         [0.30, 0.70, 0.35, 1],
  "weekday":        [0.30, 0.55, 0.40, 1],
  ...
}
```

Then mirror in `dark/theme.json` with the **same hue** but lifted
luminance:

```json
"font_highlight": [0.65, 0.85, 0.35, 1],
"active":         [0.45, 0.85, 0.50, 1],
```

### Step 4 — Authoring graphics

`background.png` — `1024×600`, full-bleed. PNG-24 with no alpha is
fine; if you want vignetting just bake it in.

Per-screen overlays (`overlay_<screen>.png`) — same `1024×600`. PNG
with alpha. Place subjects so a horizontal panel band across the
middle has a calm tone — that's where the panels sit and where text
needs to read clearly.

Drop them under `themes/forest/light/` and `dark/` and reference them
in `theme.json`:

```json
"background_image": "themes/forest/light/background.png",
"overlay_images": {
  "home":     "themes/forest/light/overlay_home.png",
  "alarm":    "themes/forest/light/overlay_alarm.png",
  ...
}
```

If you don't ship overlays for some screens, leave them as `""`.
That screen will render with just the background — which is fine.

### Step 5 — Tune `overlay_opacity` and `panel_bg`

Run the app, switch to your theme, cycle through screens. Adjust:

- If section titles are hard to read against the artwork, **raise
  `panel_bg` alpha** (more opaque panel) or **lower
  `overlay_opacity`** (dimmer art).
- Default `overlay_opacity = 0.5` is a sweet spot — go below `0.3`
  only if your artwork is noisy.

**Coupling rule (tested 2026-05-08 on minecraft + clean):** the two
knobs are not independent. Picking high `overlay_opacity` without
matching `panel_bg` alpha makes Settings (the panel-heaviest screen)
unreadable when overlay artwork has sharp light figures on dark areas.
Pair them like this:

| `overlay_opacity` | dark `panel_bg[3]` | light `panel_bg[3]` |
|---|---|---|
| 0.3–0.5 | 0.75 | 0.55 |
| 0.6–0.8 | 0.85 | 0.65 |
| 0.9–1.0 | 0.95 | 0.75 |

Drop a row if you ship pastel/low-contrast artwork; bump a row if
the overlay has high-saturation accents (bright greens, oranges).

### Step 6 — Walk through the validation checklist (§ 11).

### Step 7 — Add to release.

That's it. The Settings → Theme spinner lists `themes/*/` folders,
so the moment your `forest/` directory exists with both modes, the
user can switch to it.

---

## 10. Tunable knobs at a glance

When a designer says "make it more X," reach for:

| Want | Knob |
|---|---|
| Brighter / livelier | Bump `font_highlight` saturation, `colors.active`. |
| Calmer | Drop saturation on `font_secondary`, raise `panel_bg` alpha. |
| Bigger text | Bump every `font_sizes` entry by 1–2 sp. |
| More breathing room | `spacing_md` / `padding_md` already at 16; jump panel padding to `padding_lg` (24). |
| Tighter | `padding_xs` / `spacing_xs` (4 each) — but watch touch targets. |
| Stronger artwork | Raise `overlay_opacity` toward 1.0 — and raise `panel_bg[3]` in lockstep (see Step 5 coupling table). |
| Quieter artwork | Drop `overlay_opacity` toward 0.3. |
| Snappier touch feel | Bump `button_bg_active` away from `button_bg` so the press registers. |

---

## 11. Validation checklist

Before declaring a theme "done":

**Per mode (light AND dark separately):**

- [ ] Cycle all six screens. No content overflows past panel edges.
- [ ] Section titles are fully visible (not clipped at top — the
      Bedrock 1.0 Climate bug).
- [ ] Sensor/metric values read without squinting from 2 m away.
- [ ] Buttons have visible borders or fills (no invisible buttons
      on top of similarly-coloured panels).
- [ ] TextInputs contrast: typed text is readable inside the input.
- [ ] Toggle states: ON green/active is unmistakably different from
      OFF grey/inactive.
- [ ] Trend arrows on Home are visible (font fallback works).
- [ ] Marquee on Home keeps scrolling, no clipping.

**Per theme (covers both modes):**

- [ ] Light ↔ dark switch works without restarting — driven by
      AutoThemeService (toggle `auto_theme_strategy` in user.json or
      via admin web UI; Settings page no longer carries a manual
      Dark Mode checkbox).
- [ ] Saved choice persists across app restart.
- [ ] All `overlay_images` exist on disk if not `""`.
- [ ] `background_image` exists on disk for both modes.
- [ ] `font_name` matches a registered font name in `main.py`.
- [ ] No raw `[r, g, b, a]` arrays sneaked into KV — everything
      should go through `color_role` or `theme_config.get(...)`.

**Stretch:**

- [ ] Overlay PNGs total < 5 MB per mode (Pi has fast SSD now, but
      RAM caches every texture and the panel restarts mid-day).
- [ ] Clock + shadow are aligned (small `pos_hint` offset on the
      shadow, not a different `huge` value).

---

## 12. Common gotchas

**Hardcoded `dp` in KV.** If you write `"16dp"` in KV, your theme
can't change it. Always go through `app.ui_metrics["padding_md"]`.

**`text_size: self.size` + tall fonts.** When `text_size` matches
the label height and the font is right at the height limit,
glyphs get clipped at the top. Use `widget_height_lg` for section
titles so 30 sp text has breathing room, *not* `widget_height_md`.

**Font without `▲▼`.** Roboto and Minecraftia don't have geometric
arrows. Pin `font_name: "Symbols"` on widgets that need them, or
ship a font with coverage.

**Same `panel_bg` for both modes.** The cream that works for light
becomes mud on dark. Always pick mode-specific panel backgrounds.

**Stale `overlay_opacity`.** If you copy from an older theme that
predates the knob, you might omit it. The default `0.5` kicks in,
which is usually fine — but explicitly setting it makes the
intent clear.

**Bumping `overlay_opacity` without panel alpha.** Cranking
`overlay_opacity` to 1.0 alone makes panel-heavy screens (Settings)
bleed overlay through panel transparency. Always bump `panel_bg[3]`
together — see the coupling table in Step 5. Symptom: in dark mode,
overlay characters' saturated pixels (green zombies, orange skin)
become visible through panel rectangles right where labels sit.

**Reserved palette slots.** Three roles are present in every theme
but currently consumed nowhere in the code: `font_action`, `warning`,
`button_bg_active`. They're kept for parity (so adding the wiring
later doesn't require touching every theme) — but if you re-skin
them, expect no visual change until something starts reading them.

**Legacy size keys in old KV.** `pages/{alarm,schedule,weather,pigs}.kv`
still pull a few sizing tokens via `app.theme_config.get("grid_unit",
"32dp")`, `widget_font_size`, `widget_heights.button` etc. Those keys
are *not* defined in `_template/theme.json`, so KV always falls back
to the hardcoded literals — meaning a new theme can't override them.
Migration target: replace these with `app.ui_metrics["padding_md"]` /
`["widget_height_md"]` etc. (same way `home.kv` and `settings.kv`
already work). Until that's done, treat those tokens as off-limits
for theme tuning.

**Theme without a `dark/` folder.** AutoThemeService still calls
`apply_theme(theme, "dark")` if the strategy decides "dark" — and
the missing folder makes that load silently fail (load_theme_config
raises, caught in `apply_theme`, returns False). The panel sticks
in `light`. Ship both `light/` and `dark/` so auto-theme can swing
both ways.

**JSON without `_about`.** Future-you is going to wonder why the
panel is sage green. `_about` and `_comment_*` keys are ignored at
runtime — use them as a design-decision diary inside the theme
file.

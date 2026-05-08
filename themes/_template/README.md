# Theme schema reference

Everything Bedrock's UI reads from `theme.json` lives here. Use this folder
as a copy-paste starting point for a new theme.

## File layout

A theme is a folder under `themes/` with `light/` and `dark/` modes:

```
themes/
  <your-name>/
    light/
      theme.json           # required
      background.png       # optional, full-screen 1024x600
      menu_button.png      # optional, fits menu_button_size
      menu_button_active.png
      button.png           # optional, ThemedButton bg
      button_active.png
      overlay_<screen>.png # optional, one per screen (home/alarm/…)
    dark/
      theme.json
      …
```

Both `light` and `dark` are required even if you only ship one — the dark
mode toggle in Settings flips between the two and will fail if the file
isn't there. Easiest path: copy your light folder, tweak colors, save.

The theme is registered automatically the first time the user opens
Settings → Theme: the spinner enumerates `themes/*/` folders. No code
change needed to add a theme.

## Quick start

1. `cp -r themes/_template themes/<your-name>` (then duplicate into `light/dark`).
2. Open `theme.json` and set `name`, `mode`, `font_name`.
3. Edit `colors`, `font_sizes`, `panel_bg`, `panel_radius` for the look.
4. Drop in PNGs (background, overlays, menu buttons) under the right mode dir.
5. If using a custom font: drop the `.ttf` into `assets/fonts/` and register
   it in `main.py` via `LabelBase.register(name="MyFont", fn_regular="…")`.
   The `font_name` value in `theme.json` must match what you registered.
6. Restart the app. Pick the new theme from Settings → Theme.

`_comment_*` keys inside `theme.json` are ignored at runtime — they exist
because JSON has no comment syntax. Feel free to add your own.

## Required vs optional

**Required** (app crashes or renders badly if missing):
- `name`, `font_name`, `font_color`, `font_sizes`, `colors`, `layout`,
  `panel_bg`, `panel_radius`, `background_image`, `overlay_images`,
  `overlay_opacity`.

**Optional** (sensible default if missing):
- `mode` (informational only — actual mode is `app.theme_mode`)
- `menu_button_normal/_active`, `button_normal/_active` (empty `""` = flat)
- `menu_button_size/_padding/_font_size`
- `menu_selected_color`, `menu_unselected_color`
- Any individual `overlay_images.<screen>` (empty `""` hides the overlay)

## Schema

### Top level

| Key | Type | Used in | Notes |
|---|---|---|---|
| `name` | string | Settings spinner | Display name. |
| `mode` | string | informational | Match folder name (`"light"` / `"dark"`). |
| `font_name` | string | `classes/themed.py` | Must match a `LabelBase.register` name in `main.py`. |
| `font_color` | rgba | fallback | Default text color when `color_role` doesn't resolve. |
| `font_sizes` | dict | `classes/themed.py` | See *Font sizes* below. |
| `colors` | dict | `classes/themed.py`, KV | See *Color roles* below. |
| `layout` | dict | `app.ui_metrics`, KV | See *Layout tokens* below. |
| `panel_bg` | rgba | `ThemedPanel` | Rounded panel fill. Use alpha < 1.0 for translucency. |
| `panel_radius` | int (dp) | `ThemedPanel` | Corner radius. |
| `background_image` | path | `main.kv` | App-wide background, sized for 1024x600. |
| `overlay_images` | dict | `ScreenOverlay` (themed.py) | One PNG per screen, full-bleed. Empty `""` to disable. |
| `overlay_opacity` | float (0..1) | `ScreenOverlay` (themed.py) | Global dimmer for the decorative layer. PNG already has its own alpha; this multiplies it. Default `0.5`. Lower if artwork fights with text. |

### Menu styling (top bar)

| Key | Type | Default | Notes |
|---|---|---|---|
| `menu_button_normal` | path | `""` | 9-patch PNG. Empty = flat themed button. |
| `menu_button_active` | path | normal | Pressed state. |
| `menu_button_size` | `[w, h]` | `[180, 60]` | dp. |
| `menu_button_font_size` | int | `24` | sp. |
| `menu_button_padding` | `[l, t, r, b]` | `[0,0,0,0]` | dp. |
| `menu_selected_color` | rgba | white | Text color for the active screen's button. |
| `menu_unselected_color` | rgba | grey | Text color for inactive buttons. |

### Themed button graphics (optional)

| Key | Used in | Notes |
|---|---|---|
| `button_normal` | `ThemedButton` | 9-patch PNG. Empty `""` = flat themed bg from `colors.button_bg`. |
| `button_active` | `ThemedButton` | Pressed state PNG. |

When both are empty, `ThemedButton` uses `colors.button_bg` /
`colors.button_bg_active` for a flat look. This is the recommended path —
9-patch PNGs only render predictably if they're authored at the right
size with the right pad/border.

## Font sizes

KV refers to a font size by role: `size_role: "section_title"`. The
themed widget (`ThemedLabel/Button/Spinner/...`) reads
`theme.font_sizes[size_role]` and applies it. If the role doesn't exist
in this theme, a sensible default kicks in.

**Canonical scale** — base sizes used everywhere unless a semantic role
overrides:

| Role | Used for |
|---|---|
| `tiny` | Footnotes, micro-labels (e.g. weekly schedule day labels) |
| `small` | Secondary text |
| `default` | Body text, default `Label` font size |
| `medium` | Labels, button text, spinner items |
| `large` | Headings within sections |
| `xlarge` | Page titles (currently unused, reserved) |
| `huge` | Clock face on Home |

**Semantic roles** — meaning-driven aliases. Prefer these in KV when
possible — they let you tune typography of "section titles" vs "field
labels" without grepping every `size_role: "large"` in the codebase.

| Role | Meaning |
|---|---|
| `section_title` | Title at the top of a logical section ("Weather Forecast", "Room Sensors", "Today") |
| `field_label` | Inline label next to a field ("Theme:", "Username:", "Time") |
| `metric_value` | Numeric value of a sensor / metric ("22.6 °C", "45 %", "783 ppm") |

When designing a new theme, you can keep the semantic roles equal to a
canonical size (e.g. `section_title == large`) or set them independently
to fine-tune density without disturbing other widgets.

## Color roles

KV refers to a color by role: `color_role: "font_highlight"`. Same
fallback logic as font sizes.

### Text

| Role | Used for | Wired? |
|---|---|---|
| `font_default` | Default body text. | ✓ (heaviest use) |
| `font_secondary` | De-emphasized text (helper labels). | ✓ |
| `font_highlight` | Section titles, accents. | ✓ |
| `font_action` | Call-to-action text inside buttons. | reserved (not consumed yet) |
| `font_disabled` | Disabled state text. | ✓ |

### State

| Role | Used for | Wired? |
|---|---|---|
| `active` | Toggle ON, alarm armed, success state. | ✓ |
| `inactive` | Toggle OFF, default chrome. | ✓ |
| `semi_active` | "About to fire" or partial state (alarm time when armed). | ✓ |
| `warning` | Yellow-amber attention. | reserved (not consumed yet) |
| `error` | Red error state. | ✓ |
| `primary` | Generic accent (cursor, selection in TextInput). | ✓ |

### Domain-specific

| Role | Used for |
|---|---|
| `trend_up` / `trend_down` | Weather trend arrows ▲▼ on Home. |
| `weekend` / `weekday` | Schedule day-of-week labels. |
| `bar_water` / `bar_food` / `bar_clean` | Pigs progress bars. |

### Backgrounds for chrome

| Role | Used for | Wired? |
|---|---|---|
| `button_bg` | `ThemedButton` flat fill, MenuButton resting fill (when no PNG). | ✓ |
| `button_bg_active` | MenuButton selected/active fill (when no PNG). | ✓ |
| `input_bg` | `ThemedTextInput` background — keep dark in dark themes so `font_default` is readable. | ✓ |

### Shadow

| Role | Used for |
|---|---|
| `shadow_light` | Drop-shadow color when in *light* mode (typically dark with alpha). |
| `shadow_dark` | Drop-shadow color when in *dark* mode (typically light halo with alpha). |

`ShadowLabel` (the clock shadow on Home) picks the right one based on
`app.theme_mode`.

## Layout tokens

Everything in `theme.layout` is exposed to KV as
`app.ui_metrics['<key>']`. Use these instead of hardcoded `"8dp"` /
`"16dp"` literals — that's how the whole app stays on one grid.

The grid is `8 dp` (`grid_unit`). All other tokens are multiples.

### Spacing & padding scale

| Key | dp | Use |
|---|---|---|
| `padding_xs` / `spacing_xs` | 4 | Tight: inside compact rows, sensor lists |
| `padding_sm` / `spacing_sm` | 8 | Normal: between widgets in a panel |
| `padding_md` / `spacing_md` | 16 | Default panel padding |
| `padding_lg` / `spacing_lg` | 24 | Roomy panels (settings card) |

### Widget heights

| Key | dp | Use |
|---|---|---|
| `widget_height_sm` | 32 | Compact rows (sensor row) |
| `widget_height_md` | 48 | Default touch target (button, spinner) |
| `widget_height_lg` | 64 | Hero buttons, Save action |

### Menu / global

| Key | Default | Notes |
|---|---|---|
| `menu_height` | 72 | Top menu bar height. |
| `menu_padding` | 8 | Menu inner padding. |
| `content_padding` | 16 | Default outer padding for screen content (legacy). |
| `widget_spacing` | 10 | Generic between-widget spacing (legacy). |
| `widget_height` | 48 | Same as `widget_height_md` (legacy alias). |
| `small_widget_height` | 36 | Slightly larger than sm; used by older rules. |

The `_legacy_` group (`content_padding`, `widget_spacing`,
`widget_height`, `small_widget_height`) is kept for backwards-compat with
older `main.kv` rules and screens that haven't been migrated to the new
xs/sm/md/lg scale. Prefer the new tokens in any new KV.

## KV usage examples

```
# Padding from grid
ThemedPanel:
    padding: app.ui_metrics['padding_md']
    spacing: app.ui_metrics['spacing_sm']

# Standard touch-target height
ThemedButton:
    size_hint_y: None
    height: app.ui_metrics['widget_height_md']

# Section heading vs field label
ThemedLabel:
    text: "Weather Forecast"
    color_role: "font_highlight"
    size_role: "section_title"

ThemedLabel:
    text: "Theme:"
    color_role: "font_default"
    size_role: "field_label"

# Sensor row
ThemedLabel:
    text: "CO2: 783 ppm"
    color_role: "font_default"
    size_role: "metric_value"
    size_hint_y: None
    height: app.ui_metrics['widget_height_sm']
```

## Theme switch behavior

Switching themes from Settings calls `app.apply_theme(new_theme,
new_mode)` in `main.py`, which:

1. Loads the new `theme.json`.
2. Reassigns `app.theme_config` (DictProperty fires → KV bindings
   re-evaluate).
3. Rebuilds `app.ui_metrics` from `theme.layout`, merged over
   `_DEFAULT_LAYOUT` so missing keys fall back cleanly.
4. Persists the choice into `config/user.json`.

Themed widgets (`classes/themed.py`) bind to `theme_config` in Python
and re-paint via `_refresh()`. KV-only widgets re-evaluate their
`app.theme_config["…"]` lookups on the dict reassignment.

## Gotchas

- **Bleeding pixels in PNG-based themes:** if a 9-patch button doesn't
  fit `menu_button_size`, Kivy stretches and you get blurry edges. Either
  author the PNG at exact size, or leave `menu_button_normal: ""` for a
  flat themed button.
- **Dark mode with white `input_bg`:** if `font_default` is also white
  on a dark theme, text inside inputs becomes invisible. Always set
  `input_bg` to a dark color in dark themes.
- **Custom font with no Cyrillic / arrow glyphs:** Minecraftia for
  example has no ▲▼. We register `assets/fonts/DejaVuSans.ttf` as
  `Symbols` in `main.py` so KV can pin `font_name: "Symbols"` for those.
  If your theme's primary font has full glyph coverage, you can ignore
  this.
- **`_about` and `_comment_*` keys:** ignored at runtime. Use them
  liberally to document why a value is what it is.
- **Theme mode mismatch:** `mode` inside `theme.json` is informational.
  The folder name (`light/` or `dark/`) is what `apply_theme` reads.

# Smart widgets

Smart widgets are what you normally use. The compiler turns each one into DGUS controls plus generated images. Generated from the code by `tools/gen_docs.py`.

## `button`: Button

Tap target with label/icon and a pressed look. Action: open a page, set or step a variable, or send a key.

Category: input · needs a variable: no · verified on hardware

| Property | Type | Default | Description |
|---|---|---|---|
| `label` | string | `` |  |
| `icon` | string / null | `None` | Icon name (e.g. 'home', 'plus', 'power') |
| `style` | filled / outline / ghost | `filled` |  |
| `color` | string | `primary` |  |
| `text_color` | string / null | `None` | Default: readable colour on the button |
| `radius` | integer / null | `None` |  |
| `font_size` | integer / null | `None` |  |
| `action` | ? / null | `None` |  |
| `selected_color` | string / null | `None` | Set actions only: while the variable equals the value, show the button filled in this colour (radio / segmented buttons) |
| `selected_text_color` | string / null | `None` |  |

## `indicator`: Status indicator

Shows one of several states (colour, icon and label) for variable values 0..N-1.

Category: display · needs a variable: yes · verified on hardware

| Property | Type | Default | Description |
|---|---|---|---|
| `states` | array | `` | State 0, 1, 2... shown for variable values 0, 1, 2... |
| `style` | dot / icon / pill | `pill` |  |

## `number`: Number

Shows a variable as a number using digit images rendered from any font (works on every unit, including those with a rotated factory font). The box height sets the digit size.

Category: display · needs a variable: yes · verified on hardware

| Property | Type | Default | Description |
|---|---|---|---|
| `int_digits` | integer | `3` | Maximum integer digits shown |
| `decimals` | integer / null | `None` | Default: the variable's decimals |
| `font` | string / null | `None` |  |
| `weight` | light / regular / medium / semibold / bold | `regular` |  |
| `color` | string | `text` |  |
| `align` | left / right | `right` |  |
| `unit` | string | `` |  |
| `unit_size` | integer / null | `None` |  |
| `unit_color` | string | `muted` |  |
| `leading_zeros` | boolean | `False` |  |

## `progress`: Progress / gauge

Bar, vertical bar, ring or 270-degree arc gauge driven by a variable (one pre-rendered frame per value, so keep max-min <= 200).

Category: display · needs a variable: yes · verified on hardware

| Property | Type | Default | Description |
|---|---|---|---|
| `style` | bar / ring / arc / vbar | `bar` |  |
| `min` | integer | `0` |  |
| `max` | integer | `100` |  |
| `color` | string | `primary` |  |
| `track` | string | `surface2` |  |
| `thickness` | integer / null | `None` |  |
| `show_value` | boolean | `False` |  |
| `value_suffix` | string | `%` |  |
| `text_color` | string | `text` |  |

## `slider`: Slider

Drag to set a variable between min and max; the knob follows the value.

Category: input · needs a variable: yes · byte-matched to DGUS

| Property | Type | Default | Description |
|---|---|---|---|
| `min` | integer | `0` |  |
| `max` | integer | `100` |  |
| `vertical` | boolean | `False` |  |
| `track` | string | `surface2` |  |
| `knob` | string | `primary` |  |
| `thickness` | integer / null | `None` |  |

## `toggle`: Toggle

On/off control bound to a 0/1 variable; the screen shows the current state and reports changes.

Category: input · needs a variable: yes · verified on hardware

| Property | Type | Default | Description |
|---|---|---|---|
| `label` | string | `` |  |
| `sublabel` | string | `` |  |
| `icon` | string / null | `None` |  |
| `style` | tile / switch / pill | `tile` |  |
| `on_color` | string | `accent` |  |
| `off_color` | string | `surface` |  |
| `on_text` | string | `ON` |  |
| `off_text` | string | `OFF` |  |

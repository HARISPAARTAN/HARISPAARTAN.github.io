# Case-study content files: reference

One TOML file per project: `content/case-studies/<slug>.toml`. The build script turns each file into two pages (English and German) and adds a short list page:

| Output | Language |
|---|---|
| `work/<slug>/index.html` | English |
| `work/<slug>/de/index.html` | German |
| `work/index.html` | English list of all case studies (links to both languages) |

The interface strings (labels, buttons, footer lines) live in `content/case-studies/ui.toml`. You only edit that file to change wording that is the same on every page. Every other `*.toml` file in the folder is a project, so keep notes and drafts elsewhere.

```
python tools/build_case_studies.py                  # build every project and the list page into work/
python tools/build_case_studies.py --only <slug>    # check ONE file and write only its two pages (use this while writing)
python tools/build_case_studies.py --check          # build in memory; exit 1 if content is invalid or work/ is out of date
```

To look at a page, serve the repository folder with any static server, for example `python -m http.server 8000` in the repository root, and open `http://127.0.0.1:8000/work/<slug>/` (English) or `.../work/<slug>/de/` (German). The pages load the shared stylesheet, script and fonts by relative paths, so they work from a local server as they are.

`--only` never fails because of another project's file: that file may be missing, half written or broken. Only `meta.order`, `meta.slug` and `hero.title` of the neighbours are read, for the "previous / next" links at the end of the page. If a neighbour cannot be read, its link goes to the work section of the home page and the build prints a warning.

Errors are printed as `file: toml.path: problem` and all of them at once, so you can fix them in one pass. In a path, `flow.nodes[app]` is the `[[flow.nodes]]` table with `id = "app"`; a table without an id is counted from 1: `flow.nodes[#3]`; `fields[2]` is the second field. A build with errors writes nothing. Warnings are advice (for example "four to six steps"); they never stop a build.

## Rules that hold everywhere

1. **Every visible text is a pair**: `title.en = "..."` and `title.de = "..."`, both non-empty. Write the German as German, not word for word. In an array of tables a pair is simply the two keys of the table (`en = "..."`, `de = "..."`).
2. **Plain text only, except where a field says "rich".** Rich text understands two markups and nothing else: `**bold**` and `[label](https://address)`. Everything else is shown literally: `*italic*`, backticks and HTML tags are escaped, never interpreted. No nesting; a link target may not contain spaces or parentheses. Link targets may be `https://...`, `http://...`, a site path starting with `/`, `./`, `../` or an anchor `#how`. Anything else (`javascript:`, `mailto:`, `//host`) is an error.
3. **Line breaks inside a text are folded into single spaces.** Use `"""..."""` to wrap long prose in the file. Separate paragraphs by separate entries, never by blank lines inside one text.
4. **Unknown keys are errors** (with a "did you mean" hint), so a typo is never silently ignored.
5. **Ids** (`id`) start with a lower-case letter and contain lower-case letters, digits, `-` and `_`. They are unique inside their list (nodes, edges, steps, entities) and are never shown on the page.
6. **No numbers or names the facts do not support.** The page shows what you write; the content rules of the design spec (no client names, people, e-mail addresses, internal URLs, tenant or site names, project codes or source code; numbers only with a source; the status exactly as the facts support it) are yours to keep.

## Keys

`required` means the build fails without it. Counts in the right column are limits (error) or recommendations (warning).

### `[meta]`

| Key | Type | | Notes |
|---|---|---|---|
| `slug` | string | required | Lower-case letters, digits, single hyphens. Must equal the file name without `.toml`. Becomes the address `/work/<slug>/`. |
| `order` | integer ≥ 1 | required | Position in the card order. A full build needs the orders of all files to be exactly 1..N without gaps or duplicates. Shown as "case study 02 / 05" (N is the number of files). |
| `status` | pair | required | The status in a few words, exactly as the facts support it (design spec, section 16.3), for example `status.en = "in use since September 2026"` and `status.de = "im Einsatz seit September 2026"`. Shown at the end of the eyebrow line. A warning above 40 characters: put the long form in the facts list or the result. |
| `tech` | list of strings | required | 1 to 8 technology tags, shown as written in both languages. |
| `demo_url` | string | optional | `https://...` or a site path starting with `/`. Without it the page has no demo buttons at all. |
| `og_image` | string | optional | Social preview image, a path inside the site without a leading slash (`assets/img/og-example.png`). Default: `assets/img/og.png`. A warning appears when the file does not exist. |
| `facts_as_of` | date | required | `2026-10-26` (TOML date) or the same in quotes. Shown at the end of section 06 ("Facts as of 26 October 2026" / "Stand der Angaben: 26. Oktober 2026"). |
| `notice` | pair | optional | Replaces the footer notice ("Simplified description of an internal system ..."), for a project where it does not fit. |

### `[hero]`

| Key | Type | | Notes |
|---|---|---|---|
| `eyebrow` | pair | required | The short category in the middle of the eyebrow line: `case study 02 / 05 · <eyebrow> · <status>`. Example: `power apps`. |
| `title` | pair | required | The H1. Also used in the browser title, the pager of the other pages and the list page. |
| `subtitle` | pair | required | One line under the title. |
| `lead` | pair, rich | required | Two to four sentences. The first sentences (up to about 300 characters) also become the meta description. |
| `[[hero.stats]]` | tables | required | **Exactly four** stat tiles. `value`: a plain string (same in both languages) or a pair, for example `"20+"`; keep it short (a warning above 12 characters). `label`: pair. |
| `[[hero.facts]]` | tables | required | 1 to 6 lines of the small facts list (role, users, devices or platform): `label` (pair), `value` (pair). |

### `[why]` (section 01)

| Key | Type | | Notes |
|---|---|---|---|
| `heading` | pair | required | The H2 of the section. |
| `[[why.paragraphs]]` | pairs, rich | required | 1 to 4; two or three recommended. Each entry is a table with `en` and `de`. |
| `[[why.notes]]` | tables | optional | 0 to 3 side notes, two recommended ("Who uses it", "What it costs to run"): `title` (pair), `text` (pair, rich). |

### `[flow]` (section 02, the architecture diagram)

| Key | Type | | Notes |
|---|---|---|---|
| `heading` | pair | required | The H2 of the section. |
| `description` | pair | required | What the diagram shows, in one or two sentences. Read by screen readers as the description of the SVG. |
| `[[flow.nodes]]` | tables | required | At least 2 boxes (see below). |
| `[[flow.edges]]` | tables | required | At least 1 arrow (see below). |
| `[[flow.steps]]` | tables | required | At least 1; four to six recommended (see below). |

Each node (a box in the diagram):

| Key | Type | | Notes |
|---|---|---|---|
| `id` | string | required | Used by edges and steps. |
| `tag` | string or pair | required | The small technology line on top of the box. Shown in capitals (write it either way). A plain string is used in both languages (`tag = "SHAREPOINT"`); a pair for words (`tag.en = "PEOPLE"`, `tag.de = "MENSCHEN"`). |
| `title` | pair | required | The name of the box. |
| `role` | pair | required | One short line: what the box does. |
| `wide` | `[x, y, width]` | required | Position in the wide layout (see "Coordinates"). |
| `tall` | `[x, y, width]` | required | Position in the tall (phone) layout. |

Each edge (an arrow):

| Key | Type | | Notes |
|---|---|---|---|
| `id` | string | required | Used by steps. |
| `wide` | `["from", "to"]` | required | Two anchors for the wide layout, for example `["app.right", "lists.left@0.4"]`. The arrowhead is at the second anchor. |
| `tall` | `["from", "to"]` | required | The same for the tall layout. |

Each step (one stop of the animation, also a numbered list item):

| Key | Type | | Notes |
|---|---|---|---|
| `id` | string | required | Used in messages only. |
| `title` | pair | required | Short, shown in the list and in the caption "Step 2 of 6 · title". |
| `text` | pair | required | One or two sentences. Only `**bold**` is allowed here, no links: the step is a button. |
| `nodes` | list of node ids | required | The boxes that light up (at least one). The others dim. |
| `edges` | list of edge ids | optional | The arrows that light up, with two dots travelling along each. |
| `badge` | table | optional | A small pill on one box while the step is shown, for example OFFLINE: `node` (a node id, normally one of the step's nodes), `text` (string or pair, shown in capitals), `pos` (`"right"` default, `"left"` or `"center"`: where it sits on the top edge of the box). |

A node or arrow that no step lights up gets a warning, because it would never be highlighted.

### `[model]` (section 03, the data model)

| Key | Type | | Notes |
|---|---|---|---|
| `heading` | pair | required | The H2 of the section. |
| `description` | pair | required | What the diagram shows, for screen readers. |
| `caption` | pair, rich | required | Under the diagram. Says what was left out ("Simplified: six of the ten lists ..."). |
| `[[model.entities]]` | tables | required | At least 2 (see below). |
| `[[model.relations]]` | tables | required | At least 1 (see below). |
| `[[model.notes]]` | tables | optional | 0 to 3 notes about design details: `title` (pair), `text` (pair, rich). |

Each entity (a list, library or object):

| Key | Type | | Notes |
|---|---|---|---|
| `id` | string | required | Used by relations. |
| `kind` | string | required | `"list"`, `"library"` or `"object"`. A **library** (document library, file store) gets a dashed border and a legend line under the diagram. |
| `name` | pair | required | The name of the entity. |
| `note` | pair | required | One line under the name ("one per site walk"). |
| `wide` | `[x, y, width]` | required | Position in the wide diagram. There is no tall layout: phones show entity cards instead. |
| `fields` | list of tables | required | 1 to 5 fields: `{ key = "PK", name.en = "...", name.de = "..." }`. `key` is optional and is `"PK"` or `"FK"`. Where the real key is a SharePoint item ID, say so in the field name. |

Each relation:

| Key | Type | | Notes |
|---|---|---|---|
| `from`, `to` | entity ids | required | For `one-to-many`, `from` is the "one" side. They must be different. |
| `cardinality` | string | required | `"one-to-many"` (a bar at `from`, a crow's foot at `to`), `"one-to-one"` or `"many-to-many"`. |
| `wide` | `["from", "to"]` | required | Two anchors, the first on the `from` entity and the second on the `to` entity. No arrowhead; the line ends in the marks. |
| `text` | pair | required | The sentence for the phone cards, for example `"1 inspection → many observations"`. It appears on the card of the `from` entity. |

### `[decisions]`, `[role]`, `[result]` (sections 04 to 06)

| Key | Type | | Notes |
|---|---|---|---|
| `decisions.heading` | pair | optional | Default from `ui.toml` ("Trade-offs that shaped the build"). |
| `[[decisions.items]]` | tables | required | 1 to 6 cards, three or four recommended: `title` (pair), `text` (pair, rich). |
| `role.heading` | pair | optional | Default from `ui.toml` ("What I did"). |
| `[[role.bullets]]` | pairs, rich | required | 1 to 8 bullets, four to six recommended. |
| `result.heading` | pair | required | The H2 of the section. |
| `result.text` | pair, rich | required | One paragraph with what was delivered and when, and the status. No usage, time-saving or benefit figures unless the facts measure them. Shown with the demo button when `meta.demo_url` is set, then the "facts as of" line and the pager. |

## What the build checks

**Errors** (nothing is written until they are fixed):

* a text pair without `en` or `de`, or with an empty text; a plain string where a pair is needed; an unknown language key;
* a step, edge or relation that names an unknown node, edge or entity; a bad anchor (`app.rght`, `@1.5`); two anchors on the same box;
* not exactly four stat tiles; more than five fields in an entity; more than three notes; missing sections or keys; unknown keys; a `slug` that differs from the file name; duplicate ids;
* a text estimated wider than its box (both languages, both layouts); a box outside the canvas or less than 4 units from another box; an arrow or relation line that leaves the canvas; a badge pill outside the canvas;
* a link target that is not `https://`, `http://`, a site path or an anchor; any link inside a step text;
* in a full build: orders that are not exactly 1..N.

**Warnings** (advice, the build still succeeds): a count outside the recommended range (paragraphs, side notes, steps, decision cards, bullets); a node or arrow no step lights up; a badge on a box the step dims; a badge pill that covers the place where an arrow meets the box; an arrow or relation line that runs through a box it does not join; a stat value longer than 12 characters; an `og_image` file that does not exist; in `--only` a neighbour that cannot be read.

The other options of the script are for tests and previews: `--content-dir DIR`, `--ui FILE` and `--out-dir DIR` build from and into other folders.

## Coordinates: how to place boxes

* The diagram is drawn on a canvas of **user units**. Origin top left, x to the right, y downward. The canvas is **1000 units wide in the `wide` layout** (screens from 1000 px) and **400 units wide in the `tall` layout** (phones and tablets, under 1000 px). The page scales the canvas to the width of the column: 1000 units become about 1060 px on screens of 1280 px and wider and about 920 px at 1000 px; 400 units become 300 to 330 px on a phone (360 to 390 px) and at most 460 px on a tablet. A role line of 11.5 units is therefore drawn at least about 8.5 px high on a phone and 10.5 px on a 1000 px screen.
* A box is `[x, y, width]` for its top left corner and its width. **Every flow box is 88 units high.** An entity box is `46 + 24 × (number of fields) + 8` units high (five fields: 174).
* **The viewBox height is computed, never written.** It is the lowest point of any box or arrow plus 20 units, rounded up. The wide example below ends at 40 + 88 = 128, so its height is 148.
* A box must lie inside the canvas (`x ≥ 0`, `y ≥ 0`, `x + width ≤ 1000` or `400`), and two boxes must stay **at least 4 units apart**. Aim for 40 to 70 units of space between boxes, or the arrows have no room to show.
* Inside a flow box, text starts 14 units from the left edge: the tag at y + 25 (10 px mono), the title at y + 51 (16 px), the role at y + 71 (11.5 px). Inside an entity box the name sits at y + 21, the note at y + 37, field rows start at y + 46.
* Suggested grids. Wide: columns at x = 20, 260, 540, 810 with widths 180 to 210 and rows 150 units apart. Tall: one column at `x = 30, width = 340`, rows 120 units apart (box 88 + 32 for the arrow).

### Text must fit its box

The build estimates the width of every text in the diagrams as *characters × average glyph width of its font size* and fails when it is wider than the room inside its box. The average glyph widths were measured in Chrome on English and German strings: 0.50 em for Inter and Space Grotesk, exactly 0.6 em for JetBrains Mono. Real text varies by a few percent either way (German compounds and capitals run wider, lower-case with many i, l, t narrower), so a text that just fits may touch the right padding of its box: leave a little room. All texts are checked in both languages and in both layouts. Characters that fit (box width in units, less the padding):

| Where | Font | Units per character | Room inside a box |
|---|---|---|---|
| Node tag (capitals) | JetBrains Mono 10 px, letter-spacing 0.08 em | 6.8 | width − 28 |
| Node title | Space Grotesk 16 px | 8.0 | width − 28 |
| Node role | Inter 11.5 px | 5.75 | width − 28 |
| Entity name | Space Grotesk 14 px | 7.0 | width − 24 |
| Entity note | JetBrains Mono 10.5 px | 6.3 | width − 24 |
| Entity field | Inter 12 px | 6.0 | width − 52 |
| Badge pill | JetBrains Mono 10 px, letter-spacing 0.1 em | 7.0 | the pill grows with its text |

| Box width | tag | title | role | | Box width | name | note | field |
|---|---|---|---|---|---|---|---|---|
| 160 | 19 | 16 | 22 | | 160 | 19 | 21 | 18 |
| 180 | 22 | 19 | 26 | | 180 | 22 | 24 | 21 |
| 200 | 25 | 21 | 29 | | 200 | 25 | 27 | 24 |
| 210 | 26 | 22 | 31 | | 220 | 28 | 31 | 28 |
| 240 | 31 | 26 | 36 | | 250 | 32 | 35 | 33 |
| 300 | 40 | 34 | 47 | | 300 | 39 | 43 | 41 |
| 340 | 45 | 39 | 54 | | | | | |

## Anchors and arrows

An anchor names a box, one of its sides and, optionally, where along that side:

```
app.right          the middle of the right side of node "app"
lists.bottom@0.3   30 % along the bottom side of "lists", measured from the left
app.left@0         the top end of the left side (use 0 to 1)
```

* Sides: `top`, `right`, `bottom`, `left`. The number goes from 0 to 1: **left to right** on `top` and `bottom`, **top to bottom** on `left` and `right`. The default is 0.5.
* An arrow runs from its first anchor to its second; the arrowhead (a small triangle, 9 units long) ends 4 units before the second side.
* **A straight line** is drawn when the two anchors line up (facing sides such as `right` to `left` or `bottom` to `top`, with the same y or x, to within half a unit). To line up two boxes of different heights, choose the positions so that y matches: `y1 + t1 × h1 = y2 + t2 × h2`.
* Otherwise the arrow is a **smooth curve** that leaves the first side and arrives at the second at a right angle. Sides that are not facing each other make corners and U-turns; if the result looks odd, move a box or pick another side.
* An arrow may not leave the canvas.
* In the data model the same anchors are used for relations (`"inspections.right", "observations.left"`). A relation line has no arrowhead and no gap; it ends in a bar (one) or a crow's foot (many).

## Reading order, phones and no JavaScript

* **Phones and tablets** (under 1000 px) get the tall layout of the architecture diagram, top to bottom, and the data model as a list of entity cards (name, note, fields with PK/FK marks and the relation sentences). There is no sideways scrolling.
* **Without JavaScript** the diagram is a complete still picture (nothing dimmed) and the steps are a numbered list; every step text, the badge text and the data-model cards are in the page as text.
* **With "reduce motion"** there is no autoplay and nothing moves; the dots rest at fixed points on the active arrows, and steps still change on click.

## Minimal complete example

This file builds without errors or warnings (the tests build it). Save it as `content/case-studies/sample-tool.toml`, run `python tools/build_case_studies.py --only sample-tool`, then replace the texts.

```toml
[meta]
slug = "sample-tool"
order = 1
status.en = "pilot"
status.de = "Pilot"
tech = ["scripting", "database"]
demo_url = "https://example.org/demo/"
facts_as_of = 2026-10-26

[hero]
eyebrow.en = "small tool"
eyebrow.de = "kleines Werkzeug"
title.en = "Sample tool"
title.de = "Beispielwerkzeug"
subtitle.en = "One line that says what it is"
subtitle.de = "Eine Zeile, die sagt, was es ist"
lead.en = "Two to four sentences: what it does, for whom, and what I did. **Bold** and [links](https://example.org) work here."
lead.de = "Zwei bis vier Sätze: was es tut, für wen und was ich gemacht habe. **Fett** und [Links](https://example.org) gehen hier."

[[hero.stats]]
value = "4"
label.en = "steps"
label.de = "Schritte"

[[hero.stats]]
value = "3"
label.en = "boxes"
label.de = "Bausteine"

[[hero.stats]]
value.en = "99.5 %"
value.de = "99,5 %"
label.en = "of rows pass the check"
label.de = "der Zeilen bestehen die Prüfung"

[[hero.stats]]
value = "2"
label.en = "tables"
label.de = "Tabellen"

[[hero.facts]]
label.en = "Role"
label.de = "Rolle"
value.en = "design and build"
value.de = "Konzeption und Umsetzung"

[why]
heading.en = "Why it exists"
heading.de = "Warum es das gibt"

[[why.paragraphs]]
en = "The problem before the project, in plain words."
de = "Das Problem vor dem Projekt, in einfachen Worten."

[[why.paragraphs]]
en = "**What changed** because of the project."
de = "**Was sich geändert hat**, seit es das Projekt gibt."

[[why.notes]]
title.en = "Who uses it"
title.de = "Wer sie nutzt"
text.en = "Two people, every day."
text.de = "Zwei Personen, jeden Tag."

[[why.notes]]
title.en = "What it costs to run"
title.de = "Was der Betrieb kostet"
text.en = "Nothing beyond the existing licences."
text.de = "Nichts über die vorhandenen Lizenzen hinaus."

[flow]
heading.en = "How it works"
heading.de = "So funktioniert es"
description.en = "An input is read by a tool, which writes the result to a store."
description.de = "Eine Eingabe wird von einem Werkzeug gelesen, das das Ergebnis in einen Speicher schreibt."

[[flow.nodes]]
id = "input"
tag = "SOURCE"
title.en = "Input"
title.de = "Eingabe"
role.en = "files from a folder"
role.de = "Dateien aus einem Ordner"
wide = [40, 40, 240]
tall = [30, 20, 340]

[[flow.nodes]]
id = "tool"
tag = "SCRIPT"
title.en = "Tool"
title.de = "Werkzeug"
role.en = "checks and converts"
role.de = "prüft und wandelt um"
wide = [380, 40, 240]
tall = [30, 140, 340]

[[flow.nodes]]
id = "store"
tag = "DATABASE"
title.en = "Store"
title.de = "Speicher"
role.en = "one row per record"
role.de = "eine Zeile pro Datensatz"
wide = [720, 40, 240]
tall = [30, 260, 340]

[[flow.edges]]
id = "read"
wide = ["input.right", "tool.left"]
tall = ["input.bottom", "tool.top"]

[[flow.edges]]
id = "write"
wide = ["tool.right", "store.left"]
tall = ["tool.bottom", "store.top"]

[[flow.steps]]
id = "read"
title.en = "Read"
title.de = "Lesen"
text.en = "The tool picks up the files."
text.de = "Das Werkzeug holt die Dateien ab."
nodes = ["input", "tool"]
edges = ["read"]

[[flow.steps]]
id = "check"
title.en = "Check"
title.de = "Prüfen"
text.en = "Every row is checked. **Bad rows** are kept apart."
text.de = "Jede Zeile wird geprüft. **Schlechte Zeilen** werden getrennt aufbewahrt."
nodes = ["tool"]
badge = { node = "tool", text.en = "BATCH", text.de = "STAPEL" }

[[flow.steps]]
id = "write"
title.en = "Write"
title.de = "Schreiben"
text.en = "Good rows go to the store."
text.de = "Gute Zeilen gehen in den Speicher."
nodes = ["tool", "store"]
edges = ["write"]

[[flow.steps]]
id = "done"
title.en = "Done"
title.de = "Fertig"
text.en = "The whole path has run."
text.de = "Der ganze Weg ist durchlaufen."
nodes = ["input", "tool", "store"]
edges = ["read", "write"]

[model]
heading.en = "Two tables"
heading.de = "Zwei Tabellen"
description.en = "A batch holds many rows."
description.de = "Ein Stapel enthält viele Zeilen."
caption.en = "Simplified: two of the five tables."
caption.de = "Vereinfacht: zwei der fünf Tabellen."

[[model.entities]]
id = "batches"
kind = "list"
name.en = "Batches"
name.de = "Stapel"
note.en = "one per day"
note.de = "einer pro Tag"
wide = [40, 30, 300]
fields = [
  { key = "PK", name.en = "Batch ID", name.de = "Stapel-ID" },
  { name.en = "Received on", name.de = "Eingegangen am" },
]

[[model.entities]]
id = "rows"
kind = "list"
name.en = "Rows"
name.de = "Zeilen"
note.en = "one per record"
note.de = "eine pro Datensatz"
wide = [440, 30, 300]
fields = [
  { key = "PK", name.en = "Row ID", name.de = "Zeilen-ID" },
  { key = "FK", name.en = "Batch", name.de = "Stapel" },
  { name.en = "Value", name.de = "Wert" },
]

[[model.relations]]
from = "batches"
to = "rows"
cardinality = "one-to-many"
wide = ["batches.right", "rows.left"]
text.en = "1 batch → many rows"
text.de = "1 Stapel → viele Zeilen"

[decisions]
[[decisions.items]]
title.en = "First decision"
title.de = "Erste Entscheidung"
text.en = "What was chosen and why."
text.de = "Was gewählt wurde und warum."

[[decisions.items]]
title.en = "Second decision"
title.de = "Zweite Entscheidung"
text.en = "What was chosen and why."
text.de = "Was gewählt wurde und warum."

[[decisions.items]]
title.en = "Third decision"
title.de = "Dritte Entscheidung"
text.en = "What was chosen and why."
text.de = "Was gewählt wurde und warum."

[role]
[[role.bullets]]
en = "What I did, first."
de = "Was ich zuerst gemacht habe."

[[role.bullets]]
en = "What I did, second."
de = "Was ich als Zweites gemacht habe."

[[role.bullets]]
en = "What I did, third."
de = "Was ich als Drittes gemacht habe."

[[role.bullets]]
en = "What I did, fourth."
de = "Was ich als Viertes gemacht habe."

[result]
heading.en = "The result"
heading.de = "Das Ergebnis"
text.en = "**The measured effect**, and the status in one sentence."
text.de = "**Die gemessene Wirkung** und der Stand in einem Satz."
```

## Common mistakes

| Message | Cause and fix |
|---|---|
| `title.de: missing German text` | A pair needs both languages. Add the `de` line. |
| `must be a pair of texts: write hero.subtitle.en = ... and hero.subtitle.de = ...` | A plain string was given where a pair is needed. Only `tag`, a stat `value` and a badge `text` may be plain. |
| `unknown node "ingset" (did you mean "ingest"?)` | A step or anchor names a box that does not exist. Ids are case-sensitive. |
| `a page needs exactly 4 stat tiles, found 3` | `[[hero.stats]]` must appear four times. |
| `text is about 173 units wide (30 characters x 5.75) but the box (wide layout, box 200 wide) leaves 172; shorten it to about 29 characters or make the box wider` | See "Text must fit its box". Shorten the text or widen the box in that layout. |
| `box lies outside its viewBox: the box ends at x = 1040 but the viewBox is only 1000 wide` | `x + width` is larger than the canvas. |
| `box overlaps "store" or lies closer than 4 units to it` | Move one of the two boxes. |
| `bad anchor "app.rght"` | The anchor syntax is `id.side` or `id.side@0.3`; sides are top, right, bottom, left. |
| `links are not allowed in this text because it sits inside a button` | Step texts take **bold** only. Put the link into the paragraph above or into another section. |
| `unknown key "facts_as_off" (did you mean "facts_as_of"?)` | A typo in a key name. |
| `the orders of all content files must be exactly 1..5` | Two files claim the same `meta.order`, or one number is missing. (`--only` only warns.) |

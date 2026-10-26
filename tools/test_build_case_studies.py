"""Tests for tools/build_case_studies.py (standard library only).

    python -m unittest tools/test_build_case_studies.py -v

The tests build an invented project (tools/fixtures/case-studies/example-pipeline.toml) into temporary folders. They
never read the real project files in content/case-studies/, only its ui.toml, and never write inside the repository.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import build_case_studies as bcs  # noqa: E402

FIXTURE = TOOLS / "fixtures" / "case-studies" / "example-pipeline.toml"
UI = REPO / "content" / "case-studies" / "ui.toml"
SCRIPT = TOOLS / "build_case_studies.py"
HEAD_SCRIPT = ("document.documentElement.classList.add('js');try{if(localStorage.getItem('hh-theme')==='light')"
               "document.documentElement.setAttribute('data-theme','light')}catch(e){}")
SLUG = "example-pipeline"


def fixture_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def mutate(text: str, old: str, new: str, count: int = 1) -> str:
    assert text.count(old) == count, f"fixture changed: {old!r} occurs {text.count(old)} times, expected {count}"
    return text.replace(old, new)


def derive(slug: str, order: int, title_en: str, title_de: str | None = None) -> str:
    """The fixture as another case study: new slug, order and title."""
    text = mutate(fixture_text(), 'slug = "example-pipeline"', f'slug = "{slug}"')
    text = mutate(text, "order = 1", f"order = {order}")
    text = mutate(text, 'title.en = "Example pipeline"', f'title.en = "{title_en}"')
    return mutate(text, 'title.de = "Beispiel-Pipeline"', f'title.de = "{title_de or title_en}"')


class Workspace:
    """A temporary content folder and output folder."""

    def __init__(self, test: unittest.TestCase) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="cs-test-"))
        test.addCleanup(shutil.rmtree, self.root, True)
        self.content = self.root / "content"
        self.content.mkdir()
        self.out = self.root / "site" / "work"

    def write(self, name: str, text: str) -> Path:
        path = self.content / f"{name}.toml"
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def build(self, only: str | None = None) -> bcs.Build:
        return bcs.build(self.content, UI, self.out, only)

    def main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bcs.main(["--content-dir", str(self.content), "--ui", str(UI), "--out-dir", str(self.out), *args])
        return code, out.getvalue(), err.getvalue()

    def page(self, slug: str = SLUG, lang: str = "en") -> str:
        path = self.out / slug / "de" / "index.html" if lang == "de" else self.out / slug / "index.html"
        return path.read_text(encoding="utf-8")


def built(test: unittest.TestCase, text: str | None = None) -> tuple[Workspace, bcs.Build]:
    ws = Workspace(test)
    ws.write(SLUG, fixture_text() if text is None else text)
    result = ws.build()
    return ws, result


def messages(items) -> list[str]:
    return [str(i) for i in items]


def html_of(result: bcs.Build, ws: Workspace, lang: str = "en", slug: str = SLUG) -> str:
    return result.outputs[bcs.output_path(ws.out, slug, lang)]


class Structure(HTMLParser):
    """Collects ids and checks that every non-void element is closed in order."""
    VOID = {"meta", "link", "br", "img", "input", "hr", "source", "wbr", "col", "area", "base", "embed", "param", "track"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.ids: list[str] = []
        self.problems: list[str] = []
        self.tags: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if "id" in a:
            self.ids.append(a["id"])
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if "id" in a:
            self.ids.append(a["id"])

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"unexpected </{tag}> (open: {self.stack[-3:]})")
        else:
            self.stack.pop()

    def count(self, tag: str, **attrs) -> int:
        return sum(1 for t, a in self.tags if t == tag and all(k in a and (v is True or a[k] == v) for k, v in attrs.items()))


def parse(page: str) -> Structure:
    s = Structure()
    s.feed(page)
    s.close()
    return s


# ---------------------------------------------------------------- a valid build

class ValidBuild(unittest.TestCase):
    def setUp(self) -> None:
        self.ws, self.result = built(self)
        self.en = html_of(self.result, self.ws, "en")
        self.de = html_of(self.result, self.ws, "de")

    def test_builds_without_errors_and_with_the_expected_pages(self):
        self.assertEqual(messages(self.result.errors), [])
        self.assertEqual(
            sorted(p.relative_to(self.ws.out).as_posix() for p in self.result.outputs),
            ["example-pipeline/de/index.html", "example-pipeline/index.html", "index.html"],
        )

    def test_the_fixture_folder_itself_is_a_content_dir(self):
        out = Path(tempfile.mkdtemp(prefix="cs-fixture-out-"))
        self.addCleanup(shutil.rmtree, out, True)
        result = bcs.build(FIXTURE.parent, UI, out / "work")
        self.assertEqual(messages(result.errors), [])
        self.assertEqual(len(result.outputs), 3)
        self.assertTrue(all(out in p.parents for p in result.outputs), "every page goes below the folder given as out-dir")
        self.assertFalse((REPO / "work").exists(), "the fixture never builds into the repository's work folder")

    def test_fixture_has_no_warnings(self):
        self.assertEqual(messages(self.result.warnings), [])

    def test_pages_are_well_formed_with_unique_ids(self):
        for page in (self.en, self.de, self.result.outputs[self.ws.out / "index.html"]):
            s = parse(page)
            self.assertEqual(s.problems, [])
            self.assertEqual(s.stack, [])
            self.assertEqual(len(s.ids), len(set(s.ids)), f"duplicate ids: {sorted(i for i in s.ids if s.ids.count(i) > 1)}")

    def test_english_head(self):
        self.assertTrue(self.en.startswith("<!doctype html>\n"))
        self.assertIn('<html lang="en">', self.en)
        self.assertIn('<link rel="canonical" href="https://harispaartan.github.io/work/example-pipeline/">', self.en)
        self.assertIn('<link rel="alternate" hreflang="en" href="https://harispaartan.github.io/work/example-pipeline/">', self.en)
        self.assertIn('<link rel="alternate" hreflang="de" href="https://harispaartan.github.io/work/example-pipeline/de/">', self.en)
        self.assertIn('<link rel="alternate" hreflang="x-default" href="https://harispaartan.github.io/work/example-pipeline/">', self.en)
        self.assertIn(f"<script>{HEAD_SCRIPT}</script>", self.en, "same head script as index.html")
        for asset in ("css/site.css", "css/case-study.css"):
            self.assertIn(f'<link rel="stylesheet" href="../../assets/{asset}">', self.en)
        for asset in ("js/site.js", "js/case-study.js"):
            self.assertIn(f'<script src="../../assets/{asset}" defer></script>', self.en)
        self.assertLess(self.en.index("assets/js/site.js"), self.en.index("assets/js/case-study.js"))

    def test_german_head(self):
        self.assertIn('<html lang="de">', self.de)
        self.assertIn('<link rel="canonical" href="https://harispaartan.github.io/work/example-pipeline/de/">', self.de)
        self.assertIn('hreflang="x-default" href="https://harispaartan.github.io/work/example-pipeline/">', self.de)
        self.assertIn('property="og:locale" content="de_DE"', self.de)

    def test_header_has_brand_breadcrumb_language_switch_and_theme_toggle(self):
        s = parse(self.en)
        self.assertEqual(s.count("a", **{"class": "brand", "href": "../../"}), 1)
        self.assertIn('<a href="../../#work">work</a>', self.en)
        self.assertIn('<li aria-current="page">example-pipeline</li>', self.en)
        self.assertIn('<a href="./" lang="en" hreflang="en" title="English" aria-current="true">EN</a>', self.en)
        self.assertIn('<a href="de/" lang="de" hreflang="de" title="Deutsch">DE</a>', self.en)
        self.assertEqual(self.en.count('aria-current="true"'), 1)
        self.assertIn('<a href="../" lang="en" hreflang="en" title="English">EN</a>', self.de)
        self.assertIn('<a href="./" lang="de" hreflang="de" title="Deutsch" aria-current="true">DE</a>', self.de)
        self.assertEqual(s.count("button", id="theme-toggle"), 1)

    def test_every_section_is_present_in_order(self):
        ids = [a["id"] for t, a in parse(self.en).tags if t == "section" and "id" in a]
        self.assertEqual(ids, ["why", "how", "model", "decisions", "role", "result"])
        self.assertIn("01 / why it exists", self.en)
        self.assertIn("06 / result", self.en)
        self.assertIn("01 / warum es das gibt", self.de)

    def test_hero(self):
        self.assertIn('<p class="eyebrow">case study 01 / 01 · data pipeline · prototype</p>', self.en)
        self.assertIn('<p class="eyebrow">Fallstudie 01 / 01 · Datenpipeline · Prototyp</p>', self.de)
        s = parse(self.en)
        self.assertEqual(s.count("div", **{"class": "stat"}), 4)
        self.assertIn('<a class="btn primary" href="https://example.org/demo/">Open the live demo</a>', self.en)
        self.assertIn('<a class="btn" href="#how">How it works</a>', self.en)
        self.assertIn("<dt>Role</dt><dd>design and build</dd>", self.en)
        self.assertIn('<span class="stat-value">99,5 %</span>', self.de, "a value can differ per language")
        self.assertIn('<span class="stat-value">24</span>', self.de, "a plain value is the same in both languages")

    def test_no_demo_buttons_without_a_demo_url(self):
        ws, result = built(self, mutate(fixture_text(), 'demo_url = "https://example.org/demo/"\n', ""))
        page = html_of(result, ws)
        self.assertNotIn("Open the live demo", page)
        self.assertIn("How it works", page)

    def test_architecture_diagram_has_both_layouts_with_the_same_data(self):
        s = parse(self.en)
        self.assertEqual(s.count("svg", **{"class": "flow flow-wide"}), 1)
        self.assertEqual(s.count("svg", **{"class": "flow flow-tall"}), 1)
        for which, width in (("wide", 1000), ("tall", 400)):
            self.assertRegex(self.en, rf'<svg class="flow flow-{which}" viewBox="0 0 {width} \d+"')
        self.assertEqual(self.en.count('data-node="sensors"'), 2)
        self.assertEqual(self.en.count('data-edge="e3"'), 2)
        self.assertNotIn("<marker", self.en)
        self.assertNotIn("marker-end", self.en)
        steps = re.findall(r'<li data-step data-title="([^"]*)" data-nodes="([^"]*)" data-edges="([^"]*)">', self.en)
        self.assertEqual(len(steps), 4)
        self.assertEqual(steps[0], ("Collect", "sensors ingest", "e1"))
        for _, nodes, edges in steps:
            for n in nodes.split():
                self.assertEqual(self.en.count(f'data-node="{n}"'), 2)
            for e in edges.split():
                self.assertEqual(self.en.count(f'data-edge="{e}"'), 2)
        self.assertIn('<ol class="steps" data-count="4" aria-label="Steps">', self.en)

    def test_diagram_elements_have_a_title_and_a_description_and_no_ids_for_steps(self):
        self.assertIn('<title id="cs-flow-wide-title">Architecture diagram: Example pipeline</title>', self.en)
        self.assertIn('<title id="cs-flow-tall-title">Architekturdiagramm: Beispiel-Pipeline</title>', self.de)
        self.assertRegex(self.en, r'<desc id="cs-flow-wide-desc">Field sensors send files')
        self.assertNotRegex(self.en, r'id="(step|node|edge)')

    def test_player_hooks_and_interface_strings_come_from_data_attributes(self):
        self.assertIn('data-caption="Step {n} of {total} · {title}" data-play="Play" data-pause="Pause" data-interval="3800"', self.en)
        self.assertIn('data-caption="Schritt {n} von {total} · {title}" data-play="Abspielen" data-pause="Pause"', self.de)
        for hook in ("data-cs-flow", "data-cs-caption", "data-cs-toggle", "data-cs-toggle-label", "data-cs-toolbar"):
            self.assertIn(hook, self.en)

    def test_arrowheads_are_small_triangles_ending_before_the_box(self):
        # wide layout: sensors (20..220 at y 40..128) -> ingest (x = 290); the arrow is straight at y = 84
        self.assertIn('<g class="edge" data-edge="e1"><path class="line" d="M220,84 L277,84"/>'
                      '<path class="head" d="M286,84 L277,79.5 L277,88.5z"/></g>', self.en)

    def test_badge_pill_is_drawn_for_the_badge_step_only(self):
        self.assertEqual(self.en.count('class="pill" data-step-badge="3"'), 2)
        self.assertEqual(self.en.count("data-step-badge="), 2)
        self.assertIn(">NIGHTLY</text>", self.en)
        self.assertIn(">NÄCHTLICH</text>", self.de)
        self.assertIn('<span class="chip">NIGHTLY</span>', self.en, "the badge is also in the step list")

    def test_node_tags_are_capitals_and_can_be_plain_or_a_pair(self):
        self.assertIn(">SOURCE</text>", self.en)
        self.assertIn(">SOURCE</text>", self.de)
        self.assertIn(">PEOPLE</text>", self.en)
        self.assertIn(">MENSCHEN</text>", self.de)

    def test_viewbox_height_is_the_lowest_box_or_line_plus_20(self):
        # wide: lowest box is "analyst" (y 250 + 88); tall: "analyst" (y 500 + 88); data model: "files" (270 + 126)
        self.assertIn('viewBox="0 0 1000 358"', self.en)
        self.assertIn('viewBox="0 0 400 608"', self.en)
        self.assertIn('class="er" viewBox="0 0 1000 416"', self.en)

    def test_data_model_diagram_and_cards(self):
        s = parse(self.en)
        self.assertEqual(s.count("svg", **{"class": "er"}), 1)
        self.assertEqual(s.count("g", **{"class": "ent lib", "data-entity": "files"}), 1)
        self.assertEqual(self.en.count('class="ent"'), 2)
        self.assertEqual(self.en.count('class="keybox"'), 4, "PK/FK marks: 1 + 2 + 1")
        self.assertEqual(self.en.count('class="rel-g"'), 3)
        self.assertEqual(s.count("li", **{"class": "er-card"}), 2)
        self.assertEqual(s.count("li", **{"class": "er-card lib"}), 1)
        self.assertIn("<li>1 station → many readings</li>", self.en)
        self.assertIn("<li>1 Station → viele Messwerte</li>", self.de)
        self.assertIn('<span class="legend">Dashed border: document library or file store.</span>', self.en)
        self.assertIn('<abbr class="key" title="primary key">PK</abbr>', self.en)
        self.assertIn('<abbr class="key" title="Primärschlüssel">PK</abbr>', self.de)

    def test_crows_feet_and_ticks_follow_the_cardinality(self):
        # three one-to-many relations: three ticks (one side) and three crow's feet (many side, three strokes each)
        marks = re.findall(r'<g class="rel-g" data-relation="[^"]+"><path class="rel" d="[^"]+"/><path class="rel" d="([^"]+)"/></g>', self.en)
        self.assertEqual(len(marks), 3)
        for d in marks:
            self.assertEqual(d.count("M"), 4, d)  # 1 tick + 3 strokes of the foot

    def test_decisions_role_result_and_footer(self):
        self.assertEqual(parse(self.en).count("article", **{"class": "decision"}), 3)
        self.assertIn('<div class="cards reveal" data-count="3">', self.en)
        self.assertEqual(self.en.count("<li>Designed the table layout"), 1)
        self.assertIn('<time datetime="2026-10-26">Facts as of 26 October 2026</time>', self.en)
        self.assertIn('<time datetime="2026-10-26">Stand der Angaben: 26. Oktober 2026</time>', self.de)
        self.assertIn("Generated from one content file per project. No trackers, no cookies.", self.en)
        self.assertIn('<a href="https://github.com/HARISPAARTAN/HARISPAARTAN.github.io">Source</a>', self.en)
        self.assertIn("Aus einer Inhaltsdatei pro Projekt erzeugt. Keine Tracker, keine Cookies.", self.de)
        self.assertIn("The demos use the fictional Nordstern Projektmanagement GmbH.", self.en)
        self.assertIn("Die Demos nutzen die fiktive Nordstern Projektmanagement GmbH.", self.de)
        self.assertIn('&copy; <span id="year">2026</span> Harithas Harikaran', self.en)

    def test_footer_notice_can_be_replaced_per_project(self):
        text = mutate(fixture_text(), 'facts_as_of = 2026-10-26\n',
                      'facts_as_of = 2026-10-26\nnotice.en = "Public demos only."\nnotice.de = "Nur öffentliche Demos."\n')
        ws, result = built(self, text)
        self.assertIn('<p class="cs-notice">Public demos only.</p>', html_of(result, ws, "en"))
        self.assertIn('<p class="cs-notice">Nur öffentliche Demos.</p>', html_of(result, ws, "de"))

    def test_sections_without_notes_still_render(self):
        text = fixture_text()
        a, b = text.index("[[why.notes]]"), text.index("[flow]")
        ws, result = built(self, text[:a] + text[b:])
        self.assertEqual(messages(result.errors), [])
        self.assertIn('<div class="two reveal one">', html_of(result, ws))
        self.assertNotIn('class="aside"', html_of(result, ws))

    def test_list_page(self):
        page = self.result.outputs[self.ws.out / "index.html"]
        self.assertIn('<html lang="en">', page)
        self.assertIn('<link rel="canonical" href="https://harispaartan.github.io/work/">', page)
        self.assertIn('<h2><a href="example-pipeline/">Example pipeline</a></h2>', page)
        self.assertIn('<a href="example-pipeline/" lang="en" hreflang="en">Read in English</a>', page)
        self.assertIn('<a href="example-pipeline/de/" lang="de" hreflang="de">Auf Deutsch lesen</a>', page)
        self.assertIn('href="../assets/css/site.css"', page)
        self.assertNotIn("hreflang=\"x-default\"", page)

    def test_generated_marker_names_the_content_file(self):
        self.assertIn("<!-- Generated by tools/build_case_studies.py from example-pipeline.toml.", self.en)

    def test_player_hooks_exist_in_the_shared_script_and_stylesheet(self):
        js = (REPO / "assets" / "js" / "case-study.js").read_text(encoding="utf-8")
        css = (REPO / "assets" / "css" / "case-study.css").read_text(encoding="utf-8")
        for hook in ("data-cs-flow", "data-cs-caption", "data-cs-toggle", "data-cs-toggle-label", "data-step-badge",
                     "data-nodes", "data-edges", "data-title", "data-caption", "data-play", "data-pause", "data-interval",
                     "data-node", "data-edge", "'.steps > li'", "svg.flow"):
            self.assertIn(hook, js, f"case-study.js does not use {hook}")
        self.assertIn("is-ready", js, "the toolbar appears only once the player has started")
        self.assertIn(".is-ready .toolbar", css)
        for cls in (".flow", ".node", ".edge", ".pill", ".steps", ".step", ".toolbar", ".er", ".er-card", ".cards", ".pager", ".chip"):
            self.assertIn(cls, css, f"case-study.css has no rule for {cls}")


# ---------------------------------------------------------------- validation

class Validation(unittest.TestCase):
    def errors_for(self, old: str, new: str, count: int = 1) -> list[str]:
        ws, result = built(self, mutate(fixture_text(), old, new, count))
        self.assertTrue(result.errors, f"expected errors for replacing {old!r}")
        return messages(result.errors)

    def assertError(self, errors: list[str], *parts: str) -> None:
        hit = [e for e in errors if all(p in e for p in parts)]
        self.assertTrue(hit, f"no error containing {parts}; got:\n" + "\n".join(errors))

    def test_message_names_file_toml_path_and_problem(self):
        errors = self.errors_for('title.de = "Feldsensoren"\n', "")
        self.assertEqual(len(errors), 1, errors)
        self.assertRegex(errors[0], r"example-pipeline\.toml: flow\.nodes\[sensors\]\.title\.de: missing German text")

    def test_all_problems_are_reported_in_one_run(self):
        text = mutate(fixture_text(), 'title.de = "Feldsensoren"\n', "")
        text = mutate(text, 'nodes = ["sensors", "ingest"]', 'nodes = ["sensors", "ingset"]')
        ws, result = built(self, text)
        errors = messages(result.errors)
        self.assertEqual(len(errors), 2, errors)
        self.assertError(errors, "title.de")
        self.assertError(errors, "flow.steps[collect].nodes[2]", 'unknown node "ingset"', 'did you mean "ingest"')

    def test_missing_english_or_german_text(self):
        self.assertError(self.errors_for('subtitle.de = "Stündliche Messwerte von Feldsensoren, geprüft, gespeichert und zusammengefasst"\n', ""),
                         "hero.subtitle.de", "missing German text")
        self.assertError(self.errors_for('role.en = "reads the report"\n', ""), "flow.nodes[analyst].role.en", "missing English text")

    def test_empty_text(self):
        self.assertError(self.errors_for('role.en = "reads the report"', 'role.en = "   "'), "flow.nodes[analyst].role.en", "English text is empty")
        self.assertError(self.errors_for('title.en = "Analyst"', 'title.en = ""'), "flow.nodes[analyst].title.en", "empty")

    def test_a_plain_string_is_not_a_pair(self):
        self.assertError(self.errors_for('subtitle.en = "Hourly readings from field sensors, checked, stored and summarised"\n'
                                         'subtitle.de = "Stündliche Messwerte von Feldsensoren, geprüft, gespeichert und zusammengefasst"',
                                         'subtitle = "one text for both"'),
                         "hero.subtitle", "must be a pair", "hero.subtitle.en")

    def test_unknown_language_key(self):
        self.assertError(self.errors_for('title.de = "Analyst"', 'title.de = "Analyst"\ntitle.fr = "Analyste"'), "flow.nodes[analyst].title.fr", 'unknown language "fr"')

    def test_unknown_node_edge_and_entity_references(self):
        self.assertError(self.errors_for('nodes = ["store", "summary"]', 'nodes = ["store", "sumary"]'),
                         "flow.steps[summarise].nodes[2]", 'unknown node "sumary"', 'did you mean "summary"')
        self.assertError(self.errors_for('edges = ["e4"]', 'edges = ["e9"]'), "flow.steps[report].edges[1]", 'unknown edge "e9"')
        self.assertError(self.errors_for('wide = ["sensors.right", "ingest.left"]', 'wide = ["sensor.right", "ingest.left"]'),
                         "flow.edges[e1].wide[1]", 'unknown node "sensor"', 'did you mean "sensors"')
        self.assertError(self.errors_for('tall = ["summary.bottom", "analyst.top"]', 'tall = ["summary.bottom", "analyze.top"]'),
                         "flow.edges[e4].tall[2]", 'unknown node "analyze"')
        self.assertError(self.errors_for('to = "readings"\ncardinality = "one-to-many"\nwide = ["stations.right@0.35"',
                                         'to = "reading"\ncardinality = "one-to-many"\nwide = ["stations.right@0.35"'),
                         "model.relations[#1].to", 'unknown entity "reading"', 'did you mean "readings"')
        self.assertError(self.errors_for('node = "summary", text.en', 'node = "nowhere", text.en'),
                         "flow.steps[summarise].badge.node", 'unknown node "nowhere"')

    def test_relation_anchors_must_belong_to_its_entities(self):
        self.assertError(self.errors_for('wide = ["files.top", "readings.bottom"]', 'wide = ["stations.top", "readings.bottom"]'),
                         "model.relations[#2].wide", 'must start on "files"')

    def test_exactly_four_stat_tiles(self):
        tile = '[[hero.stats]]\nvalue = "4"\nlabel.en = "steps from file to report"\nlabel.de = "Schritte von der Datei zum Bericht"\n'
        self.assertError(self.errors_for(tile, ""), "hero.stats", "exactly 4 stat tiles, found 3")
        self.assertError(self.errors_for(tile, tile + tile.replace('"4"', '"5"')), "hero.stats", "exactly 4 stat tiles, found 5")

    def test_text_wider_than_its_box_is_reported_per_layout(self):
        errors = self.errors_for('role.en = "reads the report"', 'role.en = "reads the report every single morning before the others"')
        self.assertError(errors, "flow.nodes[analyst].role.en", "wide layout, box 160 wide", "shorten it to about 22 characters")
        self.assertError(errors, "flow.nodes[analyst].role.en", "tall layout, box 300 wide")
        # the tag is measured in capitals and with its letter spacing: 12 characters x 6.8 = 82 units
        self.assertError(self.errors_for('tag = "SOURCE"', 'tag = "A VERY LONG TAG THAT NEVER ENDS"'), "flow.nodes[sensors].tag", "wide layout")
        self.assertError(self.errors_for('name.en = "Stations"', 'name.en = "Weather stations at every site"'), "model.entities[stations].name.en", "data model")
        self.assertError(self.errors_for('{ name.en = "Region", name.de = "Region" }', '{ name.en = "Region of the installation site", name.de = "Region" }'),
                         "model.entities[stations].fields[2].name.en")

    def test_a_text_that_fits_is_accepted(self):
        ws, result = built(self, mutate(fixture_text(), 'role.en = "reads the report"', 'role.en = "reads the report daily"'))
        self.assertEqual(messages(result.errors), [])

    def test_boxes_must_lie_inside_the_viewbox(self):
        self.assertError(self.errors_for("wide = [820, 250, 160]", "wide = [880, 250, 160]"),
                         "flow.nodes[analyst].wide", "wide layout", "ends at x = 1040", "only 1000 wide")
        self.assertError(self.errors_for("tall = [70, 500, 300]", "tall = [70, 500, 340]"),
                         "flow.nodes[analyst].tall", "tall layout", "ends at x = 410", "only 400 wide")
        self.assertError(self.errors_for("wide = [20, 40, 200]", "wide = [-10, 40, 200]"), "flow.nodes[sensors].wide", "x is -10")
        self.assertError(self.errors_for("wide = [340, 30, 250]", "wide = [800, 30, 250]"), "model.entities[readings].wide", "data model", "only 1000 wide")

    def test_boxes_must_not_overlap_or_touch(self):
        self.assertError(self.errors_for("wide = [560, 220, 200]", "wide = [560, 100, 200]"), "flow.nodes[summary].wide", 'overlaps "store"')
        self.assertError(self.errors_for("wide = [560, 220, 200]", "wide = [560, 130, 200]"), "flow.nodes[summary].wide", "closer than 4 units")
        self.assertError(self.errors_for("wide = [340, 270, 250]", "wide = [340, 150, 250]"), "model.entities[files].wide", 'overlaps "readings"')
        ws, result = built(self, mutate(fixture_text(), "wide = [560, 220, 200]", "wide = [560, 136, 200]"))
        self.assertEqual(messages(result.errors), [], "a gap of 8 units is fine")

    def test_anchor_syntax(self):
        self.assertError(self.errors_for('wide = ["ingest.right", "store.left"]', 'wide = ["ingest.rght", "store.left"]'),
                         "flow.edges[e2].wide[1]", 'bad anchor "ingest.rght"', "top, right, bottom, left")
        self.assertError(self.errors_for('wide = ["ingest.right", "store.left"]', 'wide = ["ingest", "store.left"]'), 'bad anchor "ingest"')
        self.assertError(self.errors_for('tall = ["sensors.bottom", "ingest.top"]', 'tall = ["sensors.bottom@1.5", "ingest.top"]'),
                         "flow.edges[e1].tall[1]", "between 0 and 1")
        self.assertError(self.errors_for('tall = ["sensors.bottom", "ingest.top"]', 'tall = ["sensors.bottom", "sensors.top"]'),
                         "flow.edges[e1].tall", "both anchors are on")
        self.assertError(self.errors_for('wide = ["ingest.right", "store.left"]', 'wide = ["ingest.right"]'), "flow.edges[e2].wide", "list of two anchors")

    def test_arrows_must_stay_inside_the_viewbox(self):
        # a corner connector that bulges out of the 1000-unit viewBox
        self.assertError(self.errors_for('wide = ["summary.right", "analyst.left"]', 'wide = ["summary.right", "analyst.right"]'),
                         "flow.edges[e4].wide", "leaves the viewBox")

    def test_coordinates_must_be_three_finite_numbers(self):
        self.assertError(self.errors_for("wide = [20, 40, 200]", "wide = [20, 40]"), "flow.nodes[sensors].wide", "three numbers")
        self.assertError(self.errors_for("wide = [20, 40, 200]", 'wide = [20, "40", 200]'), "flow.nodes[sensors].wide", "three numbers")
        self.assertError(self.errors_for("wide = [20, 40, 200]", "wide = [20, 40, nan]"), "flow.nodes[sensors].wide", "three numbers")
        self.assertError(self.errors_for("wide = [20, 40, 200]", "wide = [20, 40, 0]"), "flow.nodes[sensors].wide", "greater than 0")

    def test_duplicate_ids(self):
        self.assertError(self.errors_for('id = "e2"', 'id = "e1"'), "duplicate edge id", '"e1"')
        self.assertError(self.errors_for('id = "validate"', 'id = "collect"'), "duplicate step id")
        self.assertError(self.errors_for('id = "files"', 'id = "readings"'), "duplicate entity id")

    def test_id_format(self):
        self.assertError(self.errors_for('id = "e3"', 'id = "E 3"'), "flow.edges", "invalid value")

    def test_unknown_keys_get_a_suggestion(self):
        self.assertError(self.errors_for("facts_as_of =", "facts_as_off ="), "meta.facts_as_off", 'unknown key', 'did you mean "facts_as_of"')
        self.assertError(self.errors_for("[decisions]\n", "[decisions]\nheadline.en = \"x\"\n"), "decisions.headline", "unknown key")
        self.assertError(self.errors_for("[result]\n", "[result]\nfoo = 1\n[extra]\nbar = 2\n", 1), "extra", "unknown key")

    def test_slug_must_match_the_file_name(self):
        self.assertError(self.errors_for('slug = "example-pipeline"', 'slug = "other-name"'), "meta.slug", 'expected "example-pipeline", found "other-name"')
        self.assertError(self.errors_for('slug = "example-pipeline"', 'slug = "Example_Pipeline"'), "meta.slug", "invalid value")

    def test_meta_values(self):
        self.assertError(self.errors_for('status.en = "prototype"\nstatus.de = "Prototyp"', 'status = "live"'), "meta.status", "must be a pair of texts")
        self.assertError(self.errors_for('status.de = "Prototyp"', 'status.de = ""'), "meta.status.de", "German text is empty")
        self.assertError(self.errors_for("order = 1", "order = 0"), "meta.order", "at least 1")
        self.assertError(self.errors_for("order = 1", 'order = "1"'), "meta.order", "whole number")
        self.assertError(self.errors_for('tech = ["scripting", "relational store", "static pages"]', "tech = []"), "meta.tech", "at least 1")
        self.assertError(self.errors_for('demo_url = "https://example.org/demo/"', 'demo_url = "http://example.org/demo/"'), "meta.demo_url", "https://")
        self.assertError(self.errors_for("facts_as_of = 2026-10-26", 'facts_as_of = "yesterday"'), "meta.facts_as_of", "date")
        self.assertError(self.errors_for("facts_as_of = 2026-10-26", 'facts_as_of = 2026-10-26\nog_image = "/etc/passwd"'), "meta.og_image", "without a leading slash")

    def test_enumerated_values(self):
        self.assertError(self.errors_for('kind = "library"', 'kind = "table"'), "model.entities[files].kind", "allowed: list, library, object")
        self.assertError(self.errors_for('to = "files"\ncardinality = "one-to-many"', 'to = "files"\ncardinality = "lots"'),
                         "model.relations[#3].cardinality", "one-to-many")
        self.assertError(self.errors_for('{ key = "FK", name.en = "Station", name.de = "Station" },\n  { name.en = "Measured at"',
                                         '{ key = "XX", name.en = "Station", name.de = "Station" },\n  { name.en = "Measured at"'),
                         "model.entities[readings].fields[2].key", "allowed: PK, FK")

    def test_field_and_note_limits(self):
        self.assertError(self.errors_for('{ name.en = "Unit", name.de = "Einheit" },',
                                         '{ name.en = "Unit", name.de = "Einheit" },\n  { name.en = "Extra", name.de = "Extra" },'),
                         "model.entities[readings].fields", "at most 5 fields, found 6")
        note = '[[model.notes]]\ntitle.en = "N"\ntitle.de = "N"\ntext.en = "t"\ntext.de = "t"\n'
        self.assertError(self.errors_for("[decisions]", note * 2 + "\n[decisions]"), "model.notes", "at most 3 notes, found 4")

    def test_links_may_only_point_to_safe_targets(self):
        for bad in ("javascript:void", "data:text/html,x", "//evil.example/x", "mailto:someone@example.org", "ftp://example.org/x"):
            self.assertError(self.errors_for("[format reference](https://example.org/format)", f"[format reference]({bad})"), "hero.lead.en", "not allowed")
        for good in ("https://example.org/x?a=1&b=2", "http://example.org/", "/work/", "#how", "../x/", "./y"):
            ws, result = built(self, mutate(fixture_text(), "[format reference](https://example.org/format)", f"[format reference]({good})"))
            self.assertEqual(messages(result.errors), [], good)

    def test_step_texts_sit_inside_buttons_so_they_may_not_contain_links(self):
        self.assertError(self.errors_for("and stored. Readings outside the range are **kept apart**.", "and [stored](https://example.org/x)."),
                         "flow.steps[validate].text.en", "links are not allowed", "inside a button")
        ws, result = built(self, mutate(fixture_text(), "**ingest script**", "**ingest script** (bold is fine)"))
        self.assertEqual(messages(result.errors), [])

    def test_invalid_toml_is_reported_with_its_position(self):
        self.assertError(self.errors_for("[meta]", "[meta"), "TOML syntax error", "line")

    def test_missing_sections_are_reported(self):
        text = fixture_text()
        a, b = text.index("[model]"), text.index("[decisions]")
        text = text[:a] + text[b:]
        ws, result = built(self, text)
        errors = messages(result.errors)
        self.assertError(errors, "model", "missing required table [model]")

    def test_wrong_types_never_crash(self):
        for old, new in (('[hero]', 'hero = 5\n[hero_old]'), ("[flow]", "flow = []\n[flow_old]"), ('slug = "example-pipeline"', "slug = 12"),
                         ('tech = ["scripting", "relational store", "static pages"]', 'tech = "scripting"'),
                         ('nodes = ["sensors", "ingest"]', "nodes = 3"), ("wide = [20, 40, 200]", 'wide = "20,40,200"')):
            ws, result = built(self, mutate(fixture_text(), old, new))
            self.assertTrue(result.errors, old)

    def test_a_long_status_is_a_warning(self):
        ws, result = built(self, mutate(fixture_text(), 'status.en = "prototype"', 'status.en = "prototype, tested in the test pane and not yet published"'))
        self.assertFalse(result.errors, messages(result.errors))
        self.assertTrue(any("meta.status.en" in str(w) and "eyebrow" in str(w) for w in result.warnings), messages(result.warnings))

    def test_soft_limits_are_warnings_not_errors(self):
        text = fixture_text()
        a = text.index("[[decisions.items]]")
        b = text.index("[[decisions.items]]", a + 10)
        c = text.index("[[decisions.items]]", b + 10)
        ws, result = built(self, text[:c] + text[text.index("[role]"):])
        self.assertEqual(messages(result.errors), [])
        self.assertTrue(any("three or four decision cards" in str(w) for w in result.warnings), messages(result.warnings))

    def test_unused_nodes_and_arrows_are_warned_about(self):
        ws, result = built(self, mutate(fixture_text(), 'edges = ["e4"]', "edges = []"))
        self.assertEqual(messages(result.errors), [])
        self.assertTrue(any("flow.edges[e4]" in str(w) and "never lights up" in str(w) for w in result.warnings), messages(result.warnings))

    def test_a_line_through_another_box_is_warned_about(self):
        ws, result = built(self)
        self.assertFalse(any("passes through" in str(w) for w in result.warnings), "the fixture's lines are clean")
        # sensors -> store runs straight through the ingest box that sits between them
        old = 'id = "e2"\nwide = ["ingest.right", "store.left"]'
        text = mutate(fixture_text(), old, 'id = "e2"\nwide = ["sensors.right", "store.left"]')
        ws, result = built(self, text)
        self.assertEqual(messages(result.errors), [], "only advice, the build still succeeds")
        self.assertTrue(any("flow.edges[e2].wide" in str(w) and 'passes through "ingest"' in str(w) for w in result.warnings), messages(result.warnings))
        # data model: a relation drawn across an entity it does not join
        text = mutate(fixture_text(), 'wide = ["stations.bottom", "files.left"]', 'wide = ["stations.right@0.9", "files.right@0.2"]')
        ws, result = built(self, text)
        self.assertEqual(messages(result.errors), [])
        self.assertTrue(any("model.relations[stations->files].wide" in str(w) and 'passes through "readings"' in str(w) for w in result.warnings),
                        messages(result.warnings))

    def test_badge_text_is_shown_in_capitals(self):
        ws, result = built(self, mutate(fixture_text(), 'text.en = "NIGHTLY", text.de = "NÄCHTLICH"', 'text.en = "nightly", text.de = "nächtlich"'))
        self.assertEqual(messages(result.errors), [])
        self.assertIn(">NIGHTLY</text>", html_of(result, ws, "en"))
        self.assertIn('<span class="chip">NÄCHTLICH</span>', html_of(result, ws, "de"))

    def test_a_badge_pill_on_top_of_an_arrow_is_warned_about(self):
        # the e3 arrow meets the top of "summary" at its middle; the pill with pos = "center" would cover it
        ws, result = built(self, mutate(fixture_text(), 'badge = { node = "summary", text.en', 'badge = { node = "summary", pos = "center", text.en'))
        self.assertEqual(messages(result.errors), [])
        hits = [str(w) for w in result.warnings if "flow.steps[summarise].badge" in str(w) and 'arrow "e3"' in str(w)]
        self.assertEqual(len(hits), 2, "once per layout, not once per language: " + str(hits))
        self.assertFalse(any("badge pill sits" in str(w) for w in built(self)[1].warnings))

    def test_badge_on_a_dimmed_node_is_warned_about(self):
        ws, result = built(self, mutate(fixture_text(), 'badge = { node = "summary"', 'badge = { node = "sensors"'))
        self.assertEqual(messages(result.errors), [])
        self.assertTrue(any("badge" in str(w) and "dimmed" in str(w) for w in result.warnings), messages(result.warnings))

    def test_a_tall_badge_pill_outside_the_viewbox_is_an_error(self):
        errors = self.errors_for('tall = [30, 380, 340]', 'tall = [-60, 380, 340]')
        self.assertError(errors, "flow.nodes[summary].tall", "x is -60")

    def test_empty_content_folder(self):
        ws = Workspace(self)
        result = ws.build()
        self.assertEqual(len(result.errors), 1)
        self.assertIn("no content files found", str(result.errors[0]))

    def test_ui_toml_of_the_repository_is_complete(self):
        ui, report = bcs.load_ui(UI)
        self.assertEqual(messages(report.errors), [])
        self.assertIsNotNone(ui)
        for key in bcs.UI_KEYS:
            for lang in bcs.LANGS:
                if bcs.UI_KEYS[key] == "pair":
                    self.assertTrue(bcs.tr(ui, key, lang).strip(), f"{key}.{lang}")
        self.assertNotEqual(bcs.tr(ui, "hero.demo", "en"), bcs.tr(ui, "hero.demo", "de"))

    def test_ui_errors_name_the_file_and_the_key(self):
        ws, _ = built(self)
        broken = ws.root / "ui.toml"
        text = UI.read_text(encoding="utf-8")
        broken.write_text(mutate(text, 'pause = { en = "Pause", de = "Pause" }\n', 'pause = { en = "Pause" }\n'), encoding="utf-8")
        ui, report = bcs.load_ui(broken)
        self.assertIsNone(ui)
        self.assertEqual(len(report.errors), 1)
        self.assertRegex(str(report.errors[0]), r"ui\.toml: flow\.pause\.de: missing German text")
        broken.write_text(mutate(text, '[date]\n', '[date]\nunexpected = { en = "x", de = "y" }\n'), encoding="utf-8")
        _, report = bcs.load_ui(broken)
        self.assertTrue(any("date.unexpected" in str(e) and "unknown interface string" in str(e) for e in report.errors))
        broken.write_text(text.replace('"November", "December"]', '"November"]', 1), encoding="utf-8")
        _, report = bcs.load_ui(broken)
        self.assertTrue(any("date.months.en" in str(e) and "twelve" in str(e) for e in report.errors), messages(report.errors))
        broken.write_text(text.replace("[flow]", "[flo]"), encoding="utf-8")
        _, report = bcs.load_ui(broken)
        self.assertTrue(any("flow.title" in str(e) and "missing" in str(e) for e in report.errors))


# ---------------------------------------------------------------- pager, neighbours and --only

class Neighbours(unittest.TestCase):
    def three(self) -> Workspace:
        ws = Workspace(self)
        ws.write("alpha-case", derive("alpha-case", 1, "Alpha case", "Alpha-Fall"))
        ws.write("beta-case", derive("beta-case", 2, "Beta case", "Beta-Fall"))
        ws.write("gamma-case", derive("gamma-case", 3, "Gamma case", "Gamma-Fall"))
        return ws

    def test_full_build_links_previous_and_next_in_the_same_language(self):
        ws = self.three()
        result = ws.build()
        self.assertEqual(messages(result.errors), [])
        beta_en, beta_de = html_of(result, ws, "en", "beta-case"), html_of(result, ws, "de", "beta-case")
        self.assertIn('<a href="../alpha-case/" rel="prev"><small>← previous case study</small><span>Alpha case</span></a>', beta_en)
        self.assertIn('<a class="next" href="../gamma-case/" rel="next"><small>next case study →</small><span>Gamma case</span></a>', beta_en)
        self.assertIn('<a href="../../alpha-case/de/" rel="prev"><small>← vorherige Fallstudie</small><span>Alpha-Fall</span></a>', beta_de)
        self.assertIn('<a class="next" href="../../gamma-case/de/" rel="next"><small>nächste Fallstudie →</small><span>Gamma-Fall</span></a>', beta_de)
        self.assertIn("02 / 03", beta_en)

    def test_first_page_leads_back_and_last_page_leads_on_to_the_work_section(self):
        ws = self.three()
        result = ws.build()
        alpha_en, alpha_de = html_of(result, ws, "en", "alpha-case"), html_of(result, ws, "de", "alpha-case")
        gamma_en, gamma_de = html_of(result, ws, "en", "gamma-case"), html_of(result, ws, "de", "gamma-case")
        self.assertIn('<a href="../../#work" rel="prev"><small>← portfolio</small><span>Selected work at S01</span></a>', alpha_en)
        self.assertIn('<a href="../../../#work" rel="prev"><small>← Portfolio</small><span>Ausgewählte Projekte bei S01</span></a>', alpha_de)
        self.assertIn('<a class="next" href="../../#work" rel="next"><small>portfolio →</small>', gamma_en)
        self.assertIn('<a class="next" href="../../../#work" rel="next"><small>Portfolio →</small>', gamma_de)
        self.assertEqual(len(result.outputs), 7)

    def test_list_page_is_ordered_by_meta_order(self):
        ws = self.three()
        page = ws.build().outputs[ws.out / "index.html"]
        self.assertLess(page.index("Alpha case"), page.index("Beta case"))
        self.assertLess(page.index("Beta case"), page.index("Gamma case"))

    def test_full_build_requires_consecutive_orders(self):
        ws = Workspace(self)
        ws.write("alpha-case", derive("alpha-case", 1, "Alpha"))
        ws.write("gamma-case", derive("gamma-case", 3, "Gamma"))
        errors = messages(ws.build().errors)
        self.assertEqual(len(errors), 1)
        self.assertIn("exactly 1..2", errors[0])
        self.assertIn("alpha-case=1, gamma-case=3", errors[0])
        ws.write("gamma-case", derive("gamma-case", 1, "Gamma"))
        self.assertIn("exactly 1..2", messages(ws.build().errors)[0])

    def test_only_writes_just_its_two_pages(self):
        ws = self.three()
        result = ws.build(only="beta-case")
        self.assertEqual(messages(result.errors), [])
        self.assertEqual(sorted(p.relative_to(ws.out).as_posix() for p in result.outputs), ["beta-case/de/index.html", "beta-case/index.html"])
        self.assertEqual(messages(result.warnings), [])
        code, out, err = ws.main("--only", "beta-case")
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(p.relative_to(ws.out).as_posix() for p in ws.out.rglob("*.html")), ["beta-case/de/index.html", "beta-case/index.html"])

    def test_only_output_equals_the_full_build_output_for_that_slug(self):
        ws = self.three()
        full = ws.build()
        only = ws.build(only="beta-case")
        for lang in ("en", "de"):
            self.assertEqual(html_of(only, ws, lang, "beta-case"), html_of(full, ws, lang, "beta-case"))

    def test_only_survives_broken_incomplete_or_missing_neighbours(self):
        for label, neighbour in (
            ("invalid TOML", "[meta\nslug = "),
            ("empty file", ""),
            ("no order", '[meta]\nslug = "alpha-case"\n'),
            ("incomplete content", '[meta]\nslug = "alpha-case"\norder = 1\n'),
            ("wrong types", '[meta]\nslug = 5\norder = "x"\n[hero]\ntitle = 3\n'),
        ):
            with self.subTest(label):
                ws = Workspace(self)
                ws.write("beta-case", derive("beta-case", 2, "Beta case", "Beta-Fall"))
                ws.write("alpha-case", neighbour)
                ws.write("gamma-case", "this is not toml at all")
                result = ws.build(only="beta-case")
                self.assertEqual(messages(result.errors), [], label)
                self.assertEqual(len(result.outputs), 2)
                page = html_of(result, ws, "en", "beta-case")
                self.assertEqual(page.count("#work"), 2 if label == "incomplete content" else 3, label)  # crumb + fallbacks
                if label == "incomplete content":
                    # order and slug are readable, the title is not: the link still works, labelled with the slug
                    self.assertIn('<a href="../alpha-case/" rel="prev"><small>← previous case study</small><span>alpha-case</span></a>', page)
                    self.assertTrue(any("hero.title" in str(w) for w in result.warnings), messages(result.warnings))
                else:
                    self.assertIn('<a href="../../#work" rel="prev">', page)
                    self.assertTrue(any("previous" in str(w) and "falls back" in str(w) for w in result.warnings), messages(result.warnings))
                self.assertTrue(any('"next" link falls back' in str(w) for w in result.warnings), messages(result.warnings))

    def test_only_with_a_lone_file_and_a_high_order(self):
        ws = Workspace(self)
        ws.write("zeta-case", derive("zeta-case", 5, "Zeta case"))
        result = ws.build(only="zeta-case")
        self.assertEqual(messages(result.errors), [])
        self.assertIn("05 / 05", html_of(result, ws, "en", "zeta-case"))
        self.assertEqual(len([w for w in result.warnings if "falls back" in str(w)]), 1, "only the missing previous neighbour is reported")

    def test_only_reports_errors_of_its_own_file_and_writes_nothing(self):
        ws = Workspace(self)
        ws.write("beta-case", mutate(derive("beta-case", 2, "Beta"), 'title.de = "Feldsensoren"\n', ""))
        code, out, err = ws.main("--only", "beta-case")
        self.assertEqual(code, 1)
        self.assertIn("beta-case.toml: flow.nodes[sensors].title.de: missing German text", err)
        self.assertFalse(ws.out.exists())

    def test_only_unknown_slug(self):
        ws = self.three()
        code, out, err = ws.main("--only", "nope")
        self.assertEqual(code, 1)
        self.assertIn('no content file for slug "nope"', err)
        self.assertIn("alpha-case", err)
        code, out, err = ws.main("--only", "../beta-case")
        self.assertEqual(code, 1)

    def test_only_warns_about_duplicate_orders_and_slug_mismatch(self):
        ws = Workspace(self)
        ws.write("beta-case", derive("beta-case", 2, "Beta"))
        ws.write("also-beta", derive("also-beta", 2, "Also beta"))
        ws.write("alpha-case", mutate(derive("alpha-case", 1, "Alpha"), 'slug = "alpha-case"', 'slug = "alfa-case"'))
        result = ws.build(only="beta-case")
        self.assertEqual(messages(result.errors), [])
        text = " ".join(messages(result.warnings))
        self.assertIn("also claimed by another content file", text)
        self.assertIn('slug "alfa-case" differs from the file name', text)

    def test_only_does_not_touch_other_files_in_the_output_folder(self):
        ws = self.three()
        ws.main()
        stamp = {p: p.read_bytes() for p in ws.out.rglob("*.html")}
        (ws.out / "alpha-case" / "index.html").write_text("hand edited", encoding="utf-8")
        ws.main("--only", "beta-case")
        self.assertEqual((ws.out / "alpha-case" / "index.html").read_text(encoding="utf-8"), "hand edited")
        self.assertEqual((ws.out / "gamma-case" / "index.html").read_bytes(), stamp[ws.out / "gamma-case" / "index.html"])


# ---------------------------------------------------------------- determinism, line endings, paths, escaping

class Output(unittest.TestCase):
    def test_two_builds_are_byte_identical(self):
        ws, first = built(self)
        second = ws.build()
        self.assertEqual({p: t.encode() for p, t in first.outputs.items()}, {p: t.encode() for p, t in second.outputs.items()})
        ws.main()
        before = {p: p.read_bytes() for p in ws.out.rglob("*.html")}
        ws.main()
        self.assertEqual(before, {p: p.read_bytes() for p in ws.out.rglob("*.html")})

    def test_files_are_utf8_with_lf_endings_and_a_final_newline(self):
        ws, _ = built(self)
        ws.main()
        files = list(ws.out.rglob("*.html"))
        self.assertEqual(len(files), 3)
        for path in files:
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, path.name)
            self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n"), path)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            raw.decode("utf-8")
        self.assertIn("Stündliche Messwerte".encode("utf-8"), (ws.out / SLUG / "de" / "index.html").read_bytes())

    def test_rewriting_unchanged_pages_leaves_them_alone(self):
        ws, _ = built(self)
        ws.main()
        code, out, err = ws.main()
        self.assertEqual(code, 0)
        self.assertEqual(len(re.findall(r"^unchanged ", out, re.M)), 3)
        self.assertNotRegex(out, r"(?m)^wrote ")
        self.assertIn("Built 3 page(s): 0 written, 3 unchanged.", out)

    def test_asset_and_page_paths_are_relative_to_each_pages_depth(self):
        ws, result = built(self)
        en, de = html_of(result, ws, "en"), html_of(result, ws, "de")
        lst = result.outputs[ws.out / "index.html"]
        for page, prefix in ((en, "../../"), (de, "../../../"), (lst, "../")):
            for asset in ("css/site.css", "css/case-study.css", "js/site.js", "js/case-study.js", "img/favicon.svg",
                          "fonts/inter-latin-wght-normal.woff2", "fonts/space-grotesk-latin-wght-normal.woff2"):
                if asset == "img/favicon.svg" or asset.startswith("fonts") or asset.startswith(("css", "js")):
                    self.assertIn(f'"{prefix}assets/{asset}"', page, f"{prefix} {asset}")
            self.assertIn(f'<a class="brand" href="{prefix}"', page)
            self.assertNotRegex(page, r'(href|src)="(?!https?://|\.\.?/|#|\./|[a-z0-9-]+/)[^"]*"' if page is not lst else r"$^")
        self.assertIn('<a href="../../#work">work</a>', en)
        self.assertIn('<a href="../../../#work">projekte</a>', de)
        self.assertIn('href="../../../assets/css/case-study.css"', de)

    def test_no_absolute_local_paths_or_timestamps_leak_into_pages(self):
        ws, result = built(self)
        for page in result.outputs.values():
            self.assertNotIn(str(ws.root), page)
            self.assertNotIn(ws.root.as_posix(), page)
            self.assertNotRegex(page, r"(?<![A-Za-z])[A-Za-z]:[\\/]")
            self.assertNotRegex(page, r"\b\d{2}:\d{2}:\d{2}\b")

    def test_pages_make_no_requests_to_other_hosts(self):
        ws, result = built(self)
        for page in result.outputs.values():
            urls = re.findall(r'(?:src|href)="(https?://[^"]+)"', page)
            for url in urls:
                self.assertRegex(url, r"^https://(harispaartan\.github\.io|github\.com/HARISPAARTAN|example\.org)/", url)
            self.assertNotRegex(page, r'<(script|link|img|iframe)[^>]+(src|href)="https?://(?!harispaartan\.github\.io)(?!github\.com)')

    def test_text_is_escaped_everywhere(self):
        evil = '<script>alert(1)</script> & "quoted" \'single\''
        text = mutate(fixture_text(), 'title.en = "Example pipeline"', f"title.en = {json.dumps(evil)}")
        quoted = 'Say "hi" <b>'
        text = mutate(text, 'title.en = "Check and store"', f"title.en = {json.dumps(quoted)}")
        text = mutate(text, 'tag = "SOURCE"', 'tag = "A&B"')
        ws, result = built(self, text)
        self.assertEqual(messages(result.errors), [])
        en = html_of(result, ws, "en")
        for page in (en, html_of(result, ws, "de")):
            self.assertNotIn("<script>alert", page)
            self.assertNotIn('hi" <b>', page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;quoted&quot; &#x27;single&#x27;", en)
        self.assertIn('data-title="Say &quot;hi&quot; &lt;b&gt;"', en)
        self.assertIn("<b>Say &quot;hi&quot; &lt;b&gt;</b>", en)
        self.assertIn(">A&amp;B</text>", en)
        self.assertEqual(parse(en).problems, [])

    def test_inline_markup_is_limited_to_bold_and_links(self):
        self.assertEqual(bcs.inline("plain"), "plain")
        self.assertEqual(bcs.inline("a **bold** word"), "a <strong>bold</strong> word")
        self.assertEqual(bcs.inline("see [the page](https://example.org/x?a=1&b=2) now"),
                         'see <a href="https://example.org/x?a=1&amp;b=2">the page</a> now')
        self.assertEqual(bcs.inline("[a](#how) and [b](/work/)"), '<a href="#how">a</a> and <a href="/work/">b</a>')
        # everything else is escaped text
        self.assertEqual(bcs.inline("*not italic* and `not code`"), "*not italic* and `not code`")
        self.assertEqual(bcs.inline("<b>raw</b> & <i>html</i>"), "&lt;b&gt;raw&lt;/b&gt; &amp; &lt;i&gt;html&lt;/i&gt;")
        self.assertEqual(bcs.inline("**open only"), "**open only")
        self.assertEqual(bcs.inline("[no url]() and [x](two words)"), "[no url]() and [x](two words)")
        self.assertEqual(bcs.inline('**<a href="x">**'), "<strong>&lt;a href=&quot;x&quot;&gt;</strong>")
        self.assertEqual(bcs.inline('[x"onmouseover="y](https://example.org/"a)'), '<a href="https://example.org/&quot;a">x&quot;onmouseover=&quot;y</a>')
        self.assertEqual(bcs.plain("a **b** [c](https://example.org/)"), "a b c")

    def test_markup_in_a_paragraph_reaches_the_page(self):
        ws, result = built(self)
        en = html_of(result, ws)
        self.assertIn('<strong>This pipeline is invented</strong>: it exists', en)
        self.assertIn('<a href="https://example.org/format">format reference</a>', en)
        self.assertIn('<strong>The pipeline checks first and stores second.</strong>', en)
        self.assertIn("Readings outside the range are <strong>kept apart</strong>.", en)
        self.assertIn('content="Field sensors write one file per hour.', en)
        self.assertNotIn('content="Field sensors write one file per hour. A small script checks every reading against its allowed range, stores it in a relational table and builds a daily summary for the analyst. **', en)

    def test_whitespace_in_multiline_strings_is_collapsed(self):
        ws, result = built(self)
        self.assertNotRegex(html_of(result, ws), r"<p class=\"lead\">[^<]*\n")
        self.assertIn("Field sensors write one file per hour. A small script checks every reading against its allowed range, stores it in a relational table and builds",
                      html_of(result, ws))


# ---------------------------------------------------------------- --check and writing

class CheckMode(unittest.TestCase):
    def setUp(self) -> None:
        self.ws, _ = built(self)
        self.assertEqual(self.ws.main()[0], 0)

    def test_current_pages_pass(self):
        code, out, err = self.ws.main("--check")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("3 page(s) are current", out)

    def test_an_edited_page_fails_and_is_named(self):
        page = self.ws.out / SLUG / "index.html"
        page.write_text(page.read_text(encoding="utf-8").replace("Example pipeline", "Edited by hand", 1), encoding="utf-8", newline="\n")
        code, out, err = self.ws.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("example-pipeline/index.html", err)
        self.assertIn("differs from the content files, first at line", err)
        self.assertNotIn("de/index.html", err)
        self.assertEqual(self.ws.main()[0], 0)
        self.assertEqual(self.ws.main("--check")[0], 0)

    def test_a_missing_page_fails(self):
        (self.ws.out / SLUG / "de" / "index.html").unlink()
        code, out, err = self.ws.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("de/index.html: missing", err)

    def test_crlf_line_endings_are_drift(self):
        page = self.ws.out / "index.html"
        page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))
        code, out, err = self.ws.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("line endings differ", err)

    def test_changed_content_fails_the_check(self):
        path = self.ws.content / f"{SLUG}.toml"
        path.write_text(mutate(path.read_text(encoding="utf-8"), 'value = "24"', 'value = "25"'), encoding="utf-8", newline="\n")
        code, out, err = self.ws.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("2 page(s) out of date", err)

    def test_invalid_content_fails_the_check_with_the_content_errors(self):
        path = self.ws.content / f"{SLUG}.toml"
        path.write_text(mutate(path.read_text(encoding="utf-8"), 'title.de = "Feldsensoren"\n', ""), encoding="utf-8", newline="\n")
        code, out, err = self.ws.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("flow.nodes[sensors].title.de: missing German text", err)

    def test_stale_generated_pages_fail_the_check_and_are_removed_by_a_build(self):
        stale = self.ws.out / "old-study" / "index.html"
        stale.parent.mkdir(parents=True)
        stale.write_text(f"<!doctype html>\n<!-- {bcs.GENERATED_MARK} from old-study.toml. -->\n", encoding="utf-8")
        handmade = self.ws.out / "notes" / "index.html"
        handmade.parent.mkdir()
        handmade.write_text("<!doctype html>\nmine\n", encoding="utf-8")
        code, out, err = self.ws.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("old-study/index.html: stale page", err)
        self.assertNotIn("notes", err)
        self.assertEqual(self.ws.main()[0], 0)
        self.assertFalse(stale.exists())
        self.assertFalse(stale.parent.exists(), "the empty folder goes too")
        self.assertTrue(handmade.exists(), "files this tool did not generate are never touched")
        self.assertEqual(self.ws.main("--check")[0], 0)

    def test_only_check_looks_at_one_slug(self):
        self.ws.write("second", derive("second", 2, "Second"))
        self.assertEqual(self.ws.main()[0], 0)  # two case studies now; then edit only the second one's page
        (self.ws.out / "second" / "index.html").write_text("changed", encoding="utf-8")
        self.assertEqual(self.ws.main("--check", "--only", SLUG)[0], 0)
        self.assertEqual(self.ws.main("--check", "--only", "second")[0], 1)

    def test_invalid_content_writes_nothing(self):
        ws = Workspace(self)
        ws.write("alpha-case", derive("alpha-case", 1, "Alpha"))
        ws.write("beta-case", mutate(derive("beta-case", 2, "Beta"), "[hero]", "[hero"))
        code, out, err = ws.main()
        self.assertEqual(code, 1)
        self.assertFalse(ws.out.exists())
        self.assertIn("1 error(s); nothing was written", err)


class Cli(unittest.TestCase):
    def run_cli(self, ws: Workspace, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "--content-dir", str(ws.content), "--ui", str(UI), "--out-dir", str(ws.out), *args],
                              capture_output=True, text=True, encoding="utf-8", cwd=cwd or ws.root)

    def test_exit_codes_and_streams(self):
        ws = Workspace(self)
        ws.write(SLUG, fixture_text())
        done = self.run_cli(ws)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Built 3 page(s): 3 written, 0 unchanged.", done.stdout)
        self.assertEqual(self.run_cli(ws, "--check").returncode, 0)
        ws.write(SLUG, mutate(fixture_text(), 'status.de = "Prototyp"', 'status.de = ""'))
        bad = self.run_cli(ws, "--check")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("error: ", bad.stderr)
        self.assertIn("meta.status", bad.stderr)
        self.assertEqual(self.run_cli(ws, "--bogus").returncode, 2)

    def test_unicode_in_paths_and_messages_survives_a_cp1252_console(self):
        # stdout of a legacy Windows console cannot show an arrow in a folder name; the script must not crash on it
        ws = Workspace(self)
        ws.out = ws.root / "site-→" / "work"
        key = '"untertitel→"'
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        args = [sys.executable, "-I", str(SCRIPT), "--content-dir", str(ws.content), "--ui", str(UI), "--out-dir", str(ws.out)]
        ws.write(SLUG, fixture_text())
        done = subprocess.run(args, capture_output=True, env=env, cwd=ws.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(b"wrote", done.stdout)
        ws.write(SLUG, mutate(fixture_text(), "[result]\n", f"[result]\n{key} = 'x'\n"))
        done = subprocess.run(args, capture_output=True, env=env, cwd=ws.root)
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn(b"unknown key", done.stderr)
        self.assertNotIn(b"Traceback", done.stderr)

    def test_runs_from_any_working_directory(self):
        ws = Workspace(self)
        ws.write(SLUG, fixture_text())
        other = ws.root / "elsewhere"
        other.mkdir()
        self.assertEqual(self.run_cli(ws, "--only", SLUG, cwd=other).returncode, 0)
        self.assertTrue((ws.out / SLUG / "de" / "index.html").is_file())

    def test_python_version_floor_is_declared(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("sys.version_info < (3, 11)", source)
        self.assertEqual(sorted(set(re.findall(r"^(?:import|from) (\w+)", source, re.M))),
                         sorted({"__future__", "sys", "argparse", "datetime", "difflib", "html", "math", "posixpath", "re", "tomllib", "dataclasses", "pathlib"}),
                         "standard library only")


# ---------------------------------------------------------------- geometry and helpers

class Geometry(unittest.TestCase):
    def test_fmt(self):
        self.assertEqual([bcs.fmt(v) for v in (1, 1.0, 1.5, 0.125, 100.004, -0.0, -0.001, 1000)], ["1", "1", "1.5", "0.12", "100", "0", "0", "1000"])

    def test_anchor_syntax(self):
        r = bcs.Report("t")
        a = bcs.parse_anchor(r, "app.right", "p", {"app": None}, "node")
        self.assertEqual((a.node, a.side, a.t), ("app", "right", 0.5))
        a = bcs.parse_anchor(r, "app.bottom@0.3", "p", {"app": None}, "node")
        self.assertEqual((a.side, a.t), ("bottom", 0.3))
        a = bcs.parse_anchor(r, "app.top@.25", "p", {"app": None}, "node")
        self.assertEqual(a.t, 0.25)
        self.assertEqual(bcs.parse_anchor(r, "app.top@1", "p", {"app": None}, "node").t, 1.0)
        self.assertEqual(bcs.parse_anchor(r, "app.top@0", "p", {"app": None}, "node").t, 0.0)
        self.assertEqual(r.errors, [])
        for bad in ("app", "app.", "app.middle", "App.right", "app.right@", "app.right@-1", "app.right@1.01", 5, "app.right@0.3@0.4", " "):
            self.assertIsNone(bcs.parse_anchor(r, bad, "p", {"app": None}, "node"), bad)
        self.assertEqual(len(r.errors), 10)

    def test_anchor_points_on_a_box(self):
        box = bcs.Box("b", 100, 50, 200, 88)
        self.assertEqual(bcs.anchor_xy(box, "top", 0.25), (150, 50))
        self.assertEqual(bcs.anchor_xy(box, "bottom", 1), (300, 138))
        self.assertEqual(bcs.anchor_xy(box, "left", 0.5), (100, 94))
        self.assertEqual(bcs.anchor_xy(box, "right", 0), (300, 50))

    def test_aligned_facing_anchors_get_a_straight_line(self):
        link = bcs.connect((200, 100), (1, 0), (260, 100), (-1, 0), gap=4, head=True)
        self.assertEqual(link.d, "M200,100 L247,100")
        self.assertEqual(link.head, "M256,100 L247,95.5 L247,104.5z")
        vertical = bcs.connect((635, 320), (0, -1), (635, 258), (0, 1), gap=4, head=True)
        self.assertEqual(vertical.d, "M635,320 L635,271")
        self.assertEqual(vertical.head, "M635,262 L630.5,271 L639.5,271z")
        plain = bcs.connect((10, 10), (1, 0), (50, 10), (-1, 0))
        self.assertEqual((plain.d, plain.head), ("M10,10 L50,10", ""))

    def test_other_anchors_get_a_cubic_curve_whose_control_points_follow_the_sides(self):
        link = bcs.connect((200, 340), (1, 0), (536, 364), (-1, 0), gap=4, head=True)
        self.assertTrue(link.d.startswith("M200,340 C"), link.d)
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", link.d)]
        sx, sy, c1x, c1y, c2x, c2y, ex, ey = nums
        self.assertEqual((sy, c1y), (340, 340), "first control point leaves to the right")
        self.assertGreater(c1x, sx)
        self.assertEqual(c2y, ey, "second control point arrives from the left")
        self.assertLess(c2x, ex)
        self.assertEqual(ex, 536 - 4 - bcs.HEAD_LEN)
        # a corner: out of a right side, into a top side
        corner = bcs.connect((100, 100), (1, 0), (300, 250), (0, -1))
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", corner.d)]
        self.assertEqual(nums[3], 100)       # first control point stays on the exit row
        self.assertEqual(nums[4], 300)       # second control point sits above the target
        self.assertLess(nums[5], 250)
        # misaligned by a hair still counts as in line, further away does not
        self.assertTrue(bcs.connect((0, 0), (1, 0), (100, 0.4), (-1, 0)).d.count("C") == 0)
        self.assertTrue(bcs.connect((0, 0), (1, 0), (100, 3), (-1, 0)).d.count("C") == 1)
        # target behind the exit side: an S-curve that does not fold back
        self.assertEqual(bcs.connect((100, 0), (1, 0), (50, 0), (-1, 0)).d.count("C"), 1)

    def test_s_curves_do_not_overshoot_on_short_distances(self):
        link = bcs.connect((200, 468), (0, 1), (220, 500), (0, -1), gap=4, head=True)
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", link.d)]
        _, sy, _, c1y, _, c2y, _, ey = nums
        self.assertLessEqual(c1y, ey)
        self.assertGreaterEqual(c2y, sy)

    def test_arrowhead_is_a_triangle_pointing_along_the_curve_end(self):
        link = bcs.connect((0, 0), (0, 1), (0, 100), (0, -1), gap=4, head=True)
        self.assertEqual(link.head, "M0,96 L4.5,87 L-4.5,87z")
        self.assertEqual(link.head.count("L"), 2)

    def test_text_width_estimate(self):
        self.assertAlmostEqual(bcs.text_width("x" * 10, bcs.ROLE_STYLE), 10 * 0.50 * 11.5)
        self.assertAlmostEqual(bcs.text_width("x" * 10, bcs.TITLE_STYLE), 10 * 0.50 * 16)
        self.assertAlmostEqual(bcs.text_width("x" * 10, bcs.TAG_STYLE), 10 * 0.68 * 10)
        self.assertAlmostEqual(bcs.text_width("x" * 10, bcs.ENOTE_STYLE), 10 * 0.6 * 10.5)

    def test_pill_geometry_straddles_the_top_edge_of_its_box(self):
        box = bcs.Box("b", 100, 100, 200, 88)
        x, y, w = bcs.pill_geometry(box, "OFFLINE", "right")
        self.assertEqual((y, w), (89, 7 * 7.0 + 20))
        self.assertEqual(x + w, 300 - 10)
        self.assertEqual(bcs.pill_geometry(box, "OFFLINE", "left")[0], 110)
        x, _, w = bcs.pill_geometry(box, "OFFLINE", "center")
        self.assertAlmostEqual(x + w / 2, 200)

    def test_short_description_takes_whole_sentences(self):
        text = "One short sentence. Another one follows here. " + "Long " * 80 + "end."
        self.assertEqual(bcs.short_description(text), "One short sentence. Another one follows here.")
        self.assertEqual(bcs.short_description("**Bold** [link](https://x.org/). Two."), "Bold link. Two.")

    def test_rel_url_and_root_prefix(self):
        self.assertEqual(bcs.rel_url("work/a", "work/a"), "./")
        self.assertEqual(bcs.rel_url("work/a", "work/a/de"), "de/")
        self.assertEqual(bcs.rel_url("work/a/de", "work/a"), "../")
        self.assertEqual(bcs.rel_url("work/a", "work/b/de"), "../b/de/")
        self.assertEqual(bcs.rel_url("work/a/de", "work/b/de", "#x"), "../../b/de/#x")
        self.assertEqual([bcs.root_prefix(d) for d in ("work", "work/a", "work/a/de")], ["../", "../../", "../../../"])

    def test_date_formatting(self):
        ui, _ = bcs.load_ui(UI)
        import datetime
        self.assertEqual(bcs.format_date(ui, "en", datetime.date(2026, 3, 5)), "5 March 2026")
        self.assertEqual(bcs.format_date(ui, "de", datetime.date(2026, 3, 5)), "5. März 2026")


# ---------------------------------------------------------------- SCHEMA.md stays true

class SchemaDocument(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = (REPO / "content" / "case-studies" / "SCHEMA.md").read_text(encoding="utf-8")

    def example(self) -> str:
        m = re.search(r"## Minimal complete example.*?```toml\n(.*?)\n```", self.doc, re.S)
        self.assertIsNotNone(m, "SCHEMA.md has no minimal example")
        return m.group(1)

    def test_the_minimal_example_builds_without_errors_or_warnings(self):
        ws = Workspace(self)
        ws.write("sample-tool", self.example())
        result = ws.build()
        self.assertEqual(messages(result.errors), [])
        self.assertEqual(messages(result.warnings), [])
        en = html_of(result, ws, "en", "sample-tool")
        self.assertIn('viewBox="0 0 1000 148"', en, "SCHEMA.md says the wide example ends at 128 and is 148 high")
        self.assertIn("Beispielwerkzeug", html_of(result, ws, "de", "sample-tool"))
        code, out, err = ws.main("--only", "sample-tool")
        self.assertEqual((code, err), (0, ""))

    def test_every_key_the_validator_accepts_is_documented(self):
        source = SCRIPT.read_text(encoding="utf-8")
        keys: set[str] = set()
        for m in re.finditer(r"check_unknown\(r, [^,]+, [^,]+, (\{[^}]*\})\)", source):
            keys |= set(eval(m.group(1)))  # a literal set of strings written in the script
        self.assertGreater(len(keys), 40)
        for key in sorted(keys):
            self.assertRegex(self.doc, rf"\b{re.escape(key)}\b", f"SCHEMA.md does not mention the key {key!r}")

    def test_the_capacity_table_matches_the_estimate_used_by_the_build(self):
        def per(style):
            return (bcs.GLYPH_EM[style[0]] + style[2]) * style[1]
        rows = re.findall(r"^\| (\d+) \| (\d+) \| (\d+) \| (\d+) \| \| (\d*) \| ?(\d*) \| ?(\d*) \| ?(\d*) \|$", self.doc, re.M)
        self.assertGreaterEqual(len(rows), 6)
        for w, tag, title, role, w2, name, note, field in rows:
            w = int(w)
            self.assertEqual((int(tag), int(title), int(role)),
                             (int((w - 28) // per(bcs.TAG_STYLE)), int((w - 28) // per(bcs.TITLE_STYLE)), int((w - 28) // per(bcs.ROLE_STYLE))), f"box {w}")
            if w2:
                w2 = int(w2)
                self.assertEqual((int(name), int(note), int(field)),
                                 (int((w2 - 24) // per(bcs.ENAME_STYLE)), int((w2 - 24) // per(bcs.ENOTE_STYLE)), int((w2 - 52) // per(bcs.EFIELD_STYLE))), f"entity {w2}")
        self.assertIn("| Node title | Space Grotesk 16 px | 8.0 |", self.doc)
        self.assertIn("| Node role | Inter 11.5 px | 5.75 |", self.doc)
        self.assertIn("| Node tag (capitals) | JetBrains Mono 10 px, letter-spacing 0.08 em | 6.8 |", self.doc)

    def test_the_documented_text_fit_message_is_the_real_one(self):
        quoted = re.search(r"`(text is about [^`]+)`", self.doc)
        self.assertIsNotNone(quoted)
        ws, result = built(self, mutate(fixture_text(), 'role.en = "one file per hour"', f'role.en = "{"a" * 30}"'))
        self.assertTrue(any(quoted.group(1) in str(e) for e in result.errors), messages(result.errors))

    def test_geometry_constants_quoted_in_the_document(self):
        self.assertEqual((bcs.NODE_H, bcs.ER_HEAD, bcs.ER_ROW, bcs.ER_PAD, bcs.MARGIN_BOTTOM, bcs.CLEARANCE), (88, 46, 24, 8, 20, 4))
        self.assertEqual((bcs.FLOW_WIDTH["wide"], bcs.FLOW_WIDTH["tall"], bcs.MODEL_WIDTH), (1000, 400, 1000))
        self.assertEqual((bcs.ARROW_GAP, bcs.HEAD_LEN, bcs.MAX_FIELDS), (4, 9, 5))
        for phrase in ("**Every flow box is 88 units high.**", "46 + 24 × (number of fields) + 8", "plus 20 units", "at least 4 units apart", "(a small triangle, 9 units long) ends 4 units before"):
            self.assertIn(phrase, self.doc)


# ---------------------------------------------------------------- the shared stylesheet stays on the portfolio's tokens

class Stylesheet(unittest.TestCase):
    def setUp(self) -> None:
        self.css = (REPO / "assets" / "css" / "case-study.css").read_text(encoding="utf-8")
        self.site = (REPO / "assets" / "css" / "site.css").read_text(encoding="utf-8")

    def test_only_tokens_of_site_css_are_used(self):
        defined = set(re.findall(r"(--[\w-]+)\s*:", self.site))
        own = set(re.findall(r"(--[\w-]+)\s*:", self.css))
        used = set(re.findall(r"var\((--[\w-]+)", self.css))
        self.assertEqual(sorted(used - defined - own), [])
        self.assertEqual(own, {"--accent-soft"}, "the only own property is a tint derived from --accent")

    def test_no_colour_literals(self):
        stripped = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)
        self.assertNotRegex(stripped, r"#[0-9a-fA-F]{3,8}\b")
        self.assertNotRegex(stripped, r"\b(rgb|rgba|hsl|hsla)\(")

    def test_dimming_uses_opacity_and_the_light_theme_selector_exists(self):
        self.assertRegex(self.css, r"\.flow \.node\.off \{ opacity: 0\.\d+; \}")
        self.assertRegex(self.css, r"\.flow \.edge\.off \{ opacity: 0\.\d+; \}")
        self.assertIn('html[data-theme="light"]', self.css)
        self.assertIn("prefers-reduced-motion: reduce", self.css)

    def test_breakpoints_match_the_player(self):
        js = (REPO / "assets" / "js" / "case-study.js").read_text(encoding="utf-8")
        self.assertIn("(min-width: 1000px)", js)
        self.assertIn("(min-width: 1000px)", self.css)
        self.assertIn("(max-width: 999.98px)", self.css)

    def test_script_has_no_network_use_or_dependencies(self):
        js = (REPO / "assets" / "js" / "case-study.js").read_text(encoding="utf-8")
        js = js.replace("http://www.w3.org/2000/svg", "")  # the SVG namespace is a name, not an address that is fetched
        for forbidden in ("fetch(", "XMLHttpRequest", "import ", "require(", "http://", "https://", "WebSocket", "sendBeacon", "localStorage.setItem"):
            self.assertNotIn(forbidden, js)
        self.assertLess(len(js.encode("utf-8")), 8000, "the player is meant to stay small")


if __name__ == "__main__":
    unittest.main()

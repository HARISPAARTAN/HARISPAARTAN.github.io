# harispaartan.github.io

Personal portfolio of Harithas Harikaran, Power Platform & Power BI Developer. Live at https://harispaartan.github.io/.

Hand-written HTML, CSS and a little JavaScript; the case-study pages under `work/` are generated from content files (see below) and committed, so GitHub Pages serves plain files. No framework, no trackers, no external requests: the three fonts (Inter, Space Grotesk, JetBrains Mono, all SIL Open Font License) are served from this repository.

## Structure

| Path | Purpose |
|---|---|
| `index.html` | The whole page: hero, work at S01, freelance projects, open-source projects, experience, skills, education, contact |
| `assets/css/site.css` | Design tokens (dark default, light by toggle), layout, print styles |
| `assets/js/site.js` | Theme toggle, mobile menu, scroll reveal |
| `assets/fonts/` | Self-hosted variable fonts and their licences |
| `assets/img/` | Favicon, Open Graph image, project thumbnails |
| `404.html` | Not-found page |
| `content/case-studies/` | One TOML file per case study (English and German), the shared interface strings `ui.toml` and the format reference `SCHEMA.md` |
| `work/` | Generated case-study pages: `work/<slug>/` (English), `work/<slug>/de/` (German) and the list `work/index.html` |
| `tools/build_case_studies.py` | Page generator (Python 3.11+, standard library only) with its tests and an invented fixture under `tools/fixtures/` |
| `assets/css/case-study.css`, `assets/js/case-study.js` | Styles of the case-study pages and the player of their animated architecture diagrams |

## Case studies

The first five S01 cards link to case studies that explain why each project exists, how it works (an animated architecture diagram), the data model, the main trade-offs, the work done and the result. They describe internal systems in simplified form: no client data, internal addresses or source code, and the demos use the fictional Nordstern Projektmanagement GmbH.

```
python tools/build_case_studies.py                 # build every page into work/
python tools/build_case_studies.py --only <slug>   # check one content file and build its two pages
python tools/build_case_studies.py --check         # fail if any content is invalid or a page is out of date
python -m unittest tools/test_build_case_studies.py
```

Edit the TOML files, never the generated pages. `content/case-studies/SCHEMA.md` lists every key, the diagram coordinates and the checks.

## Checks run before each publish

- Rendered with Playwright on Chrome at 360, 768 and 1280 px, the home page and every case-study page: no horizontal overflow, no console errors, no failed or external requests.
- Every link resolves; every image loads and carries `alt`, `width` and `height`.
- Every text colour pair in both themes measures at least 4.5:1 contrast (WCAG AA).

## Related sites under the same domain

- https://harispaartan.github.io/s01-demos/ (repo `s01-demos`, deployed by its own GitHub Actions workflow)
- https://harispaartan.github.io/ml-demos/ (repo `ml-demos`)

# harispaartan.github.io

Personal portfolio of Harithas Harikaran, Power Platform & Power BI Developer. Live at https://harispaartan.github.io/.

Hand-written HTML, CSS and a little JavaScript. No build step, no framework, no trackers, no external requests: the three fonts (Inter, Space Grotesk, JetBrains Mono, all SIL Open Font License) are served from this repository.

## Structure

| Path | Purpose |
|---|---|
| `index.html` | The whole page: hero, work at S01, open-source projects, experience, skills, education, contact |
| `assets/css/site.css` | Design tokens (dark default, light by toggle), layout, print styles |
| `assets/js/site.js` | Theme toggle, mobile menu, scroll reveal |
| `assets/fonts/` | Self-hosted variable fonts and their licences |
| `assets/img/` | Favicon, Open Graph image, project thumbnails |
| `404.html` | Not-found page |

## Checks run before each publish

- Rendered with Playwright on Chrome at 360, 768 and 1280 px: no horizontal overflow, no console errors, no failed or external requests.
- Every link resolves; every image loads and carries `alt`, `width` and `height`.
- Every text colour pair in both themes measures at least 4.5:1 contrast (WCAG AA).

## Related sites under the same domain

- https://harispaartan.github.io/s01-demos/ (repo `s01-demos`, deployed by its own GitHub Actions workflow)
- https://harispaartan.github.io/ml-demos/ (repo `ml-demos`)

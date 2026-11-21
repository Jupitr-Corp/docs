# Hikoo documentation project instructions

## About this project

- This is the **Hikoo** product documentation, built on [Mintlify](https://mintlify.com).
- Hikoo is a GEO/AEO platform (Generative / Answer Engine Optimization): it tracks how AI assistants cite a website, benchmarks against competitors, and drives content and technical fixes.
- Pages are MDX files with YAML frontmatter. Configuration lives in `docs.json`.
- Run `mint dev` to preview locally. Run `mint broken-links` to check links.
- The source of truth for product behavior is the `app` and `backend` code in this monorepo, not these docs. When they disagree, fix the docs.

## Design direction

- The site follows the marketing site (vitrine V13): cream paper `#F9F8F5`, ink `#16151A`, "press start" yellow `#F4C533`, night navy `#111A45` for dark mode. Light by default.
- Colors, background, theme (`maple`) and fonts (Host Grotesk) live in `docs.json`. `style.css` adds the pixel details: Tiny5 eyebrows, Jersey 10 method pills, square corners, 2 px frames with hard offset shadows, yellow active states. Tokens mirror `vitrine/app/globals.css`; keep them in sync.
- Reading stays sober. The retro lives in small labels, frames and shadows, never in body text.
- Logos and favicons are the Hikoo wordmark from `vitrine/assets/logos/hikoo.tsx`, in ink (`logo/light.svg`) and paper (`logo/dark.svg`).
- Icons use the **Lucide** library (`icons.library` in `docs.json`). Use Lucide icon names only, no FontAwesome or brand icons.

## API reference

- `api-reference/openapi.json` is generated, never edited by hand. It must match the backend running in production (`origin/main`).
- Regenerate: export the raw spec with `backend/scripts/export_public_openapi.py` from an `origin/main` checkout, then run `python3 scripts/build_openapi.py <raw.json>`. The script adds readable titles, tag descriptions, shared error responses and the endpoint navigation in `docs.json`.
- A new endpoint needs a title in `SUMMARIES`, and a new tag needs a place in `NAV_GROUPS`. The script fails or warns otherwise.

## Terminology

- Prompt = a tracked question sent to AI assistants. Topic = a group of prompts (the sidebar labels them **Subjects**). Mention = the brand is named in an answer; Citation = a link to the site is shown; Background source = a page the assistant read without showing it. Search query = the search an assistant runs internally (the UI says **Query fanouts**).
- Modules mirror the app sidebar: Overview, Spotlight, Battlemap (includes Outreach, a regular module, never call it beta), Elevate, Analyzer.
- The MCP server does not handle Outreach. The REST API does.
- Support email: support@tryhikoo.com.
- Platforms: ChatGPT, Perplexity, Claude, Gemini, Google AI Overviews, Google AI Mode, Bing AI Mode, Grok, Mistral. Copilot and DeepSeek are retired (Bing AI Mode replaced Copilot).
- One MCP/API key is scoped to a **user account**, not a single website (the per-website model is retired).

## Style preferences

- Active voice, second person ("you"), one idea per sentence, sentence case headings.
- **Never use an em-dash (—) or en-dash (–).** Split into two sentences or use a comma.
- Bold for UI elements: Click **Settings**. Code formatting for file names, paths, commands, and literal values.
- Do not invent prices, quota numbers, or SLAs. Say "your plan determines".
- Write the docs in English only, even though the product ships English and French.

## Content boundaries

- Do not document internal admin tools, impersonation internals, or scraping vendors.
- Do not expose secrets, internal URLs, internal headers, or how the MCP server talks to the backend. This repository is public: everything committed here is public too, not only the published pages.

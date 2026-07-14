# Hikoo documentation project instructions

## About this project

- This is the **Hikoo** product documentation, built on [Mintlify](https://mintlify.com).
- Hikoo is a GEO/AEO platform (Generative / Answer Engine Optimization): it tracks how AI assistants cite a website, benchmarks against competitors, and drives content and technical fixes.
- Pages are MDX files with YAML frontmatter. Configuration lives in `docs.json`.
- Run `mint dev` to preview locally. Run `mint broken-links` to check links.
- The source of truth for product behavior is the `app` and `backend` code in this monorepo, not these docs. When they disagree, fix the docs.

## Design direction

- The site follows Hikoo's monochrome design: black in light mode, white in dark mode, dark by default. Colors are set in `docs.json` (`colors` + `appearance`).
- Logos and favicons are the monochrome Hikoo wordmark (`logo/light.svg`, `logo/dark.svg`, `favicon-light.svg`, `favicon-dark.svg`).
- `style.css` sharpens corners to match the flat DA. It may only take effect on a paid Mintlify plan; the `docs.json` colors carry the look on the free plan.
- Icons use the **Lucide** library (`icons.library` in `docs.json`). Use Lucide icon names only, no FontAwesome or brand icons.

## Terminology

- Prompt = a tracked question sent to AI assistants. Topic = a group of prompts. Citation = one AI mention of a brand. Search query = the search an assistant runs internally.
- Modules mirror the app sidebar: Overview, Spotlight, Battlemap, Elevate, Analyzer.
- Platforms: ChatGPT, Perplexity, Claude, Gemini, Google AI Overviews, Google AI Mode, Copilot, Grok, Mistral, DeepSeek.
- One MCP/API key is scoped to a **user account**, not a single website (the per-website model is retired).

## Style preferences

- Active voice, second person ("you"), one idea per sentence, sentence case headings.
- **Never use an em-dash (—) or en-dash (–).** Split into two sentences or use a comma.
- Bold for UI elements: Click **Settings**. Code formatting for file names, paths, commands, and literal values.
- Do not invent prices, quota numbers, or SLAs. Say "your plan determines".
- Write the docs in English only, even though the product ships English and French.

## Content boundaries

- Do not document internal admin tools, impersonation internals, or scraping vendors.
- Do not expose secrets, internal URLs, or the `X-MCP-Secret` relay detail.

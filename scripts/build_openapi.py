"""Build the Mintlify API reference from the backend's public OpenAPI spec.

Two steps:

1. Export the raw spec from the backend at the commit running in production
   (``origin/main``), with the backend's own script:

       cd ../backend && git worktree add /tmp/hikoo-prod origin/main
       cd /tmp/hikoo-prod && python scripts/export_public_openapi.py /tmp/openapi-raw.json

2. Enrich it for the docs and write ``api-reference/openapi.json`` plus the
   endpoint navigation in ``docs.json``:

       python3 scripts/build_openapi.py /tmp/openapi-raw.json

The enrichment never changes what an endpoint accepts or returns. It adds
readable titles, tag descriptions, the shared error responses, and English
copy where the backend still has French strings.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_SPEC = ROOT / "api-reference" / "openapi.json"
DOCS_JSON = ROOT / "docs.json"
PREFIX = "/api/v1/public"

INFO_DESCRIPTION = (
    "Programmatic access to your Hikoo data: AI citations, prompts, topics, "
    "competitors, sources, audits, site health, indexation, AI-crawler traffic, "
    "and outreach. Authenticate with a personal API key sent as "
    "`Authorization: Bearer <key>`. Create one in the dashboard under "
    "**Settings > API keys**."
)

# Tags and endpoints kept out of the public docs on purpose (they still exist).
EXCLUDE_TAGS = {"Agency reports"}
EXCLUDE_OPS: set[str] = set()

# Navigation: (group name, [tags]) in the order they appear in the sidebar.
NAV_GROUPS: list[tuple[str, list[str]]] = [
    ("Account", ["Account", "Workspaces", "Websites", "Website"]),
    ("AI visibility", ["Citations", "Prompts", "Topics", "Search queries", "URL lookup"]),
    ("Competition and sources", ["Competitors", "Source intelligence"]),
    ("Site", ["Audits", "Health", "Indexation", "Content gaps", "Agent analytics"]),
    ("Outreach", ["Outreach"]),
]

TAG_DESCRIPTIONS: dict[str, str] = {
    "Account": "The user behind the API key.",
    "Workspaces": "Workspaces the user belongs to. Use them to find the websites you can query.",
    "Websites": "Every website the user can access, with its subscription status.",
    "Website": "Metadata and plan of one website.",
    "Citations": (
        "Every time an AI assistant answers one of your prompts, Hikoo stores the answer as a "
        "citation. These endpoints list them and aggregate them by platform, source, sentiment "
        "and match type."
    ),
    "Prompts": (
        "Prompts are the questions Hikoo sends to AI assistants for a website. Create, edit, "
        "archive and restore them, and read their visibility, answers and citations."
    ),
    "Topics": "Topics group prompts. Every prompt belongs to one topic.",
    "Search queries": (
        "The web searches AI assistants run internally (query fan-out) before answering your prompts."
    ),
    "URL lookup": "Where one URL shows up, across AI-cited sources and AI-crawler traffic, in one call.",
    "Competitors": (
        "Tracked competitors, their share of voice, and the competitor suggestions Hikoo detects in AI answers."
    ),
    "Source intelligence": "The domains and pages AI assistants cite for your prompts, and who appears on them.",
    "Audits": "GEO audits of a full site, a list of pages or a single URL.",
    "Health": "Site-level checks for AI readiness (robots.txt, llms.txt, sitemap) and improvement suggestions.",
    "Indexation": "The pages Hikoo crawled on your website, their category, health and errors.",
    "Content gaps": "Topics where AI assistants answer without citing you, with a content brief for each.",
    "Agent analytics": "Traffic from AI crawlers and AI agents on your website.",
    "Outreach": (
        "The outreach agent: sources worth getting cited on, their contacts, the pitches waiting for "
        "approval, follow-ups, and what the agent is allowed to do on its own."
    ),
    "Agency reports": (
        "Reports for agency workspaces: grade a list of prospect sites, add them, launch the reports, "
        "and share or revoke their links. Requires an agency workspace."
    ),
}

# Readable endpoint titles (Mintlify shows the summary as the page title).
SUMMARIES: dict[str, str] = {
    "GET /me": "Get current user",
    "GET /workspaces": "List workspaces",
    "GET /workspaces/with-websites": "List workspaces with their websites",
    "GET /websites": "List websites",
    "GET /website": "Get a website",
    "GET /website/subscription": "Get subscription details",
    "GET /agency/reports": "List agency reports",
    "POST /agency/reports": "Add agency reports",
    "POST /agency/reports/preview": "Preview agency reports",
    "POST /agency/reports/launch": "Launch agency reports",
    "POST /agency/reports/relaunch": "Relaunch agency reports",
    "POST /agency/reports/revoke": "Revoke agency report links",
    "GET /agent-analytics": "Get AI-crawler traffic",
    "GET /agent-analytics/pages": "List pages visited by AI crawlers",
    "GET /audits/quota": "Get audit quota",
    "GET /audits": "List audits",
    "POST /audits": "Start a full-site audit",
    "POST /audits/url": "Audit a single URL",
    "POST /audits/pages": "Audit selected pages",
    "POST /audits/{audit_id}/sync": "Re-run an audit",
    "GET /audits/{audit_id}": "Get an audit",
    "GET /audits/{audit_id}/pages/{page_id}": "Get an audited page",
    "GET /citations": "List citations",
    "GET /citations/top-platforms": "Get top platforms",
    "GET /citations/platforms": "Get visibility by platform",
    "GET /citations/top-sources": "Get top sources",
    "GET /citations/sentiment-summary": "Get sentiment summary",
    "GET /citations/sentiment-trend": "Get sentiment trend",
    "GET /citations/breakdown": "Get citation breakdown",
    "GET /citations/all-sources": "List all cited source URLs",
    "GET /citations/{citation_id}": "Get a citation",
    "GET /competitors": "Get competitor ranking",
    "POST /competitors": "Add a competitor",
    "GET /competitors/suggestions": "List competitor suggestions",
    "GET /competitors/suggestions/{suggestion_id}/citations": "List citations behind a suggestion",
    "POST /competitors/suggestions/{suggestion_id}/dismiss": "Dismiss a competitor suggestion",
    "POST /competitors/suggestions/{suggestion_id}/promote": "Promote a competitor suggestion",
    "PUT /competitors/{competitor_id}": "Update a competitor",
    "DELETE /competitors/{competitor_id}": "Remove a competitor",
    "GET /competitors/citations": "Get citations per competitor",
    "GET /competitors/chart-stats": "Get share of voice chart",
    "GET /competitors/website-shares": "Get share of voice over time",
    "GET /competitors/limit": "Get competitor quota",
    "GET /content-gaps/quota": "Get content gap quota",
    "GET /content-gaps/summary": "Get content gap summary",
    "GET /content-gaps": "List content gaps",
    "GET /content-gaps/{suggestion_id}": "Get a content gap",
    "GET /health": "Get site health",
    "POST /health/refresh": "Refresh site health",
    "GET /health/refresh-quota": "Get health refresh quota",
    "POST /health/suggestions/{suggestion_id}/dismiss": "Dismiss a health suggestion",
    "POST /health/suggestions/{suggestion_id}/restore": "Restore a health suggestion",
    "POST /health/suggestions/regenerate": "Regenerate health suggestions",
    "GET /health/suggestions/regenerate-quota": "Get suggestion regeneration quota",
    "GET /health/suggestions/{suggestion_id}/pages": "List pages affected by a suggestion",
    "GET /indexation/summary": "Get indexation summary",
    "GET /indexation/status": "Get indexation status",
    "GET /indexation/pages": "List indexed pages",
    "GET /indexation/pages/{page_id}": "Get an indexed page",
    "GET /indexation/errors": "List page errors",
    "POST /indexation/single-page": "Re-crawl a URL",
    "GET /outreach/home": "Get outreach home",
    "GET /outreach/overview": "Get outreach overview",
    "GET /outreach/work": "List active opportunities",
    "GET /outreach/activity": "List outreach activity",
    "GET /outreach/sources": "List outreach sources",
    "GET /outreach/sources/{source_id}": "Get an outreach source",
    "POST /outreach/sources/{source_id}/draft": "Request a pitch draft",
    "PATCH /outreach/sources/{source_id}/status": "Set a source status",
    "PATCH /outreach/sources/{source_id}/contact": "Update a source contact",
    "PUT /outreach/sources/{source_id}/follow-up": "Reschedule a follow-up",
    "POST /outreach/sources/{source_id}/follow-up/skip": "Skip a follow-up",
    "POST /outreach/sources/{source_id}/hot-reply": "Answer a held reply",
    "POST /outreach/sources/{source_id}/negotiation": "Authorize price negotiation",
    "DELETE /outreach/sources/{source_id}/negotiation": "Revoke price negotiation",
    "POST /outreach/sources/{source_id}/note": "Add a note to a source",
    "PATCH /outreach/messages/{message_id}": "Edit a pitch",
    "POST /outreach/messages/{message_id}/approve": "Approve a pitch",
    "POST /outreach/messages/{message_id}/rewrite": "Rewrite a pitch",
    "GET /outreach/messages/{message_id}/versions": "List pitch versions",
    "POST /outreach/messages/{message_id}/version": "Restore a pitch version",
    "GET /outreach/settings": "Get outreach settings",
    "PUT /outreach/settings/preset": "Apply a permission preset",
    "PUT /outreach/settings/permission": "Set one permission",
    "PUT /outreach/settings/money": "Set payment limits",
    "PUT /outreach/settings/follow-ups": "Set follow-up cadence",
    "PUT /outreach/settings/offer": "Set what the brand offers",
    "PUT /outreach/settings/sender": "Set the sender profile",
    "GET /outreach/mailboxes": "List sending mailboxes",
    "GET /outreach/blacklist": "List blocked domains and addresses",
    "POST /outreach/blacklist": "Block a domain or address",
    "DELETE /outreach/blacklist/{entry_id}": "Unblock a domain or address",
    "GET /prompts/quota": "Get prompt quota",
    "GET /prompts": "List prompts",
    "POST /prompts": "Create a prompt",
    "PUT /prompts/{prompt_id}": "Update a prompt",
    "DELETE /prompts/{prompt_id}": "Delete a prompt",
    "POST /prompts/batch-update": "Update prompts in bulk",
    "POST /prompts/batch-archive": "Archive prompts in bulk",
    "POST /prompts/{prompt_id}/archive": "Archive a prompt",
    "POST /prompts/{prompt_id}/restore": "Restore a prompt",
    "GET /prompts/{prompt_id}/citations": "List citations of a prompt",
    "GET /prompts/{prompt_id}/detail": "Get prompt detail",
    "GET /prompts/{prompt_id}/answers": "List answers of a prompt",
    "GET /prompts/{prompt_id}/stats": "Get prompt stats",
    "GET /search-queries": "List search queries",
    "GET /search-queries/grouped": "List search query groups",
    "GET /search-queries/grouped/queries": "List queries in a group",
    "GET /search-queries/by-prompt/{prompt_id}": "List search queries of a prompt",
    "GET /search-queries/by-citation/{citation_id}": "List search queries of a citation",
    "GET /source-intelligence/sources": "List suggested sources",
    "GET /source-intelligence/stats": "Get source intelligence stats",
    "GET /source-intelligence/pages": "List source pages",
    "GET /topics": "List topics",
    "POST /topics": "Create a topic",
    "PUT /topics/{topic_id}": "Rename a topic",
    "DELETE /topics/{topic_id}": "Delete a topic",
    "GET /url-lookup": "Look up a URL",
}

# Descriptions the backend leaves empty.
DESCRIPTIONS: dict[str, str] = {
    "POST /outreach/sources/{source_id}/note": "Add a free-text note to a source's timeline.",
    "GET /outreach/blacklist": "Domains and email addresses the outreach agent never contacts.",
    "DELETE /outreach/blacklist/{entry_id}": "Remove a domain or address from the blocklist.",
}

# Backend strings still in French.
TRANSLATIONS: dict[str, str] = {
    "Filtrer par intention": "Filter by prompt intent.",
    "Filtrer par marches (localisations du prompt)": "Filter by market (prompt localizations).",
    "Filtrer par tags de prompt (multi-select, OR)": "Filter by prompt tags. Several values match any of them.",
    "Filtrer par type de marque (branded/non_branded)": "Filter by brand scope (`branded` or `non_branded`).",
}

# Public descriptions for endpoints whose backend docstring talks about
# internals (workers, SQL, managers, quota field names, other tools).
OP_DESCRIPTIONS: dict[str, str] = {
    "GET /workspaces": "List every workspace you are a member of.",
    "GET /workspaces/with-websites": "Workspaces you belong to, each with its websites and their subscription status, in one call.",
    "GET /websites": (
        "List the websites you can access, paginated. Each item includes `has_active_subscription`. "
        "Websites without an active subscription are listed, but their data endpoints answer `403`."
    ),
    "GET /website/subscription": (
        "Plan details for the website: plan tier, product name, status, trial and expiry dates, AI platforms "
        "covered, available features and quotas. Restricted to workspace owners and admins; other members get `403`."
    ),
    "GET /audits/quota": "Audit quota usage (used, limit, remaining) for the current billing period. Check it before you start an audit.",
    "POST /audits/pages": (
        "Audit a specific list of URLs on the website. Every URL must belong to the website's domain. "
        "Your plan caps how many pages you can audit each month."
    ),
    "POST /audits/{audit_id}/sync": (
        "Queue a new audit that reuses the pages and criteria of a completed audit. "
        "Use it to re-check the same pages after you change them."
    ),
    "GET /citations/sentiment-summary": (
        "Aggregated sentiment per brand (your website, your competitors and other brands) over the period. "
        "Requires a plan that includes sentiment analysis, otherwise `403`."
    ),
    "GET /citations/sentiment-trend": (
        "Sentiment counts over time, by day or by week. Requires a plan that includes sentiment analysis, otherwise `403`."
    ),
    "GET /citations/breakdown": (
        "Counts per match type (`brand_mention`, `cited_link`, `background_link`) over the period, with the change "
        "against the previous period and a daily sparkline."
    ),
    "GET /citations/{citation_id}": (
        "One citation: the full answer, its sources, brand mentions, prompt and competitor ranks. "
        "Brand mentions are left out when your plan does not include sentiment analysis."
    ),
    "POST /competitors": "Add a competitor to the website. Answers `403` once your plan's competitor quota is reached.",
    "GET /competitors/suggestions": (
        "Competitor candidates Hikoo detected in AI answers, most cited first. Each item carries `visibility`, the share "
        "of all your website's answers that name it. Requires a plan with competitor suggestions, otherwise `403`."
    ),
    "GET /competitors/suggestions/{suggestion_id}/citations": (
        "The AI answers behind one suggestion, most recent first, with the prompt behind each answer and the rank "
        "the brand held in it."
    ),
    "POST /competitors/suggestions/{suggestion_id}/promote": (
        "Track a suggested competitor, either as a new competitor or as an alternative name of one you already track. "
        "Answers `403` once your plan's competitor quota is reached."
    ),
    "POST /health/refresh": "Re-check robots.txt, llms.txt and the sitemap now. Your plan limits refreshes per month.",
    "POST /health/suggestions/regenerate": "Regenerate health suggestions from the pages currently indexed. Your plan limits regenerations per month.",
    "GET /indexation/status": "Status of the latest indexation run (running, completed or failed) with its progress counters.",
    "POST /indexation/single-page": "Re-crawl one URL of the website. The URL must belong to the website's domain.",
    "POST /outreach/sources/{source_id}/draft": (
        "Ask Hikoo to write a pitch for this source. The call answers right away. The draft lands in the approval "
        "queue a few seconds later, never in a mailbox: read the source again to get it."
    ),
    "POST /outreach/messages/{message_id}/approve": (
        "Approve a pitch. It leaves from your own mailbox, inside your sending hours and limits. "
        "Only the person who owns the source can approve it."
    ),
    "PUT /outreach/settings/permission": "Move one square of the permission grid.",
    "POST /outreach/blacklist": "Add a domain or address to the do-not-contact list. Any draft waiting for it is cancelled.",
    "GET /prompts/quota": (
        "Active prompt count, plan limit and remaining slots. Archived prompts do not count. "
        "Check it before you create prompts in bulk."
    ),
    "POST /prompts/batch-update": (
        "Apply the same change (topic, markets, intent, journey stage) to many prompts at once. Only the fields you send "
        "change; send `null` to clear a field. Returns `{updated: <count>}`."
    ),
    "GET /prompts/{prompt_id}/answers": (
        "Every answer of a prompt, newest first. Pass `next_cursor` back as `cursor` until it is `null`. "
        "Answers that arrive meanwhile never shift or repeat a page."
    ),
    "GET /source-intelligence/pages": (
        "Cited pages, ordered by opportunity: what each page is, whether your brand is on it, and whether Hikoo has "
        "checked it. Read `brand_present` together with `page_examined`: both false means the page was not checked "
        "yet, not that you are absent. The list covers your plan's window, and `total_in_store` gives the full count. "
        "Each page also carries `momentum`."
    ),
}

# Fields kept out of the published schemas.
HIDDEN_PROPERTIES = {
    ("WebsiteResponse", "outreach_agent_beta"),
}

# Enum values kept out of the published schemas.
HIDDEN_ENUM_VALUES: set[tuple[str, str]] = set()

# Words that must never reach the public reference. The build fails on them.
# Generic developer vocabulary lives here. Names of vendors, customers and
# competitors live in scripts/denylist.local.txt, one regex per line, which is
# git-ignored because this repository is public.
_DENY_GENERIC = [
    r"founder", r"scrap", r"worker", r"\bsql\b", r"manager", r"\blot [a-z]\b", r"bench", r"report\.md",
    r"migration", r"frontend", r"\bFE\b", r"\bbeta\b", r"celery", r"redis", r"model call",
    r"app\.service", r":class:", r":data:", r"x-mcp", r"security review", r"HK-\d+", r"—", r"–",
]
_LOCAL_DENYLIST = Path(__file__).with_name("denylist.local.txt")
_DENY_LOCAL = (
    [line.strip() for line in _LOCAL_DENYLIST.read_text().splitlines() if line.strip() and not line.startswith("#")]
    if _LOCAL_DENYLIST.exists()
    else []
)
if not _DENY_LOCAL:
    print(f"Warning: {_LOCAL_DENYLIST.name} is missing, private names are not checked.", file=sys.stderr)
DENYLIST = re.compile("|".join(_DENY_GENERIC + _DENY_LOCAL), re.I)

# Backend strings rewritten in place (property and parameter descriptions).
REWRITES: dict[str, str] = {
    "What the user sees: active, needs_you, hikoo_working, waiting, in_progress, closed. Translated to statuses on the backend.":
        "Tab to list: `active`, `needs_you`, `hikoo_working`, `waiting`, `in_progress` or `closed`.",
}


ERROR_SCHEMA = {
    "type": "object",
    "title": "Error",
    "required": ["detail"],
    "properties": {
        "detail": {
            "type": "string",
            "description": "Human-readable explanation of the error.",
        }
    },
}

ERROR_CODE_HEADER = {
    "description": "Stable machine-readable error code, when one applies (for example `rate_limited`).",
    "schema": {"type": "string"},
}


def _error(description: str, example: str, headers: dict | None = None) -> dict:
    response = {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/Error"},
                "example": {"detail": example},
            }
        },
    }
    if headers:
        response["headers"] = headers
    return response


RESPONSES = {
    "Unauthorized": _error(
        "The `Authorization` header is missing, malformed, or the key is invalid, expired or revoked.",
        "Invalid or expired API key",
    ),
    "Forbidden": _error(
        "The key is valid but not allowed to do this: the website has no active subscription, "
        "your role in the workspace is read-only for a write request, or your email is not verified.",
        "This website has no active subscription, so its data is unavailable.",
        {"X-Error-Code": ERROR_CODE_HEADER},
    ),
    "NotFound": _error(
        "The website, or the resource in the path, does not exist or is not visible to this key.",
        "Website not found",
    ),
    "RateLimited": _error(
        "Too many requests for this API key. Wait for the number of seconds in `Retry-After`.",
        "Too many requests. Please try again shortly.",
        {
            "Retry-After": {
                "description": "Seconds to wait before retrying.",
                "schema": {"type": "integer"},
            },
            "X-Error-Code": ERROR_CODE_HEADER,
        },
    ),
}


def _translate(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("description", "title") and isinstance(value, str) and value in TRANSLATIONS:
                node[key] = TRANSLATIONS[value]
            else:
                _translate(value)
    elif isinstance(node, list):
        for item in node:
            _translate(item)


def enrich(spec: dict) -> dict:
    for path in list(spec["paths"]):
        item = spec["paths"][path]
        for method in list(item):
            key = f"{method.upper()} {path.removeprefix(PREFIX)}"
            if set(item[method].get("tags", [])) & EXCLUDE_TAGS or key in EXCLUDE_OPS:
                del item[method]
        if not item:
            del spec["paths"][path]
    spec["info"]["description"] = INFO_DESCRIPTION
    spec["servers"] = [{"url": "https://api.tryhikoo.com", "description": "Production"}]
    components = spec.setdefault("components", {})
    components["securitySchemes"] = {
        "apiKey": {
            "type": "http",
            "scheme": "bearer",
            "description": "Personal API key created in the dashboard under Settings > API keys.",
        }
    }
    spec["security"] = [{"apiKey": []}]
    components.setdefault("schemas", {})["Error"] = ERROR_SCHEMA
    components["responses"] = RESPONSES

    used_tags: set[str] = set()
    missing: list[str] = []
    for path, item in spec["paths"].items():
        short = path.removeprefix(PREFIX)
        for method, op in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            key = f"{method.upper()} {short}"
            if key in SUMMARIES:
                op["summary"] = SUMMARIES[key]
            else:
                missing.append(key)
            if key in OP_DESCRIPTIONS:
                op["description"] = OP_DESCRIPTIONS[key]
            elif not op.get("description") and key in DESCRIPTIONS:
                op["description"] = DESCRIPTIONS[key]
            used_tags.update(op.get("tags", []))

            # Auth headers are documented by the security scheme. The MCP relay
            # header is internal and must not appear in the public docs.
            op["parameters"] = [
                p
                for p in op.get("parameters", [])
                if not (p["in"] == "header" and p["name"].lower() in ("authorization", "x-mcp-secret"))
            ]
            if not op["parameters"]:
                del op["parameters"]
            params = {p["name"] for p in op.get("parameters", [])}
            responses = op["responses"]
            responses.setdefault("401", {"$ref": "#/components/responses/Unauthorized"})
            if "website_id" in params or "workspace_id" in params or method != "get":
                responses.setdefault("403", {"$ref": "#/components/responses/Forbidden"})
            if "website_id" in params or "workspace_id" in params or "{" in short:
                responses.setdefault("404", {"$ref": "#/components/responses/NotFound"})
            responses.setdefault("429", {"$ref": "#/components/responses/RateLimited"})

    if missing:
        print("No readable title for:\n  " + "\n  ".join(missing), file=sys.stderr)

    ordered = [t for _, tags in NAV_GROUPS for t in tags]
    unknown = sorted(used_tags - set(ordered))
    if unknown:
        raise SystemExit(f"Tags not placed in NAV_GROUPS: {unknown}")
    spec["tags"] = [
        {"name": t, "description": TAG_DESCRIPTIONS.get(t, "")} for t in ordered if t in used_tags
    ]
    _translate(spec)
    _prune_schemas(spec)
    _scrub(spec)
    return spec


def _scrub(spec: dict) -> None:
    """Remove developer notes and internal details from the published text."""
    for name, schema in spec["components"]["schemas"].items():
        if name != "Error":
            schema.pop("description", None)  # docstrings written for developers
        for owner, prop in HIDDEN_PROPERTIES:
            if name == owner:
                schema.get("properties", {}).pop(prop, None)
                if prop in schema.get("required", []):
                    schema["required"].remove(prop)
        for owner, value in HIDDEN_ENUM_VALUES:
            if name == owner and value in schema.get("enum", []):
                schema["enum"].remove(value)

    def clean(text: str) -> str:
        text = REWRITES.get(text, text)
        text = text.replace("``", "`")
        return re.sub(r"\s*[—–]\s*", ", ", text)

    leaks: list[str] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("description", "summary") and isinstance(value, str):
                    node[key] = clean(value)
                    if DENYLIST.search(node[key]):
                        leaks.append(f"{path}: {node[key][:120]}")
                else:
                    walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(spec, "")
    if leaks:
        raise SystemExit("Internal details in the public spec:\n  " + "\n  ".join(leaks))


def _prune_schemas(spec: dict) -> None:
    """Drop schemas no longer referenced (left over by EXCLUDE_TAGS)."""
    schemas = spec["components"]["schemas"]
    while True:
        text = json.dumps({k: v for k, v in spec.items() if k != "components"}) + json.dumps(
            {k: v for k, v in spec["components"].items() if k != "schemas"}
        ) + json.dumps(schemas)
        unused = [n for n in schemas if f'"#/components/schemas/{n}"' not in text]
        if not unused:
            return
        for n in unused:
            del schemas[n]


# Large tags split into sub-groups by path (longest prefix wins), shown in this order.
SPLIT_TAGS: dict[str, list[tuple[str, str]]] = {
    "Outreach": [
        ("Home and activity", "/outreach"),
        ("Sources", "/outreach/sources"),
        ("Pitches", "/outreach/messages"),
        ("Settings", "/outreach/settings"),
        ("Mailboxes and blocklist", "/outreach/mailboxes"),
        ("Mailboxes and blocklist", "/outreach/blacklist"),
    ],
}


def navigation(spec: dict) -> list[dict]:
    """Endpoint groups for docs.json, one sub-group per tag, in spec order."""
    by_tag: dict[str, list] = {}
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method in ("get", "post", "put", "patch", "delete"):
                by_tag.setdefault(op["tags"][0], []).append(f"{method.upper()} {path}")
    for tag, rules in SPLIT_TAGS.items():
        if tag not in by_tag:
            continue
        order = list(dict.fromkeys(name for name, _ in rules))
        buckets: dict[str, list[str]] = {name: [] for name in order}
        for page in by_tag[tag]:
            short = page.split(" ", 1)[1].removeprefix(PREFIX)
            name = max(
                ((n, prefix) for n, prefix in rules if short.startswith(prefix)),
                key=lambda rule: len(rule[1]),
            )[0]
            buckets[name].append(page)
        NAV_GROUPS[:] = [
            (g, ts) if ts != [tag] else (g, [f"{tag}:{n}" for n in order]) for g, ts in NAV_GROUPS
        ]
        for name in order:
            by_tag[f"{tag}:{name}"] = buckets[name]
    groups = []
    for name, tags in NAV_GROUPS:
        present = [t for t in tags if t in by_tag]
        if not present:
            continue
        flat = [page for t in present for page in by_tag[t]]
        if len(present) == 1 or len(flat) <= 8:
            groups.append({"group": name, "pages": flat})
        else:
            groups.append(
                {
                    "group": name,
                    "pages": [{"group": t.split(":")[-1], "pages": by_tag[t]} for t in present],
                }
            )
    return groups


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    spec = enrich(json.loads(Path(sys.argv[1]).read_text()))
    OUT_SPEC.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")

    docs = json.loads(DOCS_JSON.read_text())
    for tab in docs["navigation"]["tabs"]:
        if tab.get("tab") == "API reference":
            intro = [g for g in tab["groups"] if g.get("group") == "Getting started"]
            tab["openapi"] = "/api-reference/openapi.json"
            tab["groups"] = intro + navigation(spec)
    DOCS_JSON.write_text(json.dumps(docs, indent=2, ensure_ascii=False) + "\n")
    count = sum(len(v) for v in spec["paths"].values())
    print(f"Wrote {OUT_SPEC.relative_to(ROOT)} ({count} operations) and updated docs.json navigation")


if __name__ == "__main__":
    main()

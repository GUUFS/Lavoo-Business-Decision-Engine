"""
Tool discovery: grow the ai_tools catalog from tools that analyses suggest
but the catalog doesn't have.

How it works, for every finished analysis (api/routes/decision_engine/analyzer.py
starts it in the background; an hourly job in api/main.py retries leftovers):
  1. Collect every tool name the analysis suggested (any "tool_name" in the
     result, plus the names in each tool stack).
  2. Drop the ones the catalog already has (same lookup the analyzer uses,
     recommender_db.find_tool_by_name, so near-duplicates like "Notion" vs
     "Notion AI" are not added twice). Log the rest in tool_discoveries.
  3. Find the tool's official website in an outside directory:
       - Wikidata (free, no key): the entity's "official website" (P856);
       - otherwise the LLM names the website it believes is official, and
         we only accept it if the page loads and mentions the tool's name.
  4. Read that website (home page plus /pricing when there is one) and ask
     the LLM to fill our columns from that text only: description,
     summary, category, pricing, key features, pros, cons, who should use
     it, integrations. Anything the site doesn't say is written as such;
     ratings stay 0 because we have no real rating to copy.
  5. Insert the tool (source = "discovered"), with its search embedding,
     and record the outcome. Within an hour the recommender's catalog
     refresh (recommender_db.get_recommender) picks it up, so the next
     analysis can recommend it like any other tool.
Every name ends in one status with a reason in words: added,
already_in_catalog, rejected (not a business software product),
not_found (no official website could be confirmed) or failed (the exact
error; retried by the hourly job up to MAX_ATTEMPTS times).
"""
import asyncio
import ipaddress
import json
import logging
import re
import socket
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.pg_models import AITool, ToolDiscovery

logger = logging.getLogger(__name__)

# Client name for outside directories. Wikimedia refuses (HTTP 403) any
# client name without a way to reach its owner, so it carries our website.
USER_AGENT = "LavooToolDiscovery/1.0 (https://lavoo.io)"
HTTP_TIMEOUT = 12.0
MAX_PAGE_BYTES = 1_500_000      # stop reading a page after this much
PAGE_TEXT_CHARS = 9_000         # page text sent to the LLM
MAX_ATTEMPTS = 3                # a failed name is retried this many times
MAX_PER_ANALYSIS = 6            # new names looked up per analysis

# Names that are never a tool on their own (generic words the analyzer
# sometimes passes through).
_GENERIC_NAMES = frozenset({
    "email", "crm", "spreadsheet", "spreadsheets", "website", "app", "software", "ai", "chatbot",
    "social media", "google", "microsoft", "meta", "excel sheet", "calendar", "phone", "whatsapp group",
})


# =========================================================================
# 1-2. Which suggested tools are missing from the catalog
# =========================================================================

def normalize_name(name: str) -> str:
    """Lower case, single spaces: the key one tool is logged under."""
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def suggested_tool_names(data: dict) -> list[str]:
    """Every tool name an analysis result suggests, in order, once each."""
    found: dict[str, str] = {}

    def walk(node, parent_key: str = "") -> None:
        # 1. A dict: its "tool_name", then everything inside it.
        if isinstance(node, dict):
            name = node.get("tool_name")
            if isinstance(name, str) and name.strip():
                found.setdefault(normalize_name(name), name.strip())
            for key, value in node.items():
                walk(value, key)
        # 2. A list: a stack's "tools" may be plain names; otherwise go inside.
        elif isinstance(node, list):
            for item in node:
                if parent_key == "tools" and isinstance(item, str) and item.strip():
                    found.setdefault(normalize_name(item), item.strip())
                else:
                    walk(item, parent_key)

    walk(data or {})
    # 3. Skip generic words that aren't products.
    return [name for key, name in found.items() if key not in _GENERIC_NAMES and len(key) >= 2]


def _in_catalog(db: Session, name: str) -> AITool | None:
    """The catalog row for this name (the analyzer's own lookup), or None."""
    from decision_engine.recommender_db import find_tool_by_name

    # 1. Same matching the analyzer uses, so near-duplicates count as present.
    record = find_tool_by_name(name, db)
    if not record:
        return None
    # 2. The row itself.
    return db.query(AITool).filter(AITool.name == record["tool_name"]).first()


def record_suggestions(db: Session, names: list[str], analysis_id: int | None) -> list[ToolDiscovery]:
    """Log every suggested name missing from the catalog. Returns the ones
    to look up now (new, or failed and still under MAX_ATTEMPTS)."""
    to_look_up: list[ToolDiscovery] = []
    for name in names:
        key = normalize_name(name)
        # 1. Already in the catalog: nothing to discover.
        if _in_catalog(db, name):
            continue
        # 2. Seen before: count the suggestion; retry it if it failed last time.
        row = db.query(ToolDiscovery).filter(ToolDiscovery.name_key == key).first()
        if row:
            row.times_suggested = (row.times_suggested or 0) + 1
            row.last_analysis_id = analysis_id or row.last_analysis_id
            if row.status in ("pending", "failed") and (row.attempts or 0) < MAX_ATTEMPTS:
                to_look_up.append(row)
            continue
        # 3. New: log it as pending.
        row = ToolDiscovery(name=name, name_key=key, status="pending", times_suggested=1,
                            first_analysis_id=analysis_id, last_analysis_id=analysis_id, attempts=0)
        db.add(row)
        to_look_up.append(row)
    db.commit()
    return to_look_up[:MAX_PER_ANALYSIS]


# =========================================================================
# 3. Outside directory: find the official website
# =========================================================================

async def _is_public_http_url(url: str) -> bool:
    """True for an http(s) URL whose host resolves only to public addresses
    (so a bad suggestion can't make the server fetch its own network)."""
    try:
        parsed = urlparse(url)
        # 1. http or https with a host name.
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        # 2. Every address the host resolves to must be public (the DNS
        #    lookup runs in a thread so it doesn't block the server).
        infos = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, None)
        return all(ipaddress.ip_address(info[4][0]).is_global for info in infos)
    except Exception:
        return False


async def _only_public_requests(request: httpx.Request) -> None:
    """HTTP client hook: every request, redirects included, must go to a
    public address."""
    if not await _is_public_http_url(str(request.url)):
        raise ValueError(f"{request.url} is not a public web address")


async def lookup_wikidata(name: str, client: httpx.AsyncClient) -> dict | None:
    """Wikidata's entry for the tool: {website, description, directory_url},
    or None when no entry with this name lists an official website."""
    api = "https://www.wikidata.org/w/api.php"
    # 1. Entities whose label matches the name.
    resp = await client.get(api, params={
        "action": "wbsearchentities", "search": name, "language": "en",
        "type": "item", "limit": 5, "format": "json",
    })
    if resp.status_code != 200:
        raise ValueError(f"Wikidata answered HTTP {resp.status_code}: {resp.text[:200]}")
    found = resp.json().get("search", [])
    ids = [hit["id"] for hit in found if normalize_name(hit.get("label", "")) == normalize_name(name)]
    if not ids:
        return None
    # 2. Their official website claim (P856) and English description.
    entities = (await client.get(api, params={
        "action": "wbgetentities", "ids": "|".join(ids), "props": "claims|descriptions",
        "languages": "en", "format": "json",
    })).json().get("entities", {})
    # 3. The first one that has a website.
    for qid in ids:
        entity = entities.get(qid, {})
        for claim in entity.get("claims", {}).get("P856", []):
            website = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(website, str) and website.startswith("http"):
                return {
                    "website": website,
                    "description": entity.get("descriptions", {}).get("en", {}).get("value", ""),
                    "directory": "wikidata",
                    "directory_url": f"https://www.wikidata.org/wiki/{qid}",
                }
    return None


class _TextExtractor(HTMLParser):
    """Visible text and <title> of an HTML page (scripts and styles skipped)."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        # 1. Track blocks whose text isn't shown.
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        if tag == "title":
            self._in_title = True
        # 2. The meta description is often the best one-line summary.
        if tag == "meta":
            attrs_dict = dict(attrs)
            if (attrs_dict.get("name") or attrs_dict.get("property") or "").lower() in ("description", "og:description"):
                self.parts.append(attrs_dict.get("content") or "")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        # 3. Keep shown text and the title.
        if self._in_title:
            self.title += data
        elif not self._skip and data.strip():
            self.parts.append(data.strip())


async def fetch_page(url: str, client: httpx.AsyncClient) -> dict:
    """{url, title, text} of a public web page. Raises with a clear message
    when it can't be read."""
    # 1. Only public http(s) addresses.
    if not await _is_public_http_url(url):
        raise ValueError(f"{url} is not a public web address")
    # 2. Read at most MAX_PAGE_BYTES.
    async with client.stream("GET", url) as resp:
        if resp.status_code >= 400:
            raise ValueError(f"{url} answered HTTP {resp.status_code}")
        if "html" not in resp.headers.get("content-type", "html"):
            raise ValueError(f"{url} is not a web page ({resp.headers.get('content-type')})")
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk
            if len(body) > MAX_PAGE_BYTES:
                break
        final_url = str(resp.url)
    # 3. Redirects must also stay public.
    if final_url != url and not await _is_public_http_url(final_url):
        raise ValueError(f"{url} redirected to {final_url}, which is not a public web address")
    # 4. Plain text.
    parser = _TextExtractor()
    parser.feed(body.decode("utf-8", errors="ignore"))
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    return {"url": final_url, "title": parser.title.strip(), "text": text}


def _mentions(page: dict, name: str) -> bool:
    """True when the page's title, address or text names the tool."""
    # 1. Compare letters and digits only ("Monday.com" ~ "monday com").
    squash = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())  # noqa: E731
    target = squash(name)
    if not target:
        return False
    # 2. Title, host name, or the first part of the text.
    return any(target in squash(part) for part in (page["title"], urlparse(page["url"]).hostname, page["text"][:4000]))


# =========================================================================
# 4. The LLM fills our columns from the website's own text
# =========================================================================

_FILL_PROMPT = """You are adding one software tool to a catalog of business tools.
Use ONLY the website text below. Do not use outside knowledge. If the text
doesn't say something, write "Not stated on the website" (or [] for a list).

Tool name as suggested: {name}
Official website: {website}
Directory note: {directory_note}

Website text (home page):
{home_text}

Website text (pricing page, may be empty):
{pricing_text}

Pick main_category from this list exactly (closest fit): {categories}

Return JSON only:
{{
  "is_business_software": true or false,
  "reject_reason": "why not, if false (e.g. 'a person', 'a general company, not one product', 'a physical product')",
  "official_name": "the product's name as the website writes it",
  "summary": "one line, under 20 words",
  "description": "3 to 5 sentences: what it is, what it does, who it is for",
  "main_category": "one of the list",
  "sub_category": "short-kebab-case, e.g. email-marketing",
  "ai_categories": ["2 to 4 short lowercase tags"],
  "pricing": "Plan: price and what it includes | Plan: ... (or Not stated on the website)",
  "key_features": ["Feature name: what it does, 4 to 8 items"],
  "pros": ["Strength: why it helps, 3 to 5 items"],
  "cons": ["Limitation: what to watch for, 2 to 4 items; only real ones the text supports, else []"],
  "who_should_use": ["Who: why it suits them, 2 to 5 items"],
  "compatibility_integration": ["Integration or platform: how it connects, from the text only"]
}}"""


def _main_categories(db: Session) -> list[str]:
    """The catalog's main categories, most used first (the LLM picks one)."""
    rows = (
        db.query(AITool.main_category, func.count(AITool.id))
        .filter(AITool.main_category.isnot(None))
        .group_by(AITool.main_category)
        .order_by(func.count(AITool.id).desc())
        .limit(40)
        .all()
    )
    return [r[0] for r in rows if r[0]] or ["AI Productivity Tools"]


async def _ask_llm(analyzer, prompt: str, max_tokens: int = 1400) -> dict | list | None:
    """One LLM call returning parsed JSON (None when the reply isn't JSON)."""
    from decision_engine.agentic_analyzer import _safe_json_loads

    # 1. Low temperature: we want facts copied, not invented.
    resp = await analyzer._llm(
        model=analyzer.fast_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=max_tokens,
    )
    raw = (resp.choices[0].message.content or "").strip()
    # 2. Strip a ```json fence if there is one.
    if "```" in raw:
        raw = raw.split("```")[1].removeprefix("json").strip()
    return _safe_json_loads(raw)


async def _llm_website_guess(analyzer, name: str) -> str | None:
    """The website the LLM believes is the tool's official one (checked by
    the caller before it is trusted)."""
    # 1. Ask for one URL or null.
    parsed = await _ask_llm(analyzer, (
        f'What is the official website of the software product "{name}"? '
        'Reply with JSON only: {"url": "https://..."} or {"url": null} if you are not sure '
        "or it is not a software product."), max_tokens=80)
    url = parsed.get("url") if isinstance(parsed, dict) else None
    return url if isinstance(url, str) and url.startswith("http") else None


def _as_json_list(value) -> str:
    """A list column in the catalog's format: a JSON array of strings."""
    items = value if isinstance(value, list) else []
    return json.dumps([str(v).strip() for v in items if str(v).strip()])


def _embedding_for(fields: dict) -> str | None:
    """The tool's search embedding, built like the catalog's own
    (recommender_db: description + features + who should use it)."""
    try:
        from decision_engine.recommender_db import _model_lock, model

        # 1. Same composite text the recommender embeds.
        text = " ".join([fields["description"], fields["key_features"][:250], fields["who_should_use"][:150]])
        # 2. Encode under the shared model lock.
        with _model_lock:
            vector = model.encode([text], convert_to_tensor=False, show_progress_bar=False)[0]
        return "[" + ",".join(f"{float(x):.6f}" for x in vector) + "]"
    except Exception as e:
        logger.warning("[tool-discovery] embedding skipped: %s", e)
        return None


# =========================================================================
# 5. One name, start to finish
# =========================================================================

async def discover_one(db: Session, row: ToolDiscovery, analyzer, client: httpx.AsyncClient) -> None:
    """Look up one logged name and add it to the catalog, or record why not.
    Sets row.status, row.reason and the details; commits."""
    # 0. Count the attempt first, so a failure below can't undo it.
    row.attempts = (row.attempts or 0) + 1
    row.processed_at = datetime.now(UTC)
    db.commit()
    try:
        # 1. Someone may have added it since it was logged.
        existing = _in_catalog(db, row.name)
        if existing:
            row.status, row.tool_id = "already_in_catalog", existing.id
            row.reason = f"The catalog already has it as {existing.name}."
            db.commit()
            return

        # 2. Official website: Wikidata first, then the LLM's guess.
        found = await lookup_wikidata(row.name, client)
        page = None
        if found:
            page = await fetch_page(found["website"], client)
        else:
            guess = await _llm_website_guess(analyzer, row.name)
            if guess:
                try:
                    candidate = await fetch_page(guess, client)
                except Exception as e:
                    candidate, guess_error = None, str(e)
                else:
                    guess_error = None
                if candidate and _mentions(candidate, row.name):
                    page = candidate
                    found = {"website": candidate["url"], "description": "", "directory": "website",
                             "directory_url": None}
                else:
                    row.status = "not_found"
                    row.reason = (f"Wikidata has no entry with a website, and the website the LLM suggested ({guess}) "
                                  + (f"could not be read: {guess_error}" if guess_error else "doesn't mention the tool's name")
                                  + ".")
                    db.commit()
                    return
            else:
                row.status = "not_found"
                row.reason = "Wikidata has no entry with a website, and the LLM couldn't name an official website."
                db.commit()
                return
        row.website = page["url"]
        row.directory = found["directory"]
        row.directory_url = found.get("directory_url")

        # 3. The pricing page, when the site has one.
        pricing_text = ""
        try:
            pricing_text = (await fetch_page(urljoin(page["url"], "/pricing"), client))["text"][:4000]
        except Exception:
            pricing_text = ""

        # 4. The LLM fills our columns from the website's text.
        fields = await _ask_llm(analyzer, _FILL_PROMPT.format(
            name=row.name, website=page["url"],
            directory_note=found.get("description") or "none",
            home_text=page["text"][:PAGE_TEXT_CHARS], pricing_text=pricing_text or "(none)",
            categories=", ".join(_main_categories(db)),
        ))
        if not isinstance(fields, dict):
            raise ValueError("The LLM's reply wasn't valid JSON")
        if not fields.get("is_business_software", False):
            row.status = "rejected"
            row.reason = f"Not added: {fields.get('reject_reason') or 'the LLM judged it is not a business software product'}."
            db.commit()
            return

        # 5. The official name must not already be in the catalog either.
        name = (fields.get("official_name") or row.name).strip()[:255]
        existing = _in_catalog(db, name)
        if existing:
            row.status, row.tool_id = "already_in_catalog", existing.id
            row.reason = f"Its official name is {name}, which the catalog already has as {existing.name}."
            db.commit()
            return

        # 6. Insert it in the catalog's own formats.
        columns = {
            "description": (fields.get("description") or found.get("description") or "").strip(),
            "key_features": _as_json_list(fields.get("key_features")),
            "who_should_use": _as_json_list(fields.get("who_should_use")),
        }
        if not columns["description"]:
            raise ValueError("The website gave nothing to describe the tool with")
        tool = AITool(
            name=name,
            url=page["url"],
            description=columns["description"],
            summary=(fields.get("summary") or "").strip(),
            main_category=(fields.get("main_category") or "").strip()[:255] or None,
            sub_category=(fields.get("sub_category") or "").strip()[:255] or None,
            ai_categories=_as_json_list(fields.get("ai_categories")),
            pricing=(fields.get("pricing") or "Not stated on the website").strip(),
            ratings=0.0,
            key_features=columns["key_features"],
            pros=_as_json_list(fields.get("pros")),
            cons=_as_json_list(fields.get("cons")),
            who_should_use=columns["who_should_use"],
            compatibility_integration=_as_json_list(fields.get("compatibility_integration")),
            source="discovered",
        )
        tool.embedding = _embedding_for(columns)
        db.add(tool)
        db.flush()

        # 7. Done: link the log row to the new tool.
        row.status, row.tool_id = "added", tool.id
        source = "Wikidata" if found["directory"] == "wikidata" else "the LLM's suggestion, confirmed on the site"
        row.reason = f"Added as {name}. Website from {source}; columns filled from {page['url']}."
        db.commit()
        logger.info("[tool-discovery] added %s (%s)", name, page["url"])
    except IntegrityError:
        # Another worker added the same name a moment ago.
        db.rollback()
        row.status, row.reason = "already_in_catalog", "Added by another run at the same moment."
        db.commit()
    except Exception as e:
        # Keep the exact error; the hourly job retries up to MAX_ATTEMPTS.
        db.rollback()
        row.status = "failed"
        row.reason = f"Attempt {row.attempts} of {MAX_ATTEMPTS} failed: {type(e).__name__}: {e}"[:2000]
        db.commit()
        logger.warning("[tool-discovery] %s failed: %s", row.name, e)


async def process(db: Session, rows: list[ToolDiscovery]) -> dict:
    """Look up each row; returns how many ended in each status."""
    from decision_engine.agentic_analyzer import create_analyzer

    counts: dict[str, int] = {}
    if not rows:
        return counts
    # 1. One LLM client and one HTTP client for the batch.
    analyzer = create_analyzer(db)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT},
                                 event_hooks={"request": [_only_public_requests]}) as client:
        # 2. One name at a time (each is a few web requests and 1-2 LLM calls).
        for row in rows:
            await discover_one(db, row, analyzer, client)
            counts[row.status] = counts.get(row.status, 0) + 1
    return counts


async def discover_tools_for_analysis(analysis_id: int | None, data: dict) -> None:
    """Background task after an analysis: log and look up the tools it
    suggested that the catalog doesn't have. Never raises."""
    from database.pg_connections import SessionLocal

    db = SessionLocal()
    try:
        # 1. Missing names from this analysis.
        rows = record_suggestions(db, suggested_tool_names(data), analysis_id)
        # 2. Look them up now.
        if rows:
            counts = await process(db, rows)
            logger.info("[tool-discovery] analysis %s: %s", analysis_id, counts)
    except Exception:
        logger.exception("[tool-discovery] analysis %s: discovery failed", analysis_id)
    finally:
        db.close()


async def process_pending(db: Session, limit: int = 10) -> dict:
    """Hourly job and the admin "Run now": look up names still pending, and
    failed ones under MAX_ATTEMPTS, most suggested first."""
    # 1. What's left.
    rows = (
        db.query(ToolDiscovery)
        .filter(ToolDiscovery.status.in_(("pending", "failed")), ToolDiscovery.attempts < MAX_ATTEMPTS)
        .order_by(ToolDiscovery.times_suggested.desc(), ToolDiscovery.created_at)
        .limit(limit)
        .all()
    )
    # 2. Look them up.
    counts = await process(db, rows)
    return {"looked_up": len(rows), **counts}


# =========================================================================
# Admin view
# =========================================================================

def discovery_activity(db: Session, status: str = "all", limit: int = 50, offset: int = 0) -> dict:
    """Admin: counts per status, how many catalog tools were discovered, and
    the logged names (newest first) with their outcome and reason."""
    # 1. Counts per status.
    counts = dict(db.query(ToolDiscovery.status, func.count(ToolDiscovery.id)).group_by(ToolDiscovery.status).all())
    # 2. The rows asked for.
    q = db.query(ToolDiscovery)
    if status != "all":
        q = q.filter(ToolDiscovery.status == status)
    total = q.count()
    rows = q.order_by(func.coalesce(ToolDiscovery.processed_at, ToolDiscovery.created_at).desc()).offset(offset).limit(limit).all()
    # 3. Catalog size, split by where tools came from.
    catalog = dict(db.query(func.coalesce(AITool.source, "catalog"), func.count(AITool.id)).group_by(func.coalesce(AITool.source, "catalog")).all())
    return {
        "counts": counts,
        "catalog": {"total": sum(catalog.values()), "discovered": catalog.get("discovered", 0)},
        "total": total,
        "items": [{
            "id": r.id, "name": r.name, "status": r.status, "reason": r.reason,
            "times_suggested": r.times_suggested, "attempts": r.attempts,
            "website": r.website, "directory": r.directory, "directory_url": r.directory_url,
            "tool_id": r.tool_id, "first_analysis_id": r.first_analysis_id, "last_analysis_id": r.last_analysis_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        } for r in rows],
    }

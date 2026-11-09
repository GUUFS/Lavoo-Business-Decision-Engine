"""
The micromodel's "thinking" step. No LLM is used.

It reads a prompt in three steps:
  1. extract_facts: what does the prompt already say? (what they sell,
     where they sell, numbers, timeframes, what they tried, options)
  2. reason: what important information is still missing?
  3. build_questions: ask only for what is missing, using the details the
     prompt already gave.

Each step writes a short note to `trace`, so we can see why it decided
what it did.
"""
import re
from typing import Optional

# --------------------------------------------------------------------------
# Lexicons
# --------------------------------------------------------------------------

# Words that say what the business sells or what kind of business it is.
# Generic words ("business", "company", "startup") are deliberately NOT here:
# "fix my business" still doesn't tell us what is sold.
_INDUSTRY_WORDS = {
    "store", "shop", "app", "agency", "restaurant", "cafe",
    "bakery", "brand", "shopify", "ecommerce", "e-commerce", "saas",
    "clinic", "salon", "studio", "firm", "practice", "marketplace", "gym",
    "school", "academy", "hotel", "pharmacy", "supermarket", "boutique",
    "farm", "poultry", "logistics", "catering", "laundry", "spa",
    "barbershop", "barber", "consultancy", "consulting", "coaching",
    "tutoring", "printing", "real estate", "fashion", "clothing", "clothes",
    "skincare", "cosmetics", "perfume", "perfumes", "fragrance", "hair",
    "wigs", "shoes", "furniture", "electronics", "gadgets", "phone cases",
    "food", "drinks", "juice", "cakes", "pastries", "events", "photography",
    "software", "fintech", "daycare", "hospital", "dental", "transport",
    "car wash", "mechanic", "construction", "interior", "cleaning",
    "newsletter", "podcast", "youtube channel", "course", "courses",
    "ebook", "digital products", "freelance", "freelancer", "freelancing",
    "designer", "developer", "copywriting", "bookkeeping", "accounting",
    "law firm", "recruitment", "staffing", "travel", "tour", "fitness",
    "jewelry", "jewellery", "bags", "accessories", "grocery", "snacks",
    "bar", "lounge", "kitchen", "meal prep", "beauty", "nails", "makeup",
    "skincare brand", "candles", "soap", "art", "music", "film", "media",
    "marketing agency", "web design", "it services", "security", "solar",
    "agriculture", "agro", "fish", "livestock", "cosmetic", "thrift",
    "kids", "baby", "pet", "pets", "vet", "pharma", "health", "wellness",
    "edtech", "proptech", "insurance", "lending", "microfinance", "b2b",
    "d2c", "dtc", "subscription box", "dropshipping", "wholesale", "retail",
    # Service professionals: "I'm a coach" says what they sell (their service).
    "coach", "consultant", "therapist", "counsellor", "counselor", "trainer",
    "personal trainer", "tutor", "lawyer", "doctor", "nurse", "photographer",
    "makeup artist", "stylist", "caterer", "realtor", "estate agent",
    "architect", "virtual assistant", "planner", "event planner",
}

# Areas of a business. A prompt naming three or more of these and asking
# where to start ("marketing, cash, staff, product") needs a focus first.
_BUSINESS_AREAS = {
    "marketing": "marketing", "sales": "sales", "cash": "cash", "cash flow": "cash", "money": "cash",
    "finances": "cash", "staff": "staff", "team": "staff", "hiring": "staff", "employees": "staff",
    "product": "product", "products": "product", "customers": "customers", "customer service": "customers",
    "operations": "operations", "pricing": "pricing", "prices": "pricing", "suppliers": "suppliers",
    "stock": "stock", "inventory": "stock", "delivery": "delivery", "website": "website",
}
_WHERE_TO_START_RE = re.compile(
    r"where (?:do|should) (?:i|we) (?:start|begin)|what (?:do|should) (?:i|we) (?:fix|tackle|do) first"
    r"|everything is (?:going wrong|a mess|falling apart)|nothing is working",
    re.I,
)
# Creators and personal brands: saying "I'm a content creator" says what
# they do, even though nothing is "sold". Their questions are about
# platforms, audience and focus, not stock, orders or customers.
_CREATOR_RE = re.compile(
    r"\b(?:content creators?|creators?|influencers?|youtubers?|bloggers?|vloggers?|podcasters?|streamers?|"
    r"tiktokers?|instagrammers?|ugc|personal brand|public speaker|thought leader)\b"
    r"|\b(?:i|we)\s+(?:create|make|post|produce|share|publish|film|record)\s+(?:\w+\s){0,2}?"
    r"(?:content|videos?|posts?|reels?|shorts|episodes?|podcasts?|blogs?|articles?|newsletters?)\b"
    r"|\b(?:i|we)\s+(?:post|make videos|talk|share)\s+(?:on\s+\w+\s+)?about\b",
    re.I,
)
# Prompts that cover many topics at once ("content across various aspects
# of life"): the first thing to pin down is the focus.
_BROAD_SCOPE_RE = re.compile(
    r"\b(?:various|many|different|several|all)\s+(?:aspects?|areas?|topics?|niches?|things|parts)\b"
    r"|\baspects? of life\b|\beverything\b|\ball sorts of\b|\bwide range of\b|\bmany things\b",
    re.I,
)

# The idea named in "start a laundry pickup service for students": the words
# after "start a/an", up to "for", "in", "at" or the end of the sentence.
_IDEA_RE = re.compile(
    r"\b(?:start(?:ing)?|launch(?:ing)?|open(?:ing)?|set(?:ting)? up)\s+(?:a|an|my|our)\s+(?:new\s+)?"
    r"([a-z][a-z\s&'-]{2,50}?)(?=\s+(?:for|in|at|to|with|that|which|so)\b|[,.;!?]|$)",
    re.I,
)

_GENERIC_BUSINESS_WORDS = {"business", "businesses", "company", "startup", "side hustle", "venture", "brand new business"}

_CHANNEL_WORDS = {
    "online", "in-person", "in person", "physical", "instagram", "facebook",
    "tiktok", "whatsapp", "twitter", "x.com", "linkedin", "youtube",
    "website", "storefront", "store front", "jumia", "konga", "jiji",
    "amazon", "etsy", "ebay", "google", "meta ads", "google ads",
    "facebook ads", "dms", "walk-in", "walk in", "market stall", "offline",
}

# "I sell X", "we make X", "selling X" -> X names the product.
_SELLS_RE = re.compile(
    r"\b(?:i|we)\s+(?:sell|make|produce|offer|bake|cook|run|own|build|design|teach|import|export|manufacture|distribute)s?\s+"
    r"(?:a|an|the|my|our)?\s*([a-z][a-z\s&'-]{2,40}?)(?=[,.;!?]| and | but | to | in | on | for | from | with | at |$)",
    re.I,
)
_SELLING_RE = re.compile(r"\bselling\s+([a-z][a-z\s&'-]{2,30}?)(?=[,.;!?]| and | but | on | in | for | at |$)", re.I)

_MONEY_RE = re.compile(
    r"(?:[$£€₦]\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|million|thousand|bn)?)"
    r"|(?:\b\d[\d,]*(?:\.\d+)?\s?(?:k|m|million|thousand|bn)?\s?(?:naira|ngn|dollars?|usd|pounds?|gbp|euros?)\b)"
    r"|(?:\b\d[\d,]*(?:\.\d+)?(?:k|m)\b)",
    re.I,
)
_PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\s?percent\b", re.I)
_COUNT_UNITS = (
    "customers?|clients?|orders?|sales|users?|members?|followers?|visits?|visitors?|"
    "leads?|subscribers?|students?|patients?|downloads?|units?|products?|staff|"
    "employees?|people|buyers?|bookings?|enquiries|inquiries|signups?|sign-ups?|"
    "installs?|views?|likes?|impressions?|clicks?|deals?|projects?|contracts?|"
    "tables?|covers?|guests?|rooms?|trips?|deliveries|transactions?|accounts?|outlets?|branches|locations?"
)
_COUNT_RE = re.compile(rf"\b\d[\d,]*(?:\.\d+)?\s?(?:k|m)?\s+(?:\w+\s){{0,2}}?(?:{_COUNT_UNITS})\b", re.I)
_DURATION_RE = re.compile(
    r"\b\d+\s?(?:-\s?\d+\s?)?(?:days?|weeks?|months?|years?|yrs?|hours?|hrs?|quarters?)\b"
    r"|\b(?:last|this|past|next)\s+(?:week|month|year|quarter|season|christmas|holiday)\b"
    r"|\bsince\s+\w+|\bby\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b"
    r"|\b(?:yesterday|recently|lately|two months|three months|a month|a year|a week)\b",
    re.I,
)

_TRIED_RE = re.compile(
    r"\b(?:i've|ive|i have|we've|we have|i|we)?\s*(?:already\s+)?(?:tried|attempted|tested|ran|run|used|started|launched|hired|spent|paid for|did)\b[^.;!?]{0,60}"
    r"|\beven after\b[^.;!?]{0,60}|\bstill (?:no|not)\b",
    re.I,
)
# A "tried" hit only counts when it describes an action, not "I run a bakery"
# or "we started the business in 2019".
_TRIED_STRONG = re.compile(r"\b(?:tried|attempted|tested|even after|still no|still not|already)\b", re.I)

_OPEN_DECISION_RE = re.compile(
    r"\bwhich (?:one|idea|option|way|direction|should|to)\b"
    r"|\bwhat (?:should i|to|do i) (?:focus|prioriti[sz]e|do first|build|work on|start with|pick|choose)\b"
    r"|\b(?:too many|several|many|different) (?:ideas|options|things|projects)\b"
    r"|\b(?:deciding|decide|can't decide|cannot decide|choose|choosing|pick between) (?:what|which|between)\b"
    r"|\bprioriti[sz]e\b(?! (?:between|[a-z]+,))"
    r"|\bwhat (?:to|should i) focus on\b",
    re.I,
)
_COMPARE_RE = re.compile(r"\b(?:vs\.?|versus)\b|\bor\b", re.I)
_BINARY_DECISION_RE = re.compile(r"\b(?:should (?:i|we)|is it (?:worth|time)|do i need to)\b", re.I)

_PROBLEM_TYPES = [
    # Wanting to influence or help people (a goal about impact, not money).
    ("impact", re.compile(
        r"\b(?:influence|impact|affect|inspire|motivate|empower|uplift|transform|change|help|educate|reach)\s+"
        r"(?:\w+\s)?(?:people|others|lives|my audience|my followers|young people|the world|society|women|men|youths?)\b"
        r"|\b(?:people|others|lives|audience|followers)\s+positively\b"
        r"|\bpositive(?:ly)?\s+(?:impact|influence|change|effect|difference)\b"
        r"|\bmake (?:a|an) (?:difference|impact)\b|\bchange lives\b",
        re.I)),
    # Busy at some times and quiet at others ("busy on weekends but empty
    # Monday to Thursday"): a demand-pattern problem, not a staffing one.
    ("slow_periods", re.compile(
        r"\b(?:empty|quiet|slow|dead|no customers?)\b[^.!?]{0,40}\b(?:mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|"
        r"saturdays?|sundays?|weekdays?|weekends?|mornings?|afternoons?|evenings?|nights?|low season|off[- ]season)\b"
        r"|\bbusy (?:on|at|in|during)\b[^.!?]{0,40}\bbut\b",
        re.I)),
    ("start", re.compile(r"\b(?:start(?:ing)? a (?:new )?(?:business|company|startup)|want to start|business idea|launch(?:ing)? (?:a|my) (?:first|new)|which business (?:to|should))\b", re.I)),
    ("decline", re.compile(r"\b(?:dropp?(?:ed|ing)|declin\w*|fell|falling|down by|went down|reduced|reducing|slow(?:ed|ing)? down|dead|dried up|losing (?:customers|sales|money)|going down|sales are down|revenue is down|stopped buying)\b", re.I)),
    ("conversion", re.compile(r"\b(?:convert\w*|conversion|nobody buys|no one buys|not buying|visit\w* but|traffic but|views but|abandon\w*|checkout)\b", re.I)),
    ("retention", re.compile(r"\b(?:churn\w*|come back|coming back|repeat|retention|retain|one-time|once and never|cancel\w*)\b", re.I)),
    ("acquisition", re.compile(r"\b(?:more (?:customers|clients|leads|sales|users|members|followers|traffic)|get (?:customers|clients|leads)|find (?:customers|clients)|grow\w*|scale|scaling|reach more|visibility|awareness|go viral|engagement|ads? (?:aren't|are not|not) working"
                                r"|sales ?(?:person|people|rep|reps|team)|run(?:ning)? ads|advertis\w*)\b", re.I)),
    ("pricing", re.compile(
        r"\b(?:pric(?:e|es|ing)|charge|expensive|too high|too cheap|discount\w*|margin\w*|rate card|brand deals?|sponsorships?)\b"
        r"|\b(?:brands?|sponsors?|clients?)\s+(?:aren't|are not|don't|do not|won't|will not)\s+pay", re.I)),
    ("operations", re.compile(r"\b(?:overwhelm\w*|busy|time|delegate|hire|hiring|team|staff|process|system|cash ?flow|expenses|costs?|admin)\b", re.I)),
]


# --------------------------------------------------------------------------
# Step 1: facts
# --------------------------------------------------------------------------

def _find_words(lower: str, words: set) -> list[str]:
    found = []
    # Check longer phrases first, so "skincare brand" wins over "brand".
    for w in sorted(words, key=len, reverse=True):
        # Match whole words only, and skip a word already inside a longer match.
        if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", lower) and not any(w in f for f in found):
            found.append(w)
    return found


def _strip_durations(text: str) -> str:
    return _DURATION_RE.sub(" ", text)


def extract_facts(text: str) -> dict:
    lower = text.lower()

    # 1. What the business is: industry words, vague words like "business",
    #    and where it sells (Instagram, Jumia, a website).
    industry = _find_words(lower, _INDUSTRY_WORDS)
    generic = _find_words(lower, _GENERIC_BUSINESS_WORDS)
    channels = _find_words(lower, _CHANNEL_WORDS)
    # 2. Product phrases like "I sell perfumes" or "selling phone cases".
    sells = [m.group(1).strip() for m in _SELLS_RE.finditer(text)] + [m.group(1).strip() for m in _SELLING_RE.finditer(text)]
    # "I run a bakery" is caught by industry already; keep only product
    # phrases that aren't just generic words. "I sell on Jumia" / "sell
    # more" describe where or how much, not what.
    sells = [
        s for s in sells
        if s.lower() not in _GENERIC_BUSINESS_WORDS and len(s) > 2
        and not re.match(r"(?:on|in|at|to|through|via|online|more|better|less|well|it|them|things|stuff)\b", s, re.I)
    ]

    # 3. Timeframes ("3 months", "last week", "by March").
    durations = [m.group(0).strip() for m in _DURATION_RE.finditer(text)]
    # Metrics are read with the durations removed, so "in 3 months" or
    # "for 30 days" never counts as a business number.
    # 4. Business numbers: money, percentages and counts ("150 members").
    no_dur = _strip_durations(text)
    money = [m.group(0).strip() for m in _MONEY_RE.finditer(no_dur)]
    percents = [m.group(0).strip() for m in _PERCENT_RE.finditer(no_dur)]
    counts = [m.group(0).strip() for m in _COUNT_RE.finditer(no_dur)]

    # 5. Things already tried ("we tried TikTok", "even after a discount").
    tried = []
    if _TRIED_STRONG.search(text):
        tried = [m.group(0).strip() for m in _TRIED_RE.finditer(text) if _TRIED_STRONG.search(m.group(0)) or "spent" in m.group(0).lower()]

    # 6. What kind of problem it is (sales drop, getting customers, pricing...).
    #    A concrete business problem (a drop, conversion...) outranks the
    #    impact goal, so "views dropped" is a decline, not an impact question.
    problem_types = [name for name, rx in _PROBLEM_TYPES if rx.search(text)]
    if "impact" in problem_types and len(problem_types) > 1:
        problem_types.remove("impact")
        problem_types.append("impact")

    # 7. Creator or business? And does it cover many topics at once?
    creator = [m.group(0).strip() for m in _CREATOR_RE.finditer(text)]
    broad_scope = bool(_BROAD_SCOPE_RE.search(text))
    # 7b. Business areas named ("marketing, cash, staff, product"), in the
    #     order they appear, and whether they ask where to start.
    areas: list[str] = []
    for word in sorted(_BUSINESS_AREAS, key=lambda w: lower.find(w) if w in lower else 10**6):
        area = _BUSINESS_AREAS[word]
        if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", lower) and area not in areas:
            areas.append(area)
    where_to_start = bool(_WHERE_TO_START_RE.search(text))
    # 7c. A new business idea they name ("a laundry pickup service").
    idea_match = _IDEA_RE.search(text)
    idea = idea_match.group(1).strip() if idea_match else None
    if idea and idea.lower() in _GENERIC_BUSINESS_WORDS:
        idea = None

    # 8. Put it all together, plus what kind of decision it is (if any).
    return {
        "domain": "creator" if creator else "business",
        "creator": creator,
        "broad_scope": broad_scope,
        "areas": areas,
        "where_to_start": where_to_start,
        "idea": idea,
        "industry": industry,
        "generic_business": generic,
        "channels": channels,
        "sells": sells,
        "money": money,
        "percents": percents,
        "counts": counts,
        "durations": durations,
        "tried": tried,
        "problem_types": problem_types,
        "decision": _read_decision(text),
    }


def _read_decision(text: str) -> dict:
    """What kind of decision is this?
    none:    not a decision
    open:    choosing, but the options aren't named ("which should I do first?")
    binary:  a yes/no choice ("should I raise prices?")
    compare: the options are named ("Jumia or my own website")"""
    lower = text.lower()

    # 1. "Which should I do first?" style. It's open unless the options are listed.
    if _OPEN_DECISION_RE.search(lower):
        options = _named_options(text)
        if len(options) >= 2:
            return {"kind": "compare", "options": options}
        return {"kind": "open", "options": []}
    # 2. "Should I...?" style. Either options are listed, or it's a yes/no choice.
    if _BINARY_DECISION_RE.search(lower):
        options = _named_options(text)
        if len(options) >= 2:
            return {"kind": "compare", "options": options}
        # "Sales are down, what should I do?" asks for advice, not a choice.
        if re.search(r"\bwhat should (?:i|we) do\b", lower):
            return {"kind": "none", "options": []}
        return {"kind": "binary", "options": options}
    # 3. "X vs Y" with no question words.
    if re.search(r"\b(?:vs\.?|versus)\b", lower):
        return {"kind": "compare", "options": _named_options(text)}

    # 4. Not a decision.
    return {"kind": "none", "options": []}


def _named_options(text: str) -> list[str]:
    """Gets the options from "X, Y, or Z", "X or Y" or "X vs Y".
    "or not" isn't a second option."""
    # 1. Take the part after "should I" / "between", where the options are.
    m = re.search(r"\b(?:should (?:i|we)|whether to|between|is it better to)\s+(.+?)(?:[?.!]|$)", text, re.I)
    segment = m.group(1) if m else text

    # 2. Split it on "vs", commas or "or".
    if re.search(r"\bvs\.?\b|\bversus\b", segment, re.I):
        parts = re.split(r"\s+(?:vs\.?|versus)\s+", segment, flags=re.I)
    else:
        parts = re.split(r",\s*(?:or\s+)?|\s+or\s+|\s+and\s+(?=(?:a|an|the|my)?\s*\w+\s*\?)", segment, flags=re.I)
    # 3. Clean up and drop non-options like "not". Need at least two to count.
    options = [p.strip(" ?.!,") for p in parts if p and p.strip(" ?.!,")]
    options = [o for o in options if o.lower() not in {"not", "no", "nothing", "something else"}]
    return options if len(options) >= 2 else []


# --------------------------------------------------------------------------
# Step 2: reasoning
# --------------------------------------------------------------------------

def reason(text: str, history: Optional[dict] = None) -> dict:
    """Works out what is missing from the prompt.

    Returns {facts, gaps, trace, confidence}.
    history: what we already know about this user from earlier checkups,
    e.g. {"business": "a bakery"}. Anything in it is not asked again."""
    # 1. Read the facts out of the prompt.
    facts = extract_facts(text)
    trace: list[str] = []
    gaps: list[dict] = []
    fuzz = 0  # number of judgement calls made on weak evidence

    business_named = bool(facts["industry"] or facts["sells"] or facts["creator"])
    history_business = (history or {}).get("business")
    is_creator = facts["domain"] == "creator"

    # 2. Do we know what the business is? From the prompt, or from earlier checkups.
    if is_creator:
        trace.append(f"They're a creator ('{facts['creator'][0]}'), so ask about platforms, audience and focus, not stock or orders.")
    elif business_named:
        what = ", ".join((facts["sells"] or facts["industry"])[:2])
        trace.append(f"The prompt says what the business is: {what}.")
    elif history_business:
        trace.append(f"The prompt doesn't name the business, but earlier checkups say: {history_business}. Not asking again.")
        business_named = True
        fuzz += 1
    elif facts["generic_business"]:
        trace.append(f"It mentions a '{facts['generic_business'][0]}' but not what it sells.")
    elif facts["channels"]:
        trace.append(f"It names a channel ({facts['channels'][0]}) but not what is sold there.")
    else:
        trace.append("Nothing says what the business sells or does.")

    # 3. Is there hard evidence: a business number, or something already tried?
    metrics = facts["money"] + facts["percents"] + facts["counts"]
    if metrics:
        trace.append(f"It gives concrete numbers: {', '.join(metrics[:3])}.")
    if facts["tried"]:
        trace.append(f"It says what was already tried: {facts['tried'][0]}.")
    if facts["durations"] and not metrics:
        trace.append(f"'{facts['durations'][0]}' is a timeframe, not a business number.")
    has_evidence = bool(metrics or facts["tried"])

    # 4. Note the problem type and decision type for the steps below.
    problem = facts["problem_types"][0] if facts["problem_types"] else "general"
    trace.append(f"Problem type: {problem}.")
    decision = facts["decision"]

    # 5. Starting a new business: there's nothing to describe yet, so ask
    #    about the idea and resources instead, and stop here.
    if problem == "start" and not business_named:
        trace.append("They're starting out, so ask about the idea and resources, not current numbers.")
        gaps.append({"type": "missing_idea_context", "why": "no idea, budget or skills given for a new business"})
        return _finish(facts, gaps, trace, fuzz)
    # 5b. Starting a business they have named ("a laundry pickup service for
    #     students"): there are no sales yet, so ask for the budget, the
    #     timeline and any proof that people will pay, not current numbers.
    if problem == "start" and business_named:
        if facts["money"] and (facts["durations"] or facts["tried"]):
            trace.append("A named idea with a budget and a timeline or a test, so no questions are needed.")
            return _finish(facts, gaps, trace, fuzz)
        trace.append("A new business with the idea named but no sales yet: ask about budget, timeline and demand.")
        gaps.append({"type": "missing_launch_plan", "why": "new idea without budget, timeline or proof of demand"})
        return _finish(facts, gaps, trace, fuzz)

    # 6. A choice with no options named: we can't rank what we haven't been told.
    if decision["kind"] == "open":
        trace.append("It asks to choose between things without naming them, so it can't be ranked yet.")
        gaps.append({"type": "unnamed_options", "why": "decision with no options named"})
    elif decision["kind"] == "compare":
        trace.append(f"It compares named options: {', '.join(decision['options'][:3])}.")
    elif decision["kind"] == "binary":
        trace.append("It's a yes/no decision, so the option itself is known.")

    # 7. Covering many topics at once: the focus comes first, because the
    #    advice for "parenting" and "money" content is completely different.
    if facts["broad_scope"] and (is_creator or problem == "impact"):
        trace.append("It covers many topics at once, so ask which one or two to focus on and who it's for.")
        gaps.append({"type": "missing_focus", "why": "many topics, no main focus or audience"})
    # 7b. A business with many problems at once ("marketing, cash, staff,
    #     product... where do I start?"): ask which one hurts most first.
    elif not is_creator and len(facts["areas"]) >= 3 and (facts["where_to_start"] or facts["broad_scope"]):
        trace.append(f"It lists {len(facts['areas'])} problem areas ({', '.join(facts['areas'][:4])}) at once, "
                     "so ask which one hurts most before anything else.")
        gaps.append({"type": "missing_focus", "why": "many business problems at once, no main one"})
        # The focus question already asks what the main problem costs, so a
        # separate numbers question would repeat it.
        has_evidence = True

    # 8. Ask for whatever basics are still missing.
    if not business_named:
        gaps.append({"type": "missing_business_type", "why": "doesn't say what is sold"})
    if not has_evidence:
        gaps.append({"type": "missing_numbers_or_constraint", "why": "no metric and nothing already tried"})
        if facts["counts"] == [] and re.search(r"\d", text):
            fuzz += 1  # a number is present but couldn't be read as a metric

    # 9. For a drop in sales, knowing when it started changes the answer
    #    (a slow season, a new competitor, a price change).
    if problem == "decline" and not facts["durations"] and len(gaps) < 3:
        trace.append("It's a decline with no timing, and when it started changes the diagnosis.")
        gaps.append({"type": "missing_timeline", "why": "decline without a start date"})

    # 10. Nothing missing: no questions needed.
    if not gaps:
        trace.append("Business and hard evidence are both present, so no questions are needed.")

    return _finish(facts, gaps, trace, fuzz)


def _finish(facts: dict, gaps: list, trace: list, fuzz: int) -> dict:
    # Start fairly sure, and get less sure for each guess made on weak evidence.
    confidence = max(0.3, round(0.9 - 0.15 * fuzz, 2))
    # Never ask more than 3 questions.
    return {"facts": facts, "gaps": gaps[:3], "trace": trace, "confidence": confidence}


# --------------------------------------------------------------------------
# Step 3: questions
# --------------------------------------------------------------------------

_NUMBERS_BY_PROBLEM = {
    "conversion": "How many visitors or enquiries do you get in a typical month, and how many of them buy?",
    "retention": "Out of every 10 customers, roughly how many buy again, and what have you tried to bring them back?",
    "acquisition": "How many new customers or leads do you get in a month now, and where do most of them come from?",
    "pricing": "What do you charge now, and roughly what do competitors charge for the same thing?",
    "decline": "What were your monthly sales before the drop, and what are they now?",
    "operations": "How many people are on the team, and roughly how many hours a week go into this?",
    "slow_periods": ("Roughly how many customers or sales do you get on a quiet day compared with a busy one, "
                     "and what have you already tried on the quiet days?"),
}
# The numbers that settle a choice between two ways of spending ("hire a
# sales person or run ads?"): the money available and the starting point.
_DECISION_NUMBERS = ("What budget do you have for this, and roughly how many customers or sales "
                     "do you get in a month now (and where do most of them come from)?")


def _creator_numbers_question(channel: Optional[str], problem: str) -> str:
    """The "numbers" question for a creator: platform and audience size,
    plus what success looks like for their kind of goal."""
    audience = (f"Roughly how many people follow or watch you on {_display_channel(channel)}"
                if channel else "Where do you post and roughly how many people follow or watch you")
    if problem == "impact":
        return (f"{audience}? And what would positive influence look like in your audience "
                "(comments, messages, people acting on what you share)?")
    if problem == "decline":
        return f"{audience} now, compared with before the drop? And did anything change around then?"
    if problem == "pricing":
        return f"{audience}? And what do brands pay you per post now, compared with creators your size?"
    return f"{audience}? And what have you already tried to grow it?"


def write_question(gap_type: str, facts: dict, problem: str) -> str:
    """Writes the question for one missing piece of information, using the
    details the prompt already gave (platform, product, creator or business)."""
    # Details from the prompt that we can use in the wording.
    channel = facts["channels"][0] if facts["channels"] else None
    what = (facts["sells"] or facts["industry"] or [None])[0]
    is_creator = facts.get("domain") == "creator"

    # Focus. Creators: which topics, and for whom. Businesses with many
    # problems at once: which named area hurts most, and what it costs.
    if gap_type == "missing_focus":
        if not is_creator and facts.get("areas"):
            listed = _join_areas(facts["areas"])
            return (f"Of {listed}, which one is hurting the business most right now, "
                    "and what is it costing you (lost sales, unpaid bills, hours)?")
        return "Which one or two topics do you most want to be known for, and who is the person you most want your content to help?"

    # What the business is: mention the platform or word they used, if any.
    if gap_type == "missing_business_type":
        if channel:
            return f"What do you sell on {_display_channel(channel)}, and who usually buys it?"
        if facts["generic_business"]:
            return f"What does your {facts['generic_business'][0]} sell or do, and who are your customers?"
        return "What does your business sell or do, and how do customers usually reach you (in person, online, a marketplace)?"
    # Numbers: ask for the number that matters for this kind of problem.
    if gap_type == "missing_numbers_or_constraint":
        if is_creator:
            return _creator_numbers_question(channel, problem)
        if problem == "impact":
            return ("Who do you most want to reach, how do you share your work with them today, "
                    "and roughly how many people see it?")
        # A choice between named options (not about price): budget and starting point.
        if facts["decision"]["kind"] == "compare" and problem != "pricing":
            return _DECISION_NUMBERS
        q = _NUMBERS_BY_PROBLEM.get(problem)
        if q:
            return q
        if what:
            return f"What are the numbers for your {what} right now (monthly revenue, customers or orders), and what have you already tried?"
        return "What's one concrete number here (monthly revenue, customers, orders), or something you've already tried?"
    # The other gap types have one fixed question each.
    if gap_type == "unnamed_options":
        return "What are the specific options you're choosing between?"
    if gap_type == "missing_timeline":
        return "When did this start, and did anything change around then (prices, ads, season, competitors)?"
    if gap_type == "missing_idea_context":
        return "What business are you thinking of starting, and what budget, skills or contacts do you have to start with?"
    # A named new idea: budget, timeline and proof people will pay.
    if gap_type == "missing_launch_plan":
        named = facts.get("idea") or what
        idea = f"the {named}" if named else "it"
        return (f"What budget and timeline do you have for {idea}, and what have you seen so far that says "
                "people will pay for it (pre-orders, a waitlist, people asking for it)?")
    return ""


def _join_areas(areas: list[str]) -> str:
    """'marketing, cash, staff and product' from the areas a prompt named."""
    # 1. Up to four areas, in the order they were written.
    named = areas[:4]
    # 2. Join them like a sentence.
    return named[0] if len(named) == 1 else ", ".join(named[:-1]) + " and " + named[-1]


def _display_channel(c: str) -> str:
    """How a channel reads inside a question: "TikTok", "your website"."""
    # 1. Names with their own spelling, and channels that read as "your ...".
    special = {"tiktok": "TikTok", "whatsapp": "WhatsApp", "linkedin": "LinkedIn", "youtube": "YouTube", "dms": "DMs",
               "website": "your website", "storefront": "your storefront", "store front": "your storefront"}
    # 2. Anything else: capitalised if it is one word.
    return special.get(c, c.title() if c.isalpha() else c)


def build_questions(result: dict) -> list[dict]:
    problem = result["facts"]["problem_types"][0] if result["facts"]["problem_types"] else "general"
    out = []
    # One question per missing piece, numbered q1, q2, q3.
    for i, g in enumerate(result["gaps"]):
        q = write_question(g["type"], result["facts"], problem)
        if q:
            out.append({"id": f"q{i+1}", "question": q, "gap_type": g["type"]})
    return out


def classify_question(question: str) -> str:
    """Works out which gap a question is asking about, so questions
    written by the LLM can be reused for the same gap."""
    q = question.lower()
    # Check the most specific kinds first. Anything else is a "numbers" question.
    if re.search(r"\b(which (?:one or two |one |two )?topics?|known for|your niche|main focus|focus on one|who is the person|hurting the business most|which (?:one|area|problem) (?:is )?(?:hurt|matter|cost)s? (?:you )?most)\b", q):
        return "missing_focus"
    if re.search(r"\b(pre-?orders?|waitlist|will pay for it|proof (?:that )?people|people will pay)\b", q):
        return "missing_launch_plan"
    if re.search(r"\b(options?|choosing between|ideas? (?:are|you're)|on the table)\b", q):
        return "unnamed_options"
    if re.search(r"\b(thinking of starting|want to start|budget, skills)\b", q):
        return "missing_idea_context"
    if re.search(r"\b(when did|how long ago|did anything change|since when)\b", q):
        return "missing_timeline"
    if re.search(r"\b(what does your|what do you sell|what product|what service|what kind of business|what industry|who (?:are|usually) (?:your )?(?:customers|buys))\b", q):
        return "missing_business_type"
    return "missing_numbers_or_constraint"

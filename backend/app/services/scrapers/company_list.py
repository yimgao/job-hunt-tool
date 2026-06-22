"""Verified company lists for ATS scrapers.

Each entry: (slug, display_name, tier)
  tier = "f500"    Fortune 500 / large public company
  tier = "tier1"   Post-IPO unicorn / late-stage ($1B+)
  tier = "tier2"   Series C-D growth stage

All slugs verified live — 404s are silently skipped by scrapers.
Last verified: 2026-06-22
"""
from __future__ import annotations

# ── Greenhouse  ───────────────────────────────────────────────────────────────
# Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
GREENHOUSE: list[tuple[str, str, str]] = [
    # Fortune 500 / major public companies
    ("stripe",           "Stripe",              "f500"),
    ("cloudflare",       "Cloudflare",          "f500"),
    ("datadog",          "Datadog",             "f500"),
    ("elastic",          "Elastic",             "f500"),
    ("okta",             "Okta",                "f500"),
    ("pagerduty",        "PagerDuty",           "f500"),
    ("gitlab",           "GitLab",              "f500"),
    ("twilio",           "Twilio",              "f500"),
    ("squarespace",      "Squarespace",         "f500"),
    ("block",            "Block (Square)",      "f500"),
    ("pinterest",        "Pinterest",           "f500"),
    ("twitch",           "Twitch",              "f500"),
    ("sofi",             "SoFi",                "f500"),
    ("mongodb",          "MongoDB",             "f500"),
    ("databricks",       "Databricks",          "f500"),
    ("amplitude",        "Amplitude",           "f500"),

    # Unicorn / late-stage
    ("airbnb",           "Airbnb",              "tier1"),
    ("doordashusa",      "DoorDash",            "tier1"),
    ("lyft",             "Lyft",                "tier1"),
    ("coinbase",         "Coinbase",            "tier1"),
    ("discord",          "Discord",             "tier1"),
    ("duolingo",         "Duolingo",            "tier1"),
    ("figma",            "Figma",               "tier1"),
    ("reddit",           "Reddit",              "tier1"),
    ("robinhood",        "Robinhood",           "tier1"),
    ("roblox",           "Roblox",              "tier1"),
    ("dropbox",          "Dropbox",             "tier1"),
    ("asana",            "Asana",               "tier1"),
    ("instacart",        "Instacart",           "tier1"),
    ("brex",             "Brex",                "tier1"),
    ("waymo",            "Waymo",               "tier1"),
    ("spacex",           "SpaceX",              "tier1"),
    ("anthropic",        "Anthropic",           "tier1"),
    ("toast",            "Toast",               "tier1"),
    ("tripactions",      "Navan (TripActions)", "tier1"),
    ("grafanalabs",      "Grafana Labs",        "tier1"),
    ("gusto",            "Gusto",               "tier1"),
    ("intercom",         "Intercom",            "tier1"),
    ("airtable",         "Airtable",            "tier1"),
    ("chime",            "Chime",               "tier1"),

    # Series C-D / mid-tier
    ("postman",          "Postman",             "tier2"),
    ("fivetran",         "Fivetran",            "tier2"),
    ("vercel",           "Vercel",              "tier2"),
    ("hightouch",        "Hightouch",           "tier2"),
    ("carta",            "Carta",               "tier2"),
    ("pandadoc",         "PandaDoc",            "tier2"),
    ("mixpanel",         "Mixpanel",            "tier2"),
    ("typeform",         "Typeform",            "tier2"),
    ("lattice",          "Lattice",             "tier2"),
    ("netlify",          "Netlify",             "tier2"),
    ("planetscale",      "PlanetScale",         "tier2"),
    ("betterment",       "Betterment",          "tier2"),
]

# ── Lever  ────────────────────────────────────────────────────────────────────
# Endpoint: https://api.lever.co/v0/postings/{slug}?mode=json
# NOTE: most major companies migrated away from Lever; keep only verified working slugs
LEVER: list[tuple[str, str, str]] = [
    ("mistral",          "Mistral AI",          "tier1"),
    ("highspot",         "Highspot",            "tier2"),
]

# ── SmartRecruiters  ─────────────────────────────────────────────────────────
# Endpoint: https://api.smartrecruiters.com/v1/companies/{slug}/postings
SMARTRECRUITERS: list[tuple[str, str, str]] = [
    ("Canva",            "Canva",               "tier1"),
    ("Palantir",         "Palantir",            "f500"),
    ("Uber",             "Uber",                "f500"),
]

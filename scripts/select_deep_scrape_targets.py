#!/usr/bin/env python3
"""Select a targeted set of URLs for expensive deep-scraping.

Filter logic:
- Include: Reddit, Medium, news sites, parenting blogs, essays, long-form
- Exclude: video/short-form platforms (YouTube, TikTok, IG, FB, Threads),
  app listings, support/promotional pages
- Only URLs previously REJECTED by cheap extraction (snippet too thin to judge)

Outputs:
  data/benchmark/v2/scraped/deep_scrape_targets.jsonl   — curated list
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REJECTED = Path("data/benchmark/v2/scraped/rejected.jsonl")
CANDIDATES = Path("data/benchmark/v2/scraped/candidates.jsonl")
OUT = Path("data/benchmark/v2/scraped/deep_scrape_targets.jsonl")

# Domains likely to have real article-length content
HIGH_SIGNAL_DOMAINS = {
    # News / TV
    "theguardian.com", "bbc.com", "bbc.co.uk", "cnn.com", "nytimes.com",
    "washingtonpost.com", "reuters.com", "apnews.com", "npr.org",
    "skynews.com.au", "kplctv.com", "kbtx.com",
    "tech.yahoo.com", "yahoo.com", "dailymail.co.uk", "nypost.com",
    "heise.de", "spiegel.de", "zeit.de", "sueddeutsche.de",
    "lefigaro.fr", "lemonde.fr",
    "lavanguardia.com", "elpais.com", "elmundo.es",
    "corriere.it", "repubblica.it",
    "rbc.ru", "lenta.ru",
    "asahi.com", "nikkei.com",
    "chosun.com", "joongang.co.kr",
    "ynet.co.il",
    "aljazeera.com",
    "novinky.cz", "idnes.cz", "hln.be", "bd.nl",
    "ntv.com.tr", "hurriyet.com.tr", "milliyet.com.tr",
    # Parenting / family
    "internetmatters.org", "commonsensemedia.org", "parents.com",
    "parenting.com", "healthychildren.org",
    "oudersvannu.nl", "doctissimo.fr", "madrees.com",
    # Essays / long-form
    "medium.com", "substack.com", "note.com", "brunch.co.kr",
    "blog.naver.com", "tistory.com",
    # Research / academic
    "apa.org", "unicef.org", "theconversation.com",
}

# Reddit always worth a look (community = rich context)
REDDIT_DOMAIN = "reddit.com"

# Domains that are clearly low-yield even with deep scrape
EXCLUDE_DOMAINS = {
    "youtube.com", "m.youtube.com", "youtu.be",
    "tiktok.com", "vm.tiktok.com",
    "instagram.com",
    "facebook.com", "m.facebook.com",
    "threads.com", "threads.net",
    "x.com", "twitter.com",
    "play.google.com", "apps.apple.com",
    "chatgpt.com", "chat.openai.com",
    "help.openai.com", "openai.com",
    "support.apple.com", "discussions.apple.com",
    "gemini.google.com",
    "lemon8-app.com",
    "dreamfaceapp.com", "galaxykids.ai",
    "runtheprompts.com",
    "pinterest.com",
    # Short-form / listicle aggregators
    "steemit.com",
}

# Reject reasons that suggest deep scrape would help
SALVAGE_REJECT_REASONS = [
    "llm:not enough",
    "llm:insufficient",
    "llm:no specific",
    "llm:no genuine",
    "llm:not an actual",
    "llm:scraped content does not",
    "too_short",  # short snippet = deep scrape might reveal more
]


def is_high_signal(domain: str) -> bool:
    if not domain:
        return False
    if domain in EXCLUDE_DOMAINS:
        return False
    if domain == REDDIT_DOMAIN or domain.endswith(".reddit.com"):
        return True
    if domain in HIGH_SIGNAL_DOMAINS:
        return True
    # Permissive heuristic for news/blog domains we didn't enumerate:
    # TLDs that are usually article content vs social
    if any(domain.endswith(f".{tld}") for tld in ("com", "co.uk", "co.kr", "co.jp", "de", "fr", "it", "es", "pt", "pl", "cz", "nl", "ru", "ua", "tr", "jp", "kr", "br", "mx", "ar", "in", "ae", "sa", "au")):
        # But only if there's a substantive title/snippet and not a blocklisted base
        if not any(domain.endswith(excl) for excl in EXCLUDE_DOMAINS):
            return True
    return False


def reject_suggests_salvage(reason: str) -> bool:
    if not reason:
        return True  # no reason = just try
    rl = reason.lower()
    return any(s.lower() in rl for s in SALVAGE_REJECT_REASONS)


def main():
    # Load rejected + candidates
    rejected = {}
    with open(REJECTED) as f:
        for line in f:
            r = json.loads(line)
            u = r.get("source_url") or r.get("url")
            if u:
                rejected[u] = r

    with open(CANDIDATES) as f:
        candidates = [json.loads(l) for l in f]

    # Filter
    targets = []
    by_reason = Counter()
    by_domain = Counter()

    for cand in candidates:
        url = cand["url"]
        if url not in rejected:
            continue  # either accepted or not processed

        r = rejected[url]
        reject_reason = r.get("reject_reason", "")
        domain = cand.get("domain", "")

        if not is_high_signal(domain):
            continue

        if not reject_suggests_salvage(reject_reason):
            continue

        targets.append(cand)
        by_domain[domain] += 1

    # Sort: Reddit first (highest signal), then others by count
    targets.sort(key=lambda c: (
        0 if c.get("domain") == REDDIT_DOMAIN else 1,
        c.get("domain", ""),
    ))

    # Write
    with open(OUT, "w") as f:
        for t in targets:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"Selected {len(targets)} URLs for deep scraping")
    print()
    print(f"Top domains in selection:")
    for d, c in by_domain.most_common(20):
        print(f"  {c:3d}  {d}")
    print()
    print(f"By language:")
    langs = Counter(c.get("query_lang") for c in targets)
    for l, c in langs.most_common():
        print(f"  {c:3d}  {l}")
    print()
    print(f"Written to {OUT}")


if __name__ == "__main__":
    main()

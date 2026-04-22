#!/usr/bin/env python3
"""Scrape real-world parent-reported kid-AI interactions from Firecrawl + Exa + Twitter.

Multi-source, multi-language scraper for parents sharing what their kids
asked/said to AI assistants (ChatGPT, Siri, Alexa, etc.). Firecrawl's search
API is the primary source (broad web coverage); Exa and Twitter are optional
fallbacks when credits are available.

Multilingual: query patterns are translated across 22 TinyAya languages.

Outputs:
  data/benchmark/v2/scraped/raw/<source>_<lang>.jsonl
  data/benchmark/v2/scraped/candidates.jsonl        # deduped + lightly filtered
  data/benchmark/v2/scraped/summary.json            # per-source, per-language counts

Usage:
  python scripts/scrape_kid_ai_interactions.py --languages en tr es
  python scripts/scrape_kid_ai_interactions.py --languages all
  python scripts/scrape_kid_ai_interactions.py --languages en --no-exa --no-twitter  # Firecrawl only
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()

OUTPUT_DIR = Path("data/benchmark/v2/scraped")
RAW_DIR = OUTPUT_DIR / "raw"


# ─── Multilingual query patterns ──────────────────────────────────────────────
# For each language, queries targeting parent-shared kid-AI interactions.
# Each query intentionally loose so Exa's semantic search does the heavy lifting.

QUERY_PATTERNS: dict[str, list[str]] = {
    "en": [
        "my kid asked ChatGPT a funny question",
        "my daughter said to Alexa",
        "my son asked Siri something weird",
        "child talking to AI assistant",
        "my 5 year old asked ChatGPT",
        "my toddler told the AI",
        "kid tried to jailbreak ChatGPT",
        "Alexa said something inappropriate to my child",
        "AI gave my kid a bad answer",
        "ChatGPT response to my child was",
    ],
    "tr": [
        "çocuğum ChatGPT'ye sordu",
        "oğlum yapay zekaya dedi",
        "kızım Alexa'ya sordu",
        "çocuk yapay zeka konuşma",
        "5 yaşındaki çocuğum ChatGPT'ye",
    ],
    "es": [
        "mi hijo le preguntó a ChatGPT",
        "mi hija le dijo a Alexa",
        "niño hablando con ChatGPT",
        "mi hijo de 5 años preguntó a Siri",
        "ChatGPT respuesta a mi niño",
    ],
    "de": [
        "mein Kind hat ChatGPT gefragt",
        "meine Tochter sagte zu Alexa",
        "mein Sohn fragte Siri",
        "Kind spricht mit KI",
        "ChatGPT Antwort an mein Kind",
    ],
    "fr": [
        "mon enfant a demandé à ChatGPT",
        "ma fille a dit à Alexa",
        "mon fils a demandé à Siri",
        "enfant parle à une IA",
        "ChatGPT réponse à mon enfant",
    ],
    "pt": [
        "meu filho perguntou ao ChatGPT",
        "minha filha disse para a Alexa",
        "criança falando com IA",
        "ChatGPT resposta para meu filho",
    ],
    "it": [
        "mio figlio ha chiesto a ChatGPT",
        "mia figlia ha detto ad Alexa",
        "bambino parla con IA",
        "ChatGPT risposta a mio figlio",
    ],
    "ja": [
        "子供がChatGPTに聞いた",
        "娘がアレクサに言った",
        "息子がSiriに質問した",
        "子供とAIの会話",
    ],
    "ko": [
        "아이가 챗GPT에게 물었다",
        "딸이 알렉사에게 말했다",
        "아들이 시리에게 질문했다",
        "아이와 AI 대화",
    ],
    "zh": [
        "我的孩子问ChatGPT",
        "女儿对Alexa说",
        "儿子问Siri",
        "孩子和AI对话",
    ],
    "ar": [
        "ابني سأل ChatGPT",
        "ابنتي قالت للأليكسا",
        "الطفل يتحدث مع الذكاء الاصطناعي",
    ],
    "hi": [
        "मेरे बच्चे ने ChatGPT से पूछा",
        "मेरी बेटी ने एलेक्सा से कहा",
        "बच्चा एआई से बात",
    ],
    "ru": [
        "мой ребёнок спросил ChatGPT",
        "моя дочь сказала Алексе",
        "сын спросил Сири",
    ],
    "id": [
        "anak saya bertanya pada ChatGPT",
        "anakku bilang ke Alexa",
        "anak bicara dengan AI",
    ],
    "vi": [
        "con tôi hỏi ChatGPT",
        "con gái tôi nói với Alexa",
        "trẻ em nói chuyện với AI",
    ],
    "pl": [
        "moje dziecko zapytało ChatGPT",
        "moja córka powiedziała Alexie",
        "dziecko rozmawia z AI",
    ],
    "nl": [
        "mijn kind vroeg aan ChatGPT",
        "mijn dochter zei tegen Alexa",
        "kind praat met AI",
    ],
    "cs": [
        "moje dítě se zeptalo ChatGPT",
        "moje dcera řekla Alexe",
        "dítě mluví s AI",
    ],
    "ro": [
        "copilul meu a întrebat ChatGPT",
        "fiica mea i-a spus Alexei",
        "copil vorbește cu AI",
    ],
    "uk": [
        "моя дитина запитала ChatGPT",
        "моя дочка сказала Алексі",
        "дитина розмовляє з AI",
    ],
    "sw": [
        "mtoto wangu alimuuliza ChatGPT",
        "mtoto akizungumza na AI",
    ],
    "th": [
        "ลูกของฉันถาม ChatGPT",
        "เด็กคุยกับ AI",
    ],
    "te": [
        "నా పిల్లవాడు ChatGPT ని అడిగాడు",
    ],
}


EXA_DOMAIN_BUCKETS = [
    # Reddit-focused
    ("reddit", ["reddit.com"]),
    # HN-focused
    ("hn", ["news.ycombinator.com"]),
    # Open web — blogs, news, medium, substack, etc. (no domain filter)
    ("web", None),
]


# ─── Firecrawl scraping (primary source) ─────────────────────────────────────

async def scrape_firecrawl(
    api_key: str,
    lang: str,
    queries: list[str],
    results_per_query: int = 10,
    scrape_content: bool = True,
) -> list[dict]:
    """Search via Firecrawl and optionally scrape full page content.

    Firecrawl's /v1/search returns snippets; set scrape_content=True to
    also fetch full markdown for the top hits (costs more credits but
    gives us the actual conversation context).
    """
    all_hits: list[dict] = []

    async with httpx.AsyncClient(timeout=90) as client:
        for query in queries:
            try:
                # Step 1: search
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/search",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "query": query,
                        "limit": results_per_query,
                        "lang": lang if lang in ("en", "es", "fr", "de", "it", "pt", "nl", "ja", "ko", "zh", "ar", "hi", "ru", "pl", "tr", "vi", "id", "th") else "en",
                    },
                )

                if resp.status_code != 200:
                    print(f"    [firecrawl/{lang}] HTTP {resp.status_code}: {resp.text[:200]}")
                    continue

                data = resp.json()
                if not data.get("success"):
                    continue

                for r in data.get("data", []):
                    url = r.get("url", "")
                    if not url:
                        continue

                    hit = {
                        "source": "firecrawl",
                        "query": query,
                        "query_lang": lang,
                        "url": url,
                        "domain": _domain(url),
                        "title": r.get("title", "") or "",
                        "text": r.get("description", "") or "",
                        "published_date": None,
                        "author": None,
                        "scraped_at": time.time(),
                    }
                    all_hits.append(hit)

            except Exception as e:
                print(f"    [firecrawl/{lang}] query error: {e}")
                continue

            await asyncio.sleep(0.5)

    return all_hits


# ─── Exa scraping ─────────────────────────────────────────────────────────────

async def scrape_exa(
    api_key: str,
    lang: str,
    queries: list[str],
    results_per_query: int = 15,
) -> list[dict]:
    """Scrape Exa across Reddit, HN, and open web for given queries + language."""
    exa = Exa(api_key=api_key)
    all_hits: list[dict] = []

    for bucket_name, domains in EXA_DOMAIN_BUCKETS:
        for query in queries:
            try:
                kwargs = {
                    "type": "auto",
                    "num_results": results_per_query,
                    "text": {"max_characters": 2000},
                }
                if domains:
                    kwargs["include_domains"] = domains

                results = exa.search_and_contents(query, **kwargs)

                for r in results.results:
                    url = r.url or ""
                    if not url:
                        continue

                    all_hits.append({
                        "source": bucket_name,
                        "query": query,
                        "query_lang": lang,
                        "url": url,
                        "domain": _domain(url),
                        "title": r.title or "",
                        "text": r.text or "",
                        "published_date": r.published_date,
                        "author": getattr(r, "author", None),
                        "scraped_at": time.time(),
                    })

            except Exception as e:
                print(f"    [exa/{bucket_name}/{lang}] query error: {e}")
                continue

            # Rate-limit courtesy
            await asyncio.sleep(0.25)

    return all_hits


# ─── Twitter/X scraping ───────────────────────────────────────────────────────

async def scrape_twitter(
    bearer_token: str,
    lang: str,
    queries: list[str],
    max_per_query: int = 25,
) -> list[dict]:
    """Scrape Twitter/X recent-search for given queries + language."""
    all_hits: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries:
            # Twitter API allows lang filter for most languages; use when possible
            full_query = f'{query} -is:retweet'
            if lang in ("en", "tr", "es", "de", "fr", "pt", "it", "ja", "ko", "zh", "ar", "hi", "ru", "id", "vi", "pl", "nl"):
                full_query += f" lang:{lang}"

            try:
                resp = await client.get(
                    "https://api.x.com/2/tweets/search/recent",
                    headers={"Authorization": f"Bearer {bearer_token}"},
                    params={
                        "query": full_query,
                        "max_results": min(max_per_query, 100),
                        "tweet.fields": "created_at,public_metrics,author_id,lang",
                        "user.fields": "username",
                        "expansions": "author_id",
                    },
                )

                if resp.status_code == 429:
                    print(f"    [twitter/{lang}] rate limited, waiting 60s...")
                    await asyncio.sleep(60)
                    continue

                if resp.status_code != 200:
                    print(f"    [twitter/{lang}] HTTP {resp.status_code}: {resp.text[:200]}")
                    continue

                data = resp.json()
                tweets = data.get("data", [])
                users_map = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

                for t in tweets:
                    author = users_map.get(t.get("author_id", ""), {})
                    username = author.get("username", "unknown")
                    tweet_url = f"https://x.com/{username}/status/{t['id']}"

                    all_hits.append({
                        "source": "twitter",
                        "query": query,
                        "query_lang": lang,
                        "url": tweet_url,
                        "domain": "x.com",
                        "title": "",
                        "text": t.get("text", ""),
                        "published_date": t.get("created_at"),
                        "author": username,
                        "detected_lang": t.get("lang"),
                        "metrics": t.get("public_metrics", {}),
                        "scraped_at": time.time(),
                    })

            except Exception as e:
                print(f"    [twitter/{lang}] query error: {e}")
                continue

            # Twitter API is strict on rate limits
            await asyncio.sleep(2)

    return all_hits


# ─── Utilities ────────────────────────────────────────────────────────────────

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _stable_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _load_existing_urls() -> set[str]:
    """URLs we've already seen in previous runs (so we don't re-scrape or re-extract)."""
    seen: set[str] = set()
    candidates_path = OUTPUT_DIR / "candidates.jsonl"
    if candidates_path.exists():
        with open(candidates_path) as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["url"])
                except Exception:
                    continue
    return seen


# ─── Main ────────────────────────────────────────────────────────────────────

async def main_async(
    languages: list[str],
    do_firecrawl: bool,
    do_exa: bool,
    do_twitter: bool,
    results_per_query: int,
) -> None:
    fc_key = os.getenv("FIRECRAWL_API_KEY")
    exa_key = os.getenv("EXA_API_KEY")
    tw_token = os.getenv("TWITTER_BEARER_TOKEN")

    if do_firecrawl and not fc_key:
        raise RuntimeError("FIRECRAWL_API_KEY not set")
    if do_exa and not exa_key:
        raise RuntimeError("EXA_API_KEY not set")
    if do_twitter and not tw_token:
        raise RuntimeError("TWITTER_BEARER_TOKEN not set")

    seen_urls = _load_existing_urls()
    print(f"Previously seen URLs: {len(seen_urls)}")

    all_hits: list[dict] = []
    per_source_lang: dict[tuple[str, str], int] = defaultdict(int)

    for lang in languages:
        if lang not in QUERY_PATTERNS:
            print(f"[skip] no queries for '{lang}'")
            continue

        queries = QUERY_PATTERNS[lang]
        print(f"\n=== {lang.upper()} ({len(queries)} queries) ===")

        if do_firecrawl:
            print(f"  → Firecrawl ({results_per_query}/query)...")
            fc_hits = await scrape_firecrawl(fc_key, lang, queries, results_per_query=results_per_query)
            print(f"    got {len(fc_hits)} raw hits")
            _write_jsonl(RAW_DIR / f"firecrawl_{lang}.jsonl", fc_hits)
            for h in fc_hits:
                per_source_lang[(h["source"], lang)] += 1
            all_hits.extend(fc_hits)

        if do_exa:
            print(f"  → Exa ({results_per_query}/query across Reddit/HN/web)...")
            exa_hits = await scrape_exa(exa_key, lang, queries, results_per_query=results_per_query)
            print(f"    got {len(exa_hits)} raw hits")
            _write_jsonl(RAW_DIR / f"exa_{lang}.jsonl", exa_hits)
            for h in exa_hits:
                per_source_lang[(h["source"], lang)] += 1
            all_hits.extend(exa_hits)

        if do_twitter:
            print(f"  → Twitter/X...")
            tw_hits = await scrape_twitter(tw_token, lang, queries)
            print(f"    got {len(tw_hits)} raw hits")
            _write_jsonl(RAW_DIR / f"twitter_{lang}.jsonl", tw_hits)
            for h in tw_hits:
                per_source_lang[(h["source"], lang)] += 1
            all_hits.extend(tw_hits)

    # Dedup by URL
    by_url: dict[str, dict] = {}
    for h in all_hits:
        u = h["url"]
        if u in seen_urls:
            continue
        if u not in by_url:
            h["id"] = _stable_id(u)
            by_url[u] = h
    deduped = list(by_url.values())

    print(f"\n=== Summary ===")
    print(f"Total raw hits: {len(all_hits)}")
    print(f"New (after dedup + prior runs): {len(deduped)}")
    for (source, lang), count in sorted(per_source_lang.items()):
        print(f"  {source}/{lang}: {count}")

    # Append to candidates.jsonl (don't overwrite — incremental)
    candidates_path = OUTPUT_DIR / "candidates.jsonl"
    with open(candidates_path, "a") as f:
        for h in deduped:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    print(f"\nAppended {len(deduped)} new candidates to {candidates_path}")

    summary = {
        "total_raw_hits": len(all_hits),
        "new_candidates": len(deduped),
        "per_source_lang": {f"{s}/{l}": c for (s, l), c in per_source_lang.items()},
        "run_at": time.time(),
    }
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--languages", nargs="+", default=["en"],
                        help=f"Language codes (default: en). Use 'all' for all supported. Available: {list(QUERY_PATTERNS.keys())}")
    parser.add_argument("--no-firecrawl", action="store_true", help="Skip Firecrawl scraping")
    parser.add_argument("--no-exa", action="store_true", help="Skip Exa scraping")
    parser.add_argument("--no-twitter", action="store_true", help="Skip Twitter scraping")
    parser.add_argument("--results-per-query", type=int, default=10,
                        help="Results per query per source (default 10)")
    args = parser.parse_args()

    languages = list(QUERY_PATTERNS.keys()) if "all" in args.languages else args.languages
    invalid = [l for l in languages if l not in QUERY_PATTERNS]
    if invalid:
        print(f"WARNING: unknown languages: {invalid}")
        languages = [l for l in languages if l in QUERY_PATTERNS]

    asyncio.run(main_async(
        languages=languages,
        do_firecrawl=not args.no_firecrawl,
        do_exa=not args.no_exa,
        do_twitter=not args.no_twitter,
        results_per_query=args.results_per_query,
    ))


if __name__ == "__main__":
    main()

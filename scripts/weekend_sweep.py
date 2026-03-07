#!/usr/bin/env python3
"""
APEX Trading Intelligence System -- Weekend Macro Sweep
=======================================================
Standalone script (no Nebula dependency).

What it does:
  - Fetches Economic Times, MoneyControl, Reuters India/macro RSS feeds
  - Filters articles published in the last 48 hours
  - Scores each headline BULLISH / BEARISH / NEUTRAL via keyword scoring
  - Builds a WEEKEND_MACRO_SNAPSHOT dict (same schema the Nebula agent writes)
  - Writes snapshot to Redis key  WEEKEND_MACRO_SNAPSHOT  (JSON, TTL 72h)
  - Writes snapshot to            data/weekend_snapshot.json
  - All activity logged to stdout

Usage:
  python scripts/weekend_sweep.py
  python scripts/weekend_sweep.py --dry-run
  python scripts/weekend_sweep.py --hours 72
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any
from pathlib import Path


try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import redis as redis_lib
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | apex.weekend_sweep | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("apex.weekend_sweep")

RSS_FEEDS = {
    "economic_times_markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "economic_times_economy": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "moneycontrol_news": "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "moneycontrol_markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "reuters_india": "https://feeds.reuters.com/reuters/INtopNews",
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "reuters_markets": "https://feeds.reuters.com/reuters/marketsNews",
    "livemint_markets": "https://www.livemint.com/rss/markets",
    "livemint_economy": "https://www.livemint.com/rss/economy",
}

BULLISH_KEYWORDS = [
    "rally", "surge", "gain", "bull", "bullish", "breakout", "high", "rise",
    "positive", "growth", "record", "profit", "beat", "strong", "upgrade",
    "inflow", "fii buying", "dii buying", "rate cut", "stimulus", "boost",
    "recovery", "rebound", "outperform", "buy", "upside", "accumulate",
    "gdp growth", "easing", "dovish", "liquidity", "inflows", "green",
    "nifty up", "sensex up", "markets rise", "foreign inflow", "capex",
    "rbi rate cut", "fed pivot", "soft landing",
]

BEARISH_KEYWORDS = [
    "crash", "fall", "drop", "bear", "bearish", "breakdown", "low", "decline",
    "negative", "slowdown", "loss", "miss", "weak", "downgrade", "outflow",
    "fii selling", "rate hike", "hawkish", "tightening", "recession", "slump",
    "sell-off", "correction", "underperform", "sell", "downside", "red",
    "nifty falls", "sensex down", "markets fall", "foreign outflow", "tariff",
    "sanctions", "war", "conflict", "crisis", "default", "inflation surge",
    "crude spike", "oil spike", "geopolitical", "rbi hike", "fed hike",
    "stagflation", "rupee fall", "dollar surge",
]

MACRO_KEYWORDS = [
    "rbi", "fed", "fomc", "gdp", "inflation", "cpi", "wpi", "iip", "pmi",
    "crude", "oil", "dxy", "dollar", "rupee", "interest rate", "repo rate",
    "nse", "bse", "nifty", "sensex", "fii", "dii", "sebi", "budget",
    "trade deficit", "current account", "forex reserves", "monsoon",
    "earnings", "results", "quarterly", "china", "us market", "europe",
    "sgx nifty", "gift nifty",
]


def score_sentiment(title: str, summary: str = "") -> tuple[str, float]:
    text = (title + " " + summary).lower()
    bull_hits = sum(1 for kw in BULLISH_KEYWORDS if kw in text)
    bear_hits = sum(1 for kw in BEARISH_KEYWORDS if kw in text)
    total = bull_hits + bear_hits
    if total == 0:
        return "NEUTRAL", 0.5
    bull_ratio = bull_hits / total
    bear_ratio = bear_hits / total
    if bull_ratio > 0.6:
        return "BULLISH", round(min(0.5 + bull_ratio * 0.5, 0.95), 3)
    elif bear_ratio > 0.6:
        return "BEARISH", round(min(0.5 + bear_ratio * 0.5, 0.95), 3)
    return "NEUTRAL", 0.5


def is_macro_relevant(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in MACRO_KEYWORDS)


def parse_feed_entry_time(entry: Any) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def fetch_rss_feed(name: str, url: str, cutoff: datetime) -> list[dict]:
    articles = []
    log.info("  Fetching feed: %s", name)

    if HAS_FEEDPARSER:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                log.warning("    Feed parse error for %s: %s", name, feed.bozo_exception)
                return []
            for entry in feed.entries:
                published = parse_feed_entry_time(entry)
                title = getattr(entry, "title", "").strip()
                summary = getattr(entry, "summary", "").strip()
                link = getattr(entry, "link", "").strip()
                if not title:
                    continue
                if published and published < cutoff:
                    continue
                sentiment, confidence = score_sentiment(title, summary)
                articles.append({
                    "source": name,
                    "title": title,
                    "summary": summary[:300] if summary else "",
                    "link": link,
                    "published": published.isoformat() if published else None,
                    "sentiment": sentiment,
                    "confidence": confidence,
                    "macro_relevant": is_macro_relevant(title, summary),
                })
        except Exception as exc:
            log.warning("    Exception fetching %s: %s", name, exc)

    elif HAS_HTTPX:
        try:
            import re
            r = httpx.get(url, timeout=15, follow_redirects=True,
                          headers={"User-Agent": "APEX-TradingSystem/1.0"})
            r.raise_for_status()
            titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>",
                                r.text, re.DOTALL)
            for t1, t2 in titles[2:]:
                title = (t1 or t2).strip()
                if not title:
                    continue
                sentiment, confidence = score_sentiment(title)
                articles.append({
                    "source": name, "title": title, "summary": "",
                    "link": "", "published": None,
                    "sentiment": sentiment, "confidence": confidence,
                    "macro_relevant": is_macro_relevant(title),
                })
        except Exception as exc:
            log.warning("    httpx fallback failed for %s: %s", name, exc)
    else:
        log.error("Neither feedparser nor httpx available. pip install feedparser httpx")

    return articles


def aggregate_snapshot(articles: list[dict], lookback_hours: int) -> dict:
    bullish = [a for a in articles if a["sentiment"] == "BULLISH"]
    bearish = [a for a in articles if a["sentiment"] == "BEARISH"]
    neutral = [a for a in articles if a["sentiment"] == "NEUTRAL"]
    macro = [a for a in articles if a["macro_relevant"]]
    total = len(articles)
    bull_pct = round(len(bullish) / total * 100, 1) if total > 0 else 0.0
    bear_pct = round(len(bearish) / total * 100, 1) if total > 0 else 0.0
    neut_pct = round(len(neutral) / total * 100, 1) if total > 0 else 0.0
    net_score = round((len(bullish) - len(bearish)) / total, 3) if total > 0 else 0.0

    if net_score > 0.2:
        overall_sentiment = "BULLISH"
    elif net_score < -0.2:
        overall_sentiment = "BEARISH"
    else:
        overall_sentiment = "NEUTRAL"

    top = sorted(macro, key=lambda x: x["confidence"], reverse=True)[:10]
    if len(top) < 5:
        top += sorted(articles, key=lambda x: x["confidence"], reverse=True)[:10 - len(top)]

    by_source: dict[str, list] = defaultdict(list)
    for a in articles:
        by_source[a["source"]].append(a)

    feed_breakdown = {}
    raw_counts = {}
    for src, arts in by_source.items():
        b = sum(1 for x in arts if x["sentiment"] == "BULLISH")
        br = sum(1 for x in arts if x["sentiment"] == "BEARISH")
        raw_counts[src] = len(arts)
        feed_breakdown[src] = {"total": len(arts), "bullish": b, "bearish": br, "neutral": len(arts) - b - br}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": lookback_hours,
        "source": "weekend_sweep.py",
        "version": "1.0.0",
        "total_articles": total,
        "macro_relevant_count": len(macro),
        "sentiment_breakdown": {
            "bullish": len(bullish), "bearish": len(bearish), "neutral": len(neutral),
            "bullish_pct": bull_pct, "bearish_pct": bear_pct, "neutral_pct": neut_pct,
        },
        "net_sentiment_score": net_score,
        "overall_sentiment": overall_sentiment,
        "signal_strength": abs(net_score),
        "top_headlines": [
            {"title": a["title"], "source": a["source"], "sentiment": a["sentiment"],
             "confidence": a["confidence"], "published": a["published"], "link": a["link"]}
            for a in top
        ],
        "feed_breakdown": feed_breakdown,
        "raw_article_count_by_source": raw_counts,
    }


def write_to_redis(snapshot: dict) -> None:
    if not HAS_REDIS:
        log.error("redis-py not installed. pip install redis. Skipping Redis write.")
        return
    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    db = int(os.environ.get("REDIS_DB", "0"))
    try:
        r = redis_lib.Redis(host=host, port=port, db=db,
                            socket_connect_timeout=5, socket_timeout=5,
                            decode_responses=True)
        r.ping()
        r.setex("WEEKEND_MACRO_SNAPSHOT", 72 * 3600, json.dumps(snapshot, ensure_ascii=False))
        log.info("Redis write OK: WEEKEND_MACRO_SNAPSHOT (TTL=72h) -> %s:%s db%s", host, port, db)
    except Exception as exc:
        log.error("Redis write FAILED: %s", exc)


def write_to_file(snapshot: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("File write OK: %s", out_path)


def print_summary(snapshot: dict) -> None:
    bd = snapshot["sentiment_breakdown"]
    log.info("=" * 60)
    log.info("WEEKEND MACRO SNAPSHOT SUMMARY")
    log.info("  Timestamp:     %s", snapshot["timestamp"])
    log.info("  Lookback:      %sh", snapshot["lookback_hours"])
    log.info("  Total articles:%d  |  Macro-relevant: %d",
             snapshot["total_articles"], snapshot["macro_relevant_count"])
    log.info("  BULLISH: %d (%.1f%%)  BEARISH: %d (%.1f%%)  NEUTRAL: %d (%.1f%%)",
             bd["bullish"], bd["bullish_pct"], bd["bearish"], bd["bearish_pct"],
             bd["neutral"], bd["neutral_pct"])
    log.info("  Net score:     %+.3f  ->  %s  (strength=%.3f)",
             snapshot["net_sentiment_score"], snapshot["overall_sentiment"],
             snapshot["signal_strength"])
    log.info("  Top headlines:")
    for i, h in enumerate(snapshot["top_headlines"][:5], 1):
        log.info("    %d. [%s %.0f%%] %s", i, h["sentiment"],
                 h["confidence"] * 100, h["title"][:100])
    log.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="APEX Weekend Macro Sweep")
    parser.add_argument("--dry-run", action="store_true", help="Skip Redis write")
    parser.add_argument("--hours", type=int, default=48, help="Look-back window in hours (default: 48)")
    parser.add_argument("--output", type=str, default="data/weekend_snapshot.json")
    parser.add_argument("--feeds", nargs="+", choices=list(RSS_FEEDS.keys()) + ["all"], default=["all"])
    args = parser.parse_args()

    log.info("APEX Weekend Macro Sweep starting...")
    log.info("  Lookback: %dh  |  Dry-run: %s  |  Output: %s", args.hours, args.dry_run, args.output)

    if not HAS_FEEDPARSER and not HAS_HTTPX:
        log.error("No HTTP library available. Install: pip install feedparser httpx")
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    log.info("  Cutoff: %s UTC", cutoff.strftime("%Y-%m-%d %H:%M"))

    feeds_to_use = RSS_FEEDS if "all" in args.feeds else {k: v for k, v in RSS_FEEDS.items() if k in args.feeds}
    log.info("  Feeds: %d selected", len(feeds_to_use))

    all_articles: list[dict] = []
    t0 = time.monotonic()

    for name, url in feeds_to_use.items():
        try:
            arts = fetch_rss_feed(name, url, cutoff)
            log.info("    [%s] -> %d articles in window", name, len(arts))
            all_articles.extend(arts)
        except Exception as exc:
            log.warning("    [%s] failed: %s", name, exc)

    log.info("Fetched %d total articles in %.1fs", len(all_articles), time.monotonic() - t0)

    snapshot = aggregate_snapshot(all_articles, args.hours)
    print_summary(snapshot)

    if args.dry_run:
        log.info("DRY-RUN: Skipping Redis write.")
    else:
        write_to_redis(snapshot)

    write_to_file(snapshot, Path(args.output))
    log.info("Weekend sweep complete. Overall: %s (net=%+.3f)",
             snapshot["overall_sentiment"], snapshot["net_sentiment_score"])


if __name__ == "__main__":
    main()

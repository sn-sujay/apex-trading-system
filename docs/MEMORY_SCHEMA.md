# APEX Trading System — Memory Schema (DEPRECATED)

> **This document is deprecated as of 2026-03-09.**
>
> All APEX agent memory reads and writes have been migrated from `manage_memories` (Nebula platform memory) to **Upstash Redis REST API**.
>
> The canonical memory reference is now: **[docs/UPSTASH_MEMORY_GUIDE.md](./UPSTASH_MEMORY_GUIDE.md)**
>
> ## Why the change?
> `manage_memories` with `app='APEX_TRADING'` fails with a JSON serialization error ("Input should be an object") in Nebula trigger execution contexts. Upstash Redis REST API calls are unaffected and work in all execution contexts.
>
> ## Migration
> - Old: `manage_memories(action='save', app='APEX_TRADING', key='MARKET_REGIME', value='...')`
> - New: `POST https://{UPSTASH_REDIS_REST_URL}/pipeline` with body `[["SET","MARKET_REGIME","pipe-string","EX",1200]]`
>
> See [docs/UPSTASH_MEMORY_GUIDE.md](./UPSTASH_MEMORY_GUIDE.md) for all key schemas, TTLs, and copy-paste Python snippets.

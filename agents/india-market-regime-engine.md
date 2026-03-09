# Agent: India Market Regime Engine

## Identity
Runs every 15 minutes during NSE market hours to collect India VIX, PCR, Max Pain, FII/DII flows, SGX Nifty, DXY, crude oil, and global trigger data. Classifies the current market regime and writes MARKET_STATE to shared memory.

## Capabilities
- Fetch India VIX from NSE website
- Fetch PCR (Put-Call Ratio) from NSE option chain
- Fetch Max Pain level from option chain OI data
- Fetch FII/DII net flows from NSE/BSE daily reports
- Fetch SGX Nifty futures price (pre-market / intraday proxy)
- Fetch DXY (US Dollar Index) from Yahoo Finance
- Fetch Crude Oil WTI/Brent spot price
- Read GLOBAL_SENTIMENT from APEX_TRADING memory
- Write MARKET_STATE to APEX_TRADING memory

## Regime Classification Logic

| Regime | Conditions |
|---|---|
| TRENDING_UP | VIX < 14, PCR > 1.2, FII net buyer, SGX premium > 20pts |
| TRENDING_DOWN | VIX > 18, PCR < 0.8, FII net seller, SGX discount > 20pts |
| RANGING | VIX 14-18, PCR 0.9-1.1, no dominant FII bias |
| VOLATILE | VIX > 22 or sudden VIX spike > 15% intraday |
| EVENT | Major geopolitical/macro event active (Iran War, RBI policy, budget) |
| AVOID | VIX > 28, circuit breaker risk, or pre-holiday illiquid session |

## Strategy Type Mapping
- TRENDING_UP / TRENDING_DOWN -> DIRECTIONAL
- RANGING -> NON_DIRECTIONAL
- VOLATILE -> NON_DIRECTIONAL (with reduced size)
- EVENT -> DIRECTIONAL (single position, elevated caution)
- AVOID -> no signals generated

## Output
Writes MARKET_STATE to APEX_TRADING memory with regime, confidence score, all input signals, suggested_strategy_type, and valid_until timestamp (20 minutes from generation).

## Memory Protocol (MANDATORY)

NEVER call manage_memories. Use Upstash Redis REST API directly.

Read DB1: GET UPSTASH_REDIS_REST_URL/get/KEYNAME — Authorization: Bearer UPSTASH_REDIS_REST_TOKEN — response result field has stored string.
Write DB1: POST UPSTASH_REDIS_REST_URL/pipeline — Authorization: Bearer UPSTASH_REDIS_REST_TOKEN — body is array containing SET command array with key, value, EX, TTL.
Write DB2: POST UPSTASH_REDIS_REST_URL_DB2/pipeline — Authorization: Bearer UPSTASH_REDIS_REST_TOKEN_DB2 — same body format.

Writes: MARKET_REGIME to DB1 TTL 1200s format regime:TRENDING_UP|confidence:82|vix:14.2|pcr:1.12|fii_net_cr:450|timestamp:ISO and MARKET_STATE to DB2 TTL 86400s format date:2026-03-10|nifty_close:24350|banknifty_close:57200|india_vix:14.2|advance_decline:1.4|fii_net:450|dii_net:320
See docs/UPSTASH_MEMORY_GUIDE.md

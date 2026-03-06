# APEX Trading System — Setup Guide

> Complete instructions for deploying the APEX Autonomous Trading System on Nebula's multi-agent platform.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Platform Setup — Nebula](#2-platform-setup--nebula)
3. [Broker & API Connections](#3-broker--api-connections)
4. [Agent Configuration](#4-agent-configuration)
5. [Memory Namespace Initialization](#5-memory-namespace-initialization)
6. [Trigger Activation](#6-trigger-activation)
7. [Paper Trading First Run](#7-paper-trading-first-run)
8. [Going Live — Checklist](#8-going-live--checklist)
9. [Environment Variables Reference](#9-environment-variables-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Accounts Required

| Service | Purpose | Free Tier? |
|---------|---------|------------|
| [Nebula](https://nebula.gg) | Multi-agent orchestration platform | Yes |
| [Dhan](https://dhan.co) | NSE/BSE broker — live order execution | Yes (trading account) |
| [Indian API](https://indianapi.in) | Historical NSE data, option chain | Paid |
| Dhan Market Data API | Live quotes, option chain streaming | Included with Dhan account |

### Optional (for enhanced intelligence)

| Service | Purpose |
|---------|---------|
| StockTwits Whisperer | Social sentiment feed for Indian markets |
| AssemblyAI | Call transcription for earnings intelligence |
| Fireflies.ai | Meeting intelligence integration |

### Knowledge Requirements

- Basic understanding of options trading (calls, puts, spreads)
- Familiarity with NSE instruments: NIFTY, BANKNIFTY, FINNIFTY
- Python not required — system runs entirely on Nebula platform

---

## 2. Platform Setup — Nebula

### Step 1: Create a Nebula Account

1. Go to [nebula.gg](https://nebula.gg) and sign up
2. Verify your email address
3. Complete onboarding — you will land on the main chat interface

### Step 2: Fork / Import This Repository

This repo contains documentation only — the actual agents and triggers live inside Nebula. Use the docs here as the blueprint for recreating the system.

### Step 3: Connect Required Apps

In Nebula, navigate to **Settings > Connected Apps** and connect:

```
1. Dhan (broker)         — OAuth or API key
2. Indian API            — API key
3. Gmail / Email         — For EOD report delivery
```

Each app connection is done once. All agents share the same OAuth tokens automatically.

---

## 3. Broker & API Connections

### Broker API Setup (Dhan)

1. Log in to your Dhan account at https://dhan.co
2. Go to **My Profile** > **API Access**
3. Click **Generate Access Token**
4. Copy your **Client ID** and **Access Token**
5. Add them to your `.env` file:
   ```
   DHAN_CLIENT_ID=your_client_id_here
   DHAN_ACCESS_TOKEN=your_access_token_here
   ```
6. Note: The Dhan access token expires daily. Re-generate it each morning before market open (before 09:00 IST).

### Indian API Setup

1. Register at [indianapi.in](https://indianapi.in)
2. Subscribe to the NSE data plan
3. Copy your API key
4. Add to `.env`:

```
INDIAN_API_KEY=your_api_key_here
```

---

## 4. Agent Configuration

### Core Agents

All agents are created via Nebula's chat interface. Each agent is configured with a system prompt from the `/agents` directory in this repo.

| Agent File | Role | Triggers |
|------------|------|----------|
| `apex-trading-monitor.md` | Master orchestrator | 15-min schedule |
| `nse-option-chain-monitor.md` | Option chain analysis | Price alert |
| `sentiment-intelligence-engine.md` | Sentiment analysis | Daily schedule |
| `live-trade-performance-monitor.md` | P&l tracking | Trade event |
| `apex-self-evolution-engine.md` | Strategy learning | EOD schedule |

### Creating Agents in Nebula

1. In Nebula, click **New Agent**
2. Paste the system prompt from the agent markdown file
3. Configure the agent's app connections (Dhan, IndianAPI, Gmail)
4. Save the agent

---

## 5. Memory Namespace Initialization

Before first run, initialize the APEX memory namespace in Nebula:

```
APEX_TRADING.KILL_SWITCH=FALSE
APEX_TRADING.PAPER_MODE=TRUE
APEX_TRADING.PAPER_LEDGER={}
APEX_TRADING.DAILY_PNL={}
APEX_TRADING.RISK_PER_TRADE=0.02
```

These are set via Nebula's memory interface or through an agent command.

---

## 6. Trigger Activation

### Main Trading Trigger

Create a scheduled trigger in Nebula:

```
Trigger: Scheduled
Cron: */15 9-15 Mon-Fri * * (IST)
Agent: APEX Trading Monitor
```

### Additional Triggers

```
EOD Report:       0 16 Mon-Fri * * (IST)
Self Evolution:   0 20 Mon-Fri * * (IST)
Sentiment Scan:   0 8 Mon-Fri * * (IST)
```

---

## 7. Paper Trading First Run

1. Ensure `APEX_TRADING.PAPER_MODE=TRUE` in memory
2. Start the main trigger at 09:15 IST
3. Monitor the agent logs in Nebula
4. Check paper P&L after market close (15:30 IST)
5. Run for at least 2 weeks before going live

---

## 8. Going Live — Checklist

- [ ] Paper trading profitable for 2+ weeks
- [ ] Risk parameters reviewed and approved
- [ ] Dhan account funded
- [ ] APEX_TRADING.PAPER_MODE set to FALSE
- [ ] Kill switch tested
- [ ] EOD report email verified
- [ ] Position sizing confirmed (max 2% risk per trade)

---

## 9. Environment Variables Reference

| Variable | Required | Description |
|----------|----------|--------------|
| DHAN_CLIENT_ID | Yes | Dhan account ID |
| DHAN_ACCESS_TOKEN | Yes | Dhan API token (daily renewal) |
| INDIAN_API_KEY | Yes | IndianAPI.in key for NSE data |
| PAPER_MODE | No | TRUE for paper trading (default) |
| RISK_PER_TRADE | No | Max risk per trade (default: 0.02) |
| MAX_DAILY_LOSS | No | Daily loss limit (default: 0.05) |
| GMAIL_TO | Yes | EOD report recipient email |

---

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| Dhan authentication error | Regenerate access token in Dhan portal |
| No market data | Check IndianAPI subscription status |
| Orders not executing | Verify PAPER_MODE=FALSE and Dhan limits |
| Agent not triggering | Check Nebula trigger schedule and timezone |
| Memory errors | Re-initialize APEX_TRADING namespace |

---

> **Ready to trade? ** Start with paper trading, validate performance, then go live with confidence.

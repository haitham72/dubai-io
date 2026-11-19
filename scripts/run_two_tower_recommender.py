"""Two-Tower Recommender Engine: 10 Daily Targeted Searches.

Executes targeted search queries via Tavily API matching user context:
- YouTube watch history (Hermes, Honcho, PyTorch, Graph RAG)
- Dev sessions (ide-companio, mirsal, agent tools)
- Career & Hardware memory facts (AI Engineer Dubai, iPhone trade-in)

Saves results to data/sync/two_tower_results.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "sync"
OUTPUT_FILE = DATA_DIR / "two_tower_results.json"
SHARED_POOL_FILE = DATA_DIR / "shared_news_pool.json"

# Load environment
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "apps" / "api" / ".env")

TAVILY_KEY = os.getenv("TVLY_API_KEY", "")


QUERIES = [
    {
        "slot": 1,
        "category": "05-gaming-and-culture",
        "topic": "GTA 6 & Rockstar Pre-Orders",
        "query": "GTA 6 PC release date Rockstar official update 2026",
        "because": "Matched to your visits on rockstargames.com/VI/editions and GTA 6 PC release searches.",
    },
    {
        "slot": 2,
        "category": "05-gaming-and-culture",
        "topic": "PS5 Pro vs Dubizzle Market",
        "query": "PS5 Pro price UAE Dubai vs PS5 disc edition Dubizzle Sharaf DG",
        "because": "Matched to your searches on r/dubaiclassifieds, r/DubaiGaming, and Dubizzle for PS5 consoles.",
    },
    {
        "slot": 3,
        "category": "05-gaming-and-culture",
        "topic": "Steam Indie Simulators",
        "query": "Satisfying indie simulation games like Moon Sweepers That Damn Grass Steam",
        "because": "Matched to your Steam purchases of Moon Sweepers, That Damn Grass, and Find The Needle.",
    },
    {
        "slot": 4,
        "category": "05-gaming-and-culture",
        "topic": "League of Legends ADC Meta",
        "query": "League of Legends Tristana ADC patch notes build meta 2026",
        "because": "Matched to your League of Legends match sessions playing Tristana ADC.",
    },
    {
        "slot": 5,
        "category": "03-tech-and-hardware",
        "topic": "QD-OLED Gaming Displays",
        "query": "Gawfolk 32 inch 4K QD OLED 165Hz gaming monitor reviews UAE Amazon",
        "because": "Matched to your Amazon.ae research on 32-inch 4K QD-OLED 165Hz gaming monitors.",
    },
    {
        "slot": 6,
        "category": "04-learning-and-ideas",
        "topic": "AI Agent Memory & Context",
        "query": "Hermes Agent Honcho memory context architecture update",
        "because": "Matched to your YouTube research on 'What Is Agentic Context? Hermes & Honcho Memory'.",
    },
    {
        "slot": 7,
        "category": "06-design-and-creative",
        "topic": "Generative Motion & Video AI",
        "query": "Higgsfield AI video models vs AffectUI generative motion design",
        "because": "Matched to your frequent workflows in Figma, AffectUI, and Higgsfield AI.",
    },
    {
        "slot": 8,
        "category": "04-learning-and-ideas",
        "topic": "Great Learning ML Academics",
        "query": "Great Learning Olympus machine learning capstone evaluation benchmarks",
        "because": "Matched to your 700+ sessions on olympus.mygreatlearning.com coursework.",
    },
    {
        "slot": 9,
        "category": "02-career-and-craft",
        "topic": "Dubai AI Engineering Careers",
        "query": "site:naukrigulf.com AI Engineer Dubai 2026",
        "because": "Matched to your active career pivot to AI Engineering in Dubai.",
    },
    {
        "slot": 10,
        "category": "05-home-and-money",
        "topic": "Mobile Hardware & Upgrades",
        "query": "Apple trade in value iPhone 16 Pro Max UAE Dubai Mall",
        "because": "Matched to your trade-in calculations for iPhone 16 Pro Max vs iPhone 14 Pro Max in Dubai.",
    },
]


def search_tavily(query: str, key: str) -> list[dict]:
    if not key:
        return []
    try:
        res = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "query": query,
                "search_depth": "basic",
                "max_results": 3,
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=8.0,
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("results") or []
    except Exception as e:
        print(f"  Warning: Tavily query failed for '{query[:30]}...': {e}")
    return []


def main():
    print("=" * 60)
    print("Two-Tower Recommender: 10 Daily Targeted Searches")
    print("=" * 60)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not TAVILY_KEY:
        print("[Error] TVLY_API_KEY is not set in environment or apps/api/.env.")
        sys.exit(1)

    print(f"[API] TVLY_API_KEY detected. Executing 10 targeted searches...")
    results = []

    for item in QUERIES:
        slot = item["slot"]
        q_text = item["query"]
        print(f"\n[Slot {slot}/10] {item['topic']} ({item['category']})")
        print(f"  Query: '{q_text}'")

        hits = search_tavily(q_text, TAVILY_KEY)
        clean_hits = []
        for h in hits:
            clean_hits.append({
                "title": h.get("title", ""),
                "url": h.get("url", ""),
                "snippet": h.get("content", "")[:280],
                "score": h.get("score", 0.0),
            })
        print(f"  Found: {len(clean_hits)} results")

        results.append({
            "slot": slot,
            "category": item["category"],
            "topic": item["topic"],
            "query": q_text,
            "because": item["because"],
            "hits": clean_hits,
        })
        time.sleep(0.3)  # brief pause

    # Save to two_tower_results.json
    OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Done] All 10 targeted searches completed.")
    print(f"[Saved] Output written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

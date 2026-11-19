import os
import subprocess
import json

REF_IMG_8 = r"design\references\quest\interactive\WhatsApp Image 2026-11-19 at 4.31.44 PM (8).jpeg"
REF_IMG_9 = r"design\references\quest\interactive\WhatsApp Image 2026-11-19 at 4.31.44 PM (9).jpeg"

pages = [
    {
        "id": "page1_coding_agent",
        "title": "Fun facts about you: If you were a coding agent",
        "prompt": (
            "High-end mobile UI screenshot in the exact visual style of Quest app. "
            "Clean aesthetic, warm off-white ivory background with soft green-emerald gradient aurora header. "
            "Top left back chevron button. Big bold editorial serif headline: 'Fun facts about you'. "
            "Subhead: 'I had fun imagining who you'd be in your favorite universes.' "
            "Large sub-heading: 'If you were a coding agent'. "
            "A sleek modern card showing Claude Code with a deep emerald wave texture, reading: "
            "'Claude Code: Works from the terminal, reads the whole repo before it speaks, and ships.' "
            "Bottom right circular white floating audio wave microphone button. 9:16 mobile aspect ratio, crisp typography."
        ),
        "ref": REF_IMG_8
    },
    {
        "id": "page2_creative_journey",
        "title": "Looking back at your journey: You make pictures move",
        "prompt": (
            "High-end mobile UI screenshot in the exact visual style of Quest app. "
            "Deep sapphire blue to soft cream vertical gradient header. Top left white chevron back button. "
            "Big bold editorial serif headline: 'Looking back at your journey'. "
            "Subhead: 'I found a few patterns and connected the dots.' "
            "Section text: 'You make pictures move, whatever the tool is. The tool keeps changing. "
            "The urge to make something move hasn't. The next version of you directs with prompts the way you once directed with keyframes.' "
            "Card featuring glowing abstract generative motion waves. "
            "Bottom right circular white floating audio wave microphone button. 9:16 mobile aspect ratio, ultra-premium UI design."
        ),
        "ref": REF_IMG_9
    },
    {
        "id": "page3_proactive_chat",
        "title": "Quest Companion: Proactive Empathy & Autonomous Ping",
        "prompt": (
            "High-end mobile UI screenshot of Quest AI Companion chat page. "
            "Warm ivory background (#F5F3EC), elegant modern chat thread. "
            "Top companion header with glowing golden aurora icon and 'Quest AI Companion · Hot Memory Active'. "
            "Highlighted gold-bordered proactive ping card: '🤖 Autonomous Ping · Empathy & Alignment', saying: "
            "'Hey Haitham, I wanted to follow up and apologize about earlier. I noticed I missed your gaming interests in your morning feed. I updated your permanent memory profile so I don't drop the ball on that again.' "
            "Underneath: small badge '⚡ Ingested into Temporal Memory [trust: T1 | topic: gaming/preferences]'. "
            "Bottom rounded input bar and floating circular audio wave button. 9:16 mobile aspect ratio, elegant iOS aesthetic."
        ),
        "ref": REF_IMG_8
    },
    {
        "id": "page4_knowledge_connector",
        "title": "Dubai-io Connector: Personal Knowledge Vault & Selective Sharing",
        "prompt": (
            "High-end mobile UI screenshot of Dubai-io Personal Knowledge Connector. "
            "Warm off-white background with subtle champagne gold accents. "
            "Headline in elegant serif: 'Dubai-io Knowledge Vault'. "
            "Subhead: 'Control what other AI apps and workspaces can see about you.' "
            "Three interactive permission cards: "
            "1. 'Inner Circle & Family' (Private · 0% Shared), "
            "2. 'Developer Craft & IDE Sessions' (Shared with ide-companio & VS Code · 85%), "
            "3. 'Dubai Civic & Services' (Shared with Dubai-io Recommender · 100%). "
            "Toggle switches, verified trust badges, bottom floating audio button. 9:16 mobile aspect ratio, sleek Apple-grade design."
        ),
        "ref": REF_IMG_8
    }
]

print("Ready to launch Higgsfield Flare generation jobs.")
for p in pages:
    print(f"- {p['id']}: {p['title']}")

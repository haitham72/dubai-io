# Dubai-io — Final Architecture & Phased Implementation Plan

**Product:** Dubai-io (`dubai-io.com`)  
**Positioning:** The Autonomous AI Super-App & Jarvis Living Companion for Dubai  
**Status:** Approved & Finalized  
**Date:** 9 October 2026 · Baseline: Canonical Specification v1.3 (`08-UNIFIED-VISION-AND-FINAL-SPECIFICATION.md`)  
**Audience:** Technical Architect, Full-Stack Engineers, AI Engineers, QA & Jury Presentation Team  

---

## 1. Executive Summary & Architecture Strategy

Dubai-io concantenates four core pillars into a single stateful AI companion:
1. **Dubai Now Civic Intelligence:** Vehicle lifecycle (renewal, inspection locator, petrol delivery, recovery truck dispatch), utilities (DEWA, Salik), official dispute recovery.
2. **WeChat Merchant Ecosystem:** Lightweight private merchant onboarding (photo/menu to structured catalog), interactive card streaming, quote/booking/acknowledgement lifecycle.
3. **Jarvis Context Engine:** Proactive micro-triggers driven by $f(\text{WHO}, \text{WHERE}, \text{WHEN}, \text{WHAT}, \text{HISTORY})$ — anticipating parking spot memory, airport checklists, passport prep, and trip logistics *before* the user prompts.
4. **Adaptive Dual-Mode:** Automatic context switching between **Visitor Companion** (DXB arrival, cultural etiquette, tours, VAT refunds) and **Resident Companion** (household, vehicles, bills, neighborhood services) within a single continuous conversation.

The system is implemented as a **Modular Monolith** with a decoupled proactive event dispatcher, an audited LangGraph agent core, and a mobile-first streaming frontend.

---

## 2. System Architecture & Tech Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FRONTEND: Next.js 15 (React 19) PWA                   │
│  • Mobile-first luxury Dubai aesthetic (Tailored dark/light themes, HSL)     │
│  • Server-Sent Events (SSE) streaming chat & proactive notification feed     │
│  • Dynamic Action Card renderer (Quote, Approval, Checklist, Parking OCR)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ HTTP / SSE
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKEND: FastAPI Modular Monolith (Python 3.12)           │
│                                                                             │
│  ┌────────────────────────┐  ┌───────────────────────────────────────────┐  │
│  │   Auth & RBAC Service  │  │         Proactive Context Engine          │  │
│  │ (User / Merchant / Ops)│  │ • Geofence & Sensor Signal Evaluator     │  │
│  └────────────────────────┘  │ • Scheduled Outbox Cron & Task Dispatcher │  │
│                              │ • User Context Manager (WHO/WHERE/WHEN)   │  │
│  ┌────────────────────────┐  └─────────────────────┬─────────────────────┘  │
│  │  Domain State Engine   │                        │                        │
│  │(Quotes, Bookings, Logs)│                        ▼                        │
│  └───────────┬────────────┘  ┌───────────────────────────────────────────┐  │
│              │               │        LangGraph Orchestrator Agent       │  │
│              │               │ • Intent Router (Civic vs. Commerce)      │  │
│              │               │ • Sandboxed Tool Execution Pipeline       │  │
│              │               │ • Action Approval & Human-in-the-Loop     │  │
│              │               └─────────────────────┬─────────────────────┘  │
└──────────────┼─────────────────────────────────────┼────────────────────────┘
               │                                     │
               ▼                                     ▼
┌─────────────────────────────────┐   ┌──────────────────────────────────────┐
│       EXTERNAL / ADAPTER LAYER  │   │          PERSISTENCE LAYER           │
│                                 │   │                                      │
│ • Mock Dubai Gov API Adapter    │   │ • PostgreSQL 16 (Relational state)   │
│   (Vehicles, Mulkiya, Salik)    │   │ • pgvector (Official Civic RAG DB)   │
│ • Merchant Web Inbox & Portal   │   │ • Outbox Table (Durable event queue) │
│ • S3-Compatible Asset Storage   │   │ • LangGraph State Checkpoint Store   │
└─────────────────────────────────┘   └──────────────────────────────────────┘
```

| Area | Production Stack | Implementation Boundary |
|---|---|---|
| **Frontend** | Next.js 15 (React 19), Vanilla CSS Tokens, Lucide Icons | Mobile-first PWA, reactive SSE stream, dynamic card slate |
| **API Gateway** | Python FastAPI, Pydantic v2 schemas | Modular monolith, clean domain routers, strict validation |
| **Agent Core** | LangGraph, ChatAnthropic / ChatOpenAI / ChatGoogle | Explicit state graph, checkpoint persistence, bounded tool calls |
| **Database** | PostgreSQL 16 with `pgvector` | Users, requests, quotes, chats, vehicle records, vector embeddings |
| **Event Outbox** | PostgreSQL Outbox Pattern + Async Worker | Reliable event dispatch, proactive cron triggers, zero lost events |
| **RAG Knowledge** | Chunked Official Dubai Legislation & Guides | Grounded consumer protection (Law No. 5 of 2020), tenancy laws |
| **Gov Simulation** | Deterministic Mock Dubai Gov API Adapter | Vehicles, Mulkiya status, Salik balance, DEWA consumption |
| **Merchant Portal** | Next.js / Tailwind Minimal Operator View | Real-time quote inbox with one-tap accept/reject |

---

## 3. Core Data Contracts & Card Schemas

All UI elements stream as typed, discriminated union action cards (`ActionCard`):

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Union

class CardAction(BaseModel):
    action_id: str
    label: str
    requires_approval: bool = True
    payload: dict

class ServiceComparisonCard(BaseModel):
    type: Literal["service_comparison"] = "service_comparison"
    title: str
    providers: List[dict]  # id, name, price_aed, rating, availability_slot
    actions: List[CardAction]

class VehicleStatusCard(BaseModel):
    type: Literal["vehicle_status"] = "vehicle_status"
    plate_number: str
    mulkiya_expiry_days: int
    inspection_required: bool
    nearest_test_center: str
    actions: List[CardAction]

class ParkingRecallCard(BaseModel):
    type: Literal["parking_recall"] = "parking_recall"
    venue: str
    floor_level: str
    pillar_number: str
    timestamp: str
    photo_url: Optional[str] = None

class ActionApprovalCard(BaseModel):
    type: Literal["action_approval"] = "action_approval"
    summary: str
    cost_aed: Optional[float] = None
    recipient: str
    actions: List[CardAction]

ActionCardUnion = Union[
    ServiceComparisonCard,
    VehicleStatusCard,
    ParkingRecallCard,
    ActionApprovalCard
]
```

---

## 4. Phased Implementation Roadmap & Verification Gates

```
Phase 0: Architecture Contracts & Registry Schemas (Days 1–3)
Phase 1: Persistent PWA Shell & Proactive Event Stream (Days 4–9)
Phase 2: Dubai Now Layer — Vehicles, Salik & Consumer RAG (Days 10–14)
Phase 3: WeChat Layer — Merchant Onboarding & Web Inbox (Days 15–19)
Phase 4: Jarvis Context Engine — Parking, Geofencing, Reminders (Days 20–24)
Phase 5: Contest Demo Polish, Evals & Live Rehearsal (Days 25–28)
```

### Phase 0: Architecture Contracts & Foundations (Days 1–3)
- **Deliverables:**
  - Initialize modular monorepo structure (`backend/`, `frontend/`, `docs/`, `tests/`).
  - Define all Pydantic v2 models and TypeScript interfaces for messages and dynamic cards.
  - Setup PostgreSQL 16 schema with Alembic migrations and `pgvector` extension.
  - Build Mock Dubai Gov API client (vehicles, Salik, DEWA records).
- **Exit Verification Gate:**
  - Automated tests validate card serializations. Zero schema ambiguity between backend and frontend.

### Phase 1: Persistent PWA Shell & Streaming Core (Days 4–9)
- **Deliverables:**
  - Next.js 15 PWA mobile shell with bespoke Dubai Luxury styling tokens.
  - FastAPI SSE streaming endpoint (`/api/chat/stream`) with token streaming and card injection.
  - Multi-tenant session manager with scoped user roles and LangGraph Postgres checkpointer.
- **Exit Verification Gate:**
  - Browser reload completely restores active chat, previous cards, and pending approval states.

### Phase 2: Dubai Now Layer — Civic, Vehicles & Consumer Law (Days 10–14)
- **Deliverables:**
  - Vehicle lifecycle workflow: Mulkiya expiry detection, inspection test center locator, petrol delivery hook.
  - Salik and DEWA balance status queries and top-up approval flow.
  - Official Dubai Consumer Protection (Law No. 5 of 2020) RAG pipeline with cited legal recoveries.
- **Exit Verification Gate:**
  - 100% of legal/consumer queries cite official source articles with zero hallucinations; vehicle workflows correctly bind to registered test centers.

### Phase 3: WeChat Layer — Merchant Onboarding & Operator Inbox (Days 15–19)
- **Deliverables:**
  - Service Registry supporting L1–L5 merchant capability models.
  - Merchant catalog parser (photo/text menu -> structured items).
  - Lightweight Merchant Web Inbox (`/merchant/inbox`) with live Webhook/SSE notification.
  - Split-screen quote-request -> merchant approval -> customer confirmation loop.
- **Exit Verification Gate:**
  - Merchant operator accepts quote request in portal; customer conversation updates with live confirmation card in < 1 second.

### Phase 4: Jarvis Context Engine — Proactive Micro-Moments (Days 20–24)
- **Deliverables:**
  - Context engine tracking $f(\text{WHO}, \text{WHERE}, \text{WHEN}, \text{WHAT}, \text{HISTORY})$.
  - Geofence trigger simulator (entering Dubai Mall -> parking spot reminder; approaching DXB -> passport checklist).
  - Parking photo/pillar memory store with visual OCR capture.
  - Outbox-backed scheduled reminder cron dispatcher with quiet-hours enforcement.
- **Exit Verification Gate:**
  - Simulated geofence or time event injects a proactive, unprompted message card directly into the chat timeline without duplicate delivery.

### Phase 5: Contest Demo Polish, Evals & Rehearsal (Days 25–28)
- **Deliverables:**
  - Rehearsed 4-minute live stage demo covering all four pillars in a single continuous conversation.
  - Split-screen live view: User Mobile Screen on left, Merchant Inbox on right, Jarvis Context Telemetry in background.
  - Offline fallback harness with pre-cached states for rock-solid presentation resilience.
- **Exit Verification Gate:**
  - Complete live demo runs seamlessly end-to-end within 4 minutes on stage.

---

## 5. Repository Structure

```text
dubai-io/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes (chat, merchants, webhooks, civic)
│   │   ├── core/            # Config, security, database session
│   │   ├── domain/          # Entities: users, requests, quotes, vehicles
│   │   ├── agents/          # LangGraph state graph, intent router, tools
│   │   ├── context/         # Jarvis Context Engine (WHO/WHERE/WHEN/HISTORY)
│   │   ├── rag/             # Official Dubai Law & Civic vector store
│   │   ├── adapters/        # Mock Gov API, Cafu/Petrol, Tasjeel, S3
│   │   └── schemas/         # Pydantic card contracts and events
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router (chat, merchant portal, admin)
│   │   ├── components/      # Dynamic cards, chat stream, proactive banners
│   │   ├── styles/          # Vanilla CSS tokens, Dubai luxury aesthetics
│   │   └── lib/             # API client, SSE stream reader, offline cache
│   └── package.json
├── docs/                    # Authoritative handoff documents (01–08)
├── docker-compose.yml
└── README.md
```

---

## 6. Final Sign-off

The planning phase is now officially **finalized and locked**.  
All design, architecture, scenario, and contest parameters are consolidated in the handoff suite (`docs/01-PRODUCT-VISION.md` through `docs/08-UNIFIED-VISION-AND-FINAL-SPECIFICATION.md`).

When the instruction to build is given, execution immediately commences at **Phase 0**.

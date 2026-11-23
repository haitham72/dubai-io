// Seed Mirsal tasks shown in Mirsal Updates on load. Owned by LLM 1 (may enrich; keep the export name).
import type { MirsalTask } from "../types";
import { img } from "../ui";

const ago = (min: number) => Date.now() - min * 60_000;

export const seedTasks: MirsalTask[] = [
  {
    id: "seed-esign", type: "esign", title: "Signature needed", subtitle: "e& yearly contract renewal · AED 300/month",
    status: "completed", startedAt: ago(3), completedAt: ago(2), unread: true,
    result: { type: "esign", doc: "eand-renewal" },
  },
  {
    id: "seed-image", type: "image", title: "Image ready", subtitle: "Your social post visual is ready",
    status: "completed", startedAt: ago(7), completedAt: ago(5), unread: true,
    result: { type: "image", prompt: "Dubai beach at golden hour", imageUrl: img("photo-1512453979798-5ea266f8880c", 1400) },
  },
  {
    id: "seed-flight", type: "flight", title: "Flight found", subtitle: "3 flights to Dubai from AED 1,240",
    status: "completed", startedAt: ago(14), completedAt: ago(12), unread: true,
    result: {
      type: "flight",
      query: { from: "JED", to: "DXB", depart: "2026-12-12", passengers: 1, cabin: "economy" },
      flights: [
        { id: "f1", airline: "Saudia", flightNo: "SV 542", date: "Sat, 12 Dec", fromCode: "JED", fromTime: "10:30 AM", toCode: "DXB", toTime: "12:50 PM", duration: "2h 20m", stops: 0, price: 1240, currency: "AED", cabin: "Economy", bestPrice: true },
        { id: "f2", airline: "Emirates", flightNo: "EK 803", date: "Sat, 12 Dec", fromCode: "JED", fromTime: "3:15 PM", toCode: "DXB", toTime: "5:40 PM", duration: "2h 25m", stops: 0, price: 1580, currency: "AED", cabin: "Economy" },
        { id: "f3", airline: "Qatar Airways", flightNo: "QR 1012", date: "Sat, 12 Dec", fromCode: "JED", fromTime: "8:10 AM", toCode: "DXB", toTime: "1:20 PM", duration: "5h 10m", stops: 1, price: 1860, currency: "AED", cabin: "Economy" },
      ],
    },
  },
  {
    id: "seed-research", type: "research", title: "Research ready", subtitle: "5 key insights on market trends",
    status: "completed", startedAt: ago(40), completedAt: ago(36), unread: true,
    result: {
      type: "research",
      items: [
        {
          id: "r1", title: "UAE AI market trends 2026", time: "12:36 PM",
          summary: "5 key insights on the UAE AI market for 2026 based on recent reports and industry analysis.",
          findings: [
            "Strong government investment in sovereign AI and cloud infrastructure.",
            "Growing demand for Arabic NLP and multilingual solutions.",
            "Increased adoption across public sector and smart city initiatives.",
            "Rising opportunities in AI engineering, MLOps, and RAG systems.",
            "Competitive salary range for AI engineers in UAE (AED 30k – 50k).",
          ],
        },
        {
          id: "r2", title: "RAG vs fine-tuning comparison", time: "10:12 AM",
          summary: "A practical comparison for a multilingual support assistant. Illustrative demo research.",
          findings: ["Use retrieval for frequently changing policies and source-backed answers.", "Fine-tuning can improve tone and structured output consistency.", "Evaluate Arabic and English examples separately before choosing an approach.", "Start with a small retrieval baseline and measure answer quality and latency."],
        },
        {
          id: "r3", title: "Instagram comment moderation", time: "Yesterday",
          summary: "A proposed workflow for reviewing brand comments without losing useful feedback.",
          findings: ["Separate spam, abuse, customer questions and ordinary criticism.", "Queue ambiguous Arabic dialect expressions for a human reviewer.", "Keep a short audit trail of moderation decisions.", "Measure false positives using a sample of approved comments."],
        },
        {
          id: "r4", title: "Local LLM deployment options", time: "Oct 2",
          summary: "An illustrative checklist for running an internal assistant on local hardware.",
          findings: ["Estimate memory needs using model size and expected context length.", "Benchmark quantized models on representative internal questions.", "Keep sensitive documents in a controlled retrieval index.", "Plan monitoring, model updates and a fallback for overloaded hardware."],
        },
        {
          id: "r5", title: "UAE AI job market analysis", time: "Oct 1",
          summary: "Demo notes for a job search focused on applied AI roles in Dubai and Abu Dhabi.",
          findings: ["Compare engineering roles with research and consulting positions.", "Show production examples of retrieval, evaluation and observability in a portfolio.", "Review language requirements and onsite expectations for each employer.", "Use a consistent checklist for compensation, benefits and growth opportunities."],
        },
      ],
    },
  },
  {
    id: "seed-email", type: "email", title: "Email draft ready", subtitle: "Your follow-up draft is prepared",
    status: "completed", startedAt: ago(62), completedAt: ago(60), unread: true,
    result: {
      type: "email",
      drafts: [
        {
          id: "e1", to: "Shweta – IDC Technologies", time: "11:20 AM",
          subject: "Re: QA Automation (Arabic Speaker) – Abu Dhabi",
          body: "Hi Shweta,\n\nThank you for reaching out regarding the QA Automation (Arabic Speaker) opportunity at IDC Technologies. I'm very interested in this role.\n\nI'd be happy to share my CV and discuss further details at your convenience.\n\nBest regards,\nHaitham",
        },
        {
          id: "e2", to: "Noel — NeoHealth", time: "10:42 AM", subject: "Re: Interview availability",
          body: "Hi Noel,\n\nThank you for the invitation. I can join an interview on Tuesday at 10 AM or Wednesday at 2 PM Gulf Standard Time.\n\nPlease let me know which slot works best and whether there is anything I should prepare.\n\nBest regards,\nHaitham",
        },
        {
          id: "e3", to: "Hadeel — Content team", time: "9:18 AM", subject: "Re: Content collaboration",
          body: "Hi Hadeel,\n\nI enjoyed our conversation about the Dubai campaign. I've prepared the initial visual direction and a short outline for the launch posts.\n\nCould we review them together on Thursday? I would appreciate your feedback before we finalize the brief.\n\nBest regards,\nHaitham",
        },
      ],
    },
  },
];

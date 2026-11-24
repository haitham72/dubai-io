"""P1A corpus renderer: truth ledger -> WhatsApp / Gmail / notes + ingest order.

Reads gold/ledger.json (renders authored there), interleaves seeded noise, writes:
  gold/sources/whatsapp_best.txt, whatsapp_work.txt, whatsapp_family.txt
  gold/sources/gmail.jsonl, gold/sources/notes.md
  gold/ingest_order.json
and backfills ledger fact evidence[] with record IDs (rewrites ledger.json).

Deterministic: RNG seed 42. Record IDs:
  WhatsApp: {wab|wag|waf}-NNNN (NNNN = 1-based line number in that file)
  Gmail:    gNNN (chronological)
  Notes:    nNNN (chronological)
"""
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent
LEDGER = GOLD / "ledger.json"
SOURCES = GOLD / "sources"
RNG = random.Random(42)

START = date(2026, 10, 20)
DAYS = [(START + timedelta(days=i)).isoformat() for i in range(31)]  # 10-20 .. 11-19 inclusive

# Late-arriving older facts: old_fact -> newer_fact (old evidence ingests AFTER new).
LATE = {"f005": "f004", "f029": "f028", "f041": "f040", "f050": "f034"}

CHATS = {
    "wab": {"file": "whatsapp_best.txt", "title": "Omar Farouk (best friend, 1:1)",
            "members": ["Karim Haddad", "Omar Farouk"]},
    "wag": {"file": "whatsapp_work.txt", "title": "QamarTech Atlas Squad (work group)",
            "members": ["Karim Haddad", "Salma Nasser", "Youssef Adel", "Omar El-Sayed",
                        "Priya Raman", "Daniel Okoro", "Sherif Kamal"]},
    "waf": {"file": "whatsapp_family.txt", "title": "Haddad Family (family + building neighbours)",
            "members": ["Karim Haddad", "Layla Haddad", "Tarek Haddad", "Mariam Haddad",
                        "Salma Haddad", "Abu Khalid", "Khalid Al-Farsi"]},
}
# Sherif left QamarTech Oct 24: no noise from him after that (planted f032 stays).
LEFT_AFTER = {"Sherif Kamal": "2026-10-24"}

KARIM = "Karim Haddad"

# ---------------- noise templates (generic; no ledger-grade facts, no real names) ----------------
WAB_NOISE = [
    (0, "Omar Farouk", "Salam Kimo, match tonight?"),
    (1, "Karim Haddad", "Can't, long run tomorrow 😅"),
    (0, "Omar Farouk", "ok"),
    (1, "Karim Haddad", "Did you see the game last night??"),
    (0, "Omar Farouk", "That last goal was insane 🔥"),
    (1, "Karim Haddad", "Karak tonight?"),
    (0, "Omar Farouk", "Can't, Rana has plans for us 😅"),
    (1, "Karim Haddad", "😂😂"),
    (0, "Omar Farouk", "<Media omitted>"),
    (1, "Karim Haddad", "😂😂😂"),
    (0, "Omar Farouk", "Jummah mubarakah bro"),
    (1, "Karim Haddad", "Jummah mubarakah 🙏"),
    (0, "Omar Farouk", "3amel eh ya Kimo"),
    (1, "Karim Haddad", "Mashy el hal, enta?"),
    (0, "Omar Farouk", "El hamdulelah"),
    (1, "Karim Haddad", "Check this out <Media omitted>"),
    (0, "Omar Farouk", "Hahahaha classic"),
    (1, "Karim Haddad", "Gym?"),
    (0, "Omar Farouk", "Tomorrow isa"),
    (1, "Karim Haddad", "👍"),
    (0, "Omar Farouk", "Did you pay the DEWA bill? Reminds me I forgot mine"),
    (1, "Karim Haddad", "Auto-pay bro, join 2026 😎"),
    (0, "Omar Farouk", "Ezay el sho3'l?"),
    (1, "Karim Haddad", "Mad3'oot bs tamam"),
]

WAG_NOISE = [
    (0, "Salma Nasser", "Standup in 10, thread your updates please"),
    (1, "Youssef Adel", "Staging deploy done, smoke tests green"),
    (2, "Priya Raman", "Eval job finished, numbers look sane"),
    (3, "Daniel Okoro", "Reviewing the mobile PRs after lunch"),
    (4, "Karim Haddad", "On it"),
    (0, "Salma Nasser", "Reminder: log your hours before Thursday"),
    (1, "Omar El-Sayed", "Billing sandbox is down again?"),
    (2, "Youssef Adel", "Restarted it, try now"),
    (3, "Omar El-Sayed", "Works 👍"),
    (4, "Priya Raman", "GPU queue is long today, training delayed a bit"),
    (0, "Salma Nasser", "Client moved the sync to 2pm"),
    (1, "Karim Haddad", "Noted"),
    (2, "Daniel Okoro", "Anyone else seeing flaky push notifications on staging?"),
    (3, "Youssef Adel", "Known issue, fix in the next build"),
    (4, "Priya Raman", "Dataset refresh done"),
    (0, "Salma Nasser", "Great sprint team, velocity is up 🙌"),
    (1, "Karim Haddad", "Docs updated in the drive"),
    (2, "Omar El-Sayed", "ok"),
    (3, "Daniel Okoro", "Taking lunch, back in 30"),
    (4, "Youssef Adel", "VPN is slow for anyone else?"),
]

WAF_NOISE = [
    (0, "Layla Haddad", "صباح الخير يا ولاد ❤️"),
    (1, "Karim Haddad", "صباح النور يا ماما"),
    (2, "Mariam Haddad", "صباح الخير"),
    (3, "Tarek Haddad", "Someone call the AC guy, the Cairo flat is a sauna"),
    (4, "Layla Haddad", "Already called him Baba 😄"),
    (0, "Mariam Haddad", "يوسف... I mean Karim, did you eat?"),
    (1, "Karim Haddad", "Yes mama-in-training 😂"),
    (2, "Salma Haddad", "Hey cousins! How is everyone?"),
    (3, "Khalid Al-Farsi", "Salam all, Thursday football still on?"),
    (4, "Karim Haddad", "Yes 8pm 👍"),
    (0, "Abu Khalid", "Salam neighbours, water will be cut Sunday 9-12 for maintenance"),
    (1, "Tarek Haddad", "مبارك يا كريم على الشغل، ربنا يوفقك"),
    (2, "Karim Haddad", "الله يبارك فيك يا بابا 🙏"),
    (3, "Layla Haddad", "<Media omitted>"),
    (4, "Mariam Haddad", "Mashallah 😍"),
    (0, "Salma Haddad", "<Media omitted>"),
    (1, "Layla Haddad", "كلوا كويس يا ولاد"),
    (2, "Khalid Al-Farsi", "GGs last match 🔥"),
    (3, "Abu Khalid", "Jummah mubarakah all"),
    (4, "Tarek Haddad", "The radio works again 📻"),
]

GMAIL_NOISE_SENDERS = [
    ("noon", "deals@noon.example", "promo"), ("talabat", "offers@talabat.example", "promo"),
    ("amazon.ae", "deals@amazon-ae.example", "promo"), ("Namshi", "style@namshi.example", "promo"),
    ("Sharaf DG", "offers@sharafdg.example", "promo"), ("Atlantis", "stay@atlantis.example", "promo"),
    ("Careem", "rides@careem.example", "promo"), ("Du", "myaccount@du.example", "bill"),
    ("Noor Energy", "bills@noorenergy.example", "bill"),
    ("SkillUp Newsletter", "digest@skillup.example", "newsletter"),
    ("AI Weekly", "news@aiweekly.example", "newsletter"),
    ("MarathonDXB", "run@marathondxb.example", "newsletter"),
    ("DarProperty Alerts", "alerts@darproperty.example", "jobalert"),
    ("Tawzef Jobs", "alerts@tawzef.example", "jobalert"),
    ("Bayt", "alerts@bayt.example", "jobalert"),
    ("QamarTech IT", "it@qamartech.example", "otp"),
    ("SkillForge", "verify@skillforge.example", "otp"),
    ("PeakForm", "noreply@peakform.example", "receipt"),
    ("Aramex", "track@aramex.example", "receipt"),
]
GMAIL_NOISE_SUBJ = {
    "promo": ["Flash sale: up to 70% off this weekend", "Your exclusive coupon expires tonight",
              "New arrivals you may like", "Weekend deals inside 🌙", "Price drop on your wishlist"],
    "bill": ["Your monthly bill is ready", "Payment reminder", "Receipt for your payment"],
    "newsletter": ["This week in AI", "5 stories you missed", "Sunday digest"],
    "jobalert": ["New roles matching Senior AI Engineer", "3 new jobs in DIFC", "Your weekly job picks"],
    "otp": ["Your verification code", "Login code", "Security code"],
    "receipt": ["Your order has shipped", "Delivery update", "Payment receipt"],
}
GMAIL_NOISE_BODY = {
    "promo": "Hi Karim, limited-time offers selected for you. Shop before midnight. Unsubscribe anytime.",
    "bill": "Dear customer, your latest statement is available in the app. Thank you.",
    "newsletter": "Top stories this week. Read the full digest in your browser.",
    "jobalert": "Based on your profile, these roles may interest you. Update preferences anytime.",
    "otp": "Your code is 493820. It expires in 10 minutes. Never share it.",
    "receipt": "Your shipment is on its way. Track it in the app.",
}
# Neutral substantive mail: real personal admin, no new durable ledger facts.
GMAIL_NEUTRAL = [
    ("QamarTech HR <hr@qamartech.example>", "Payslip October", "Your October payslip is available on the HR portal."),
    ("QamarTech HR <hr@qamartech.example>", "Public holiday announced", "Reminder: Thursday is a public holiday, office closed."),
    ("Noor Energy <bills@noorenergy.example>", "Bill paid - thank you", "We received AED 312 for account ending 4410. Thank you."),
    ("Aramex <track@aramex.example>", "Delivered", "Shipment from Cairo delivered and signed. Track ref CF88231."),
    ("PeakForm <noreply@peakform.example>", "Class booked: Spin Thursday", "You booked Spin, Thursday 7pm with Coach Dana."),
    ("Barsha Smile Clinic <hello@barshasmile.example>", "Thanks for visiting", "Thanks for visiting us. Rate your experience here."),
    ("SkillForge <hello@skillforge.example>", "New labs available", "Two new practice labs were added to your library."),
    ("DarProperty <alerts@darproperty.example>", "Saved search update", "2 new listings match your saved search in Barsha."),
    ("Tawzef <alerts@tawzef.example>", "Profile views", "3 employers viewed your profile this week."),
    ("NexaPay <events@nexapay.example>", "Tech talk invite", "Join our public tech talk on realtime ML, Dec 10."),
    ("Dubai Marathon <run@marathondxb.example>", "Race pack collection", "Collect your race pack Jan 2-4 at the expo hall."),
    ("AutoHub Deira <service@autohub-deira.example>", "Service reminder", "Your booked inspection slot is confirmed. Arrive 10 min early."),
    ("StreamFlix <noreply@streamflix.example>", "We miss you", "Come back for 50% off 3 months. Offer ends soon."),
    ("FitZone <hello@fitzone.example>", "Membership paused", "Your membership pause is confirmed. See you back soon!"),
]

NOTES_NOISE = [
    "Water the balcony plants. They are judging me.",
    "Call Etisalat... I mean the telecom, about the fibre upgrade.",
    "Idea: Raseef widget for split balance on home screen.",
]

def wa_stamp(day: str) -> str:
    h = RNG.randint(8, 23)
    m = RNG.randint(0, 59)
    s = RNG.randint(0, 59)
    y, mo, d = day.split("-")
    ampm = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{int(mo)}/{int(d)}/{y}, {h12}:{m:02d}:{s:02d} {ampm}", f"{day}T{h:02d}:{m:02d}:{s:02d}"


def gmail_stamp(day: str) -> str:
    return f"{day}T{RNG.randint(7, 22):02d}:{RNG.randint(0, 59):02d}:{RNG.randint(0, 59):02d}"


def thread_root(subject: str) -> str:
    s = subject.lower()
    s = re.sub(r"^(re|fw|fwd)\s*:\s*", "", s)
    return "_".join(re.sub(r"[^a-z0-9]+", " ", s).split()[:4]) or "misc"


def main() -> None:
    SOURCES.mkdir(parents=True, exist_ok=True)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    evidence: dict[str, list[str]] = {f["id"]: [] for f in ledger["facts"]}
    order_pool: list[tuple[str, str]] = []  # (ts, record_id)

    # ---- WhatsApp ----
    wa_templates = {"wab": WAB_NOISE, "wag": WAG_NOISE, "waf": WAF_NOISE}
    for chat, cfg in CHATS.items():
        planted = []
        for f in ledger["facts"]:
            for r in f["renders"]:
                if r["src"] == chat:
                    planted.append((r["day"], r["by"], r["text"].replace("\n", " "), f["id"]))
        by_day: dict[str, list] = {d: [] for d in DAYS}
        for day, by, text, fid in planted:
            by_day[day].append(("plant", by, text, fid))
        lines: list[tuple[str, str, str, str | None]] = []  # ts, by, text, fid
        tmpl = wa_templates[chat]
        ti = 0
        for day in DAYS:
            msgs = list(by_day[day])
            need = max(2, 10 - len(msgs))
            for _ in range(need):
                _, by, text = tmpl[ti % len(tmpl)]
                ti += 1
                if by in LEFT_AFTER and day > LEFT_AFTER[by]:
                    by, text = KARIM, "ok"
                msgs.append(("noise", by, text, None))
            RNG.shuffle(msgs)
            for kind, by, text, fid in msgs:
                stamp, ts = wa_stamp(day)
                lines.append((ts, f"[{stamp}] {by}: {text}", fid, kind))
        lines.sort(key=lambda x: x[0])
        out = []
        for i, (ts, line, fid, kind) in enumerate(lines, 1):
            rid = f"{chat}-{i:04d}"
            out.append(line)
            order_pool.append((ts, rid))
            if fid:
                evidence[fid].append(rid)
        (SOURCES / cfg["file"]).write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"{cfg['file']}: {len(out)} msgs ({sum(1 for _, _, f, _ in lines if f)} planted)")

    # ---- Gmail ----
    mails: list[dict] = []
    for f in ledger["facts"]:
        for r in f["renders"]:
            if r["src"] == "gmail":
                mails.append({"fact_id": f["id"], "day": r["day"], "from": r["from"],
                              "subject": r["subject"], "body": r["text"]})
    neutral_days = [d for d in DAYS for _ in range(2)][:42]
    RNG.shuffle(neutral_days)
    for i in range(42):
        frm, subj, body = GMAIL_NEUTRAL[i % len(GMAIL_NEUTRAL)]
        mails.append({"fact_id": None, "day": neutral_days[i], "from": frm, "subject": subj, "body": body})
    for i in range(128):
        sender, addr, kind = GMAIL_NOISE_SENDERS[i % len(GMAIL_NOISE_SENDERS)]
        subj = RNG.choice(GMAIL_NOISE_SUBJ[kind])
        mails.append({"fact_id": None, "day": RNG.choice(DAYS), "from": f"{sender} <{addr}>",
                      "subject": subj, "body": GMAIL_NOISE_BODY[kind]})
    for m in mails:
        m["ts"] = gmail_stamp(m["day"])
    mails.sort(key=lambda m: m["ts"])
    threads: dict[str, str] = {}
    tn = 0
    glines = []
    for i, m in enumerate(mails, 1):
        rid = f"g{i:03d}"
        key = m["from"].split("<")[-1].rstrip(">") + "|" + thread_root(m["subject"])
        if key not in threads:
            tn += 1
            threads[key] = f"th-{tn:03d}"
        glines.append(json.dumps({"id": rid, "thread_id": threads[key], "ts": m["ts"],
                                  "from": m["from"], "subject": m["subject"], "body": m["body"]},
                                 ensure_ascii=False))
        order_pool.append((m["ts"], rid))
        if m["fact_id"]:
            evidence[m["fact_id"]].append(rid)
    (SOURCES / "gmail.jsonl").write_text("\n".join(glines) + "\n", encoding="utf-8")
    print(f"gmail.jsonl: {len(glines)} mails ({sum(1 for m in mails if m['fact_id'])} planted, 42 neutral, 128 noise)")

    # ---- Notes ----
    notes: list[tuple[str, str, str | None]] = []
    for f in ledger["facts"]:
        for r in f["renders"]:
            if r["src"] == "notes":
                notes.append((r["day"], r["text"].replace("\n", " "), f["id"]))
    for i, t in enumerate(NOTES_NOISE):
        notes.append((DAYS[5 + i * 9], t, None))
    notes.sort(key=lambda x: x[0])
    nlines = []
    for i, (day, text, fid) in enumerate(notes, 1):
        rid = f"n{i:03d}"
        nlines.append(f"[{rid}] {day} | {text}")
        order_pool.append((f"{day}T12:00:00", rid))
        if fid:
            evidence[fid].append(rid)
    (SOURCES / "notes.md").write_text("\n".join(nlines) + "\n", encoding="utf-8")
    print(f"notes.md: {len(nlines)} notes ({sum(1 for _, _, f in notes if f)} planted)")

    # ---- ingest order: chronological, late arrivals last ----
    order_pool.sort(key=lambda x: (x[0], x[1]))
    late_ids: dict[str, dict] = {}
    for old_fid, new_fid in LATE.items():
        for rid in evidence[old_fid]:
            late_ids[rid] = {"fact_id": old_fid, "after_fact_id": new_fid,
                             "reason": f"{old_fid} occurred earlier but ingests after {new_fid}; must not overwrite it"}
    order = [rid for _, rid in order_pool if rid not in late_ids]
    order += [rid for _, rid in order_pool if rid in late_ids]
    (GOLD / "ingest_order.json").write_text(json.dumps(
        {"order": order, "late_records": late_ids,
         "counts": {"total": len(order), "late": len(late_ids)}}, indent=1), encoding="utf-8")
    print(f"ingest_order.json: {len(order)} records, {len(late_ids)} late: {sorted(late_ids)}")

    # ---- backfill evidence into ledger ----
    missing = [fid for fid, ev in evidence.items() if not ev]
    assert not missing, f"facts without evidence: {missing}"
    for f in ledger["facts"]:
        f["evidence"] = evidence[f["id"]]
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ledger.json: evidence backfilled for {len(evidence)} facts")


if __name__ == "__main__":
    main()


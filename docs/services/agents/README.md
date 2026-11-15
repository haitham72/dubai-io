# Agents

One doc per agent: how it works end to end. How agents are combined to answer a request: [orchestrator.md](orchestrator.md). Connectors that feed agents: [../../plan/connectors.md](../../plan/connectors.md).

## Designed

| Agent | Doc | State |
|---|---|---|
| Emails (job applications first) | [emails.md](emails.md) | Design draft |

## Candidates (high level, 15 Nov)

Contest picks (proposed): **Lost item in transport**, **Documents & expiry + Bills**, **Job applications**.

### Work & admin
| Agent | What it does | Sources |
|---|---|---|
| Job applications | Applications + status | Email |
| What needs me | Unanswered messages, promises made ("I'll send it tomorrow") | Email, WhatsApp, Slack |
| Follow-up nudger | "You emailed Ali 5 days ago, no reply" | Email |
| Meeting prep | Brief on the person/company before an event | Calendar + all |
| Documents & expiry | Visa, Emirates ID, passport, licence, trade licence dates → reminders | Email, uploads |

### Household & money
| Agent | What it does | Sources |
|---|---|---|
| Bills | DEWA, e&/du, Empower, Salik amounts, due dates, spikes | Email |
| Rent & tenancy | Ejari renewal, rent cheque schedule, notice periods | Email, uploads |
| Subscriptions | Recurring charges from receipts | Email |
| Orders, returns & warranty | Return windows, warranty end dates | Email |
| Deliveries | Shipment status in one place | Email, WhatsApp |
| Home maintenance | AC service history, next service → Services | Email, orders |
| School (parents) | School emails + class groups → events, fees, forms | Email, WhatsApp |
| Spending | Monthly spend by category, salary day, unusual charges | Bank emails/SMS |
| Split with friends | "You owe me 120" from groups | WhatsApp |
| Insurance | Renewals, claim status | Email |
| Deposit disputes | Car rental / tenancy deposits returned or not, with evidence | Email, uploads |
| Household staff | Domestic worker visa, salary dates, leave | Email, uploads |

### Places & trips
| Agent | What it does | Sources |
|---|---|---|
| Lost item in transport | Ride receipts → time, route, plate → prefilled report | Email, memory |
| Trips | Bookings → itinerary, check-in, DXB guide | Email |
| Car | Mulkiya, insurance, service dates, fines | Email, uploads |
| Home search | Property alerts → shortlist, price changes | Email |

### Social & personal
| Agent | What it does | Sources |
|---|---|---|
| Group digests | Building/family/community groups → key items | WhatsApp |
| Invites & events | Invitations → calendar suggestions | WhatsApp, email |
| People | Birthdays, people you've lost touch with | WhatsApp, Instagram |
| Voice notes | Transcribe + summarize, pull out actions | WhatsApp |
| Official letters | Photo of a letter → meaning, deadline, what to do | Uploads |
| Health admin | Appointments, refills, insurance approvals | Email |
| Creator analytics | Reach, best times, top posts, comment themes | Instagram |
| Know me | Profile built from all agents | All |

### Small business & freelancers
| Agent | What it does | Sources |
|---|---|---|
| DM leads → orders | Customer questions in DMs → lead list, unanswered | Instagram, WhatsApp |
| Invoices & unpaid | Sent invoices, unpaid, reminder drafts | Email |
| Tax & licence deadlines | VAT, corporate tax, trade licence dates | Email, uploads |

### Bundles (several agents together)
| Bundle | Combines |
|---|---|
| Moving apartment | Ejari, DEWA move-out/in, internet transfer, movers, address change |
| New job / leaving a job | Offer, visa transfer, labour card, end-of-service, salary bank |
| New arrival in Dubai | Emirates ID, bank, SIM, DEWA, licence conversion, airport guide |
| Weekly briefing | Sunday "your week" from all agents |

## Shared pieces

- **Connectors:** Gmail, Outlook, WhatsApp, Slack, Instagram, Calendar, document upload.
- **Storage + learning:** `source_items`, `item_labels`, `label_rules`, `entities`, `entity_items` ([emails.md §3](emails.md#3-storage-postgres)).
- **Reminders:** one scheduler for expiry, due dates, follow-ups.
- **Document reading:** PDFs/photos (visa, Ejari, Mulkiya, warranties).
- **Test set per agent:** ~20 real examples with the right answer.

## Agent doc template

Each new agent doc has these sections:

1. **Trigger** — what question or event starts it
2. **Inputs** — connectors and tables it reads
3. **Contract** — input / output JSON the orchestrator sees
4. **Skill** — seed rules + prompt
5. **Output** — what the user sees
6. **Test set** — examples with the right answer

# Demo resident pack — “Sam Resident” (2 Nov 2026)

Status: **ready for founder review** (Phase A1). Fixture identities only — every seeded fact carries `provenance: demo_fixture` and renders a **Demo data** pill, never "You told me" (that label is only for what a real user stated, `user_supplied`; rules 2 and 9). Never present as a real person.

**Used by:** best-5 journeys in `2026-11-02-demo-journeys.md` + memory seed (companion-MCP Phase C4).  
**UI bots:** threads roll up per `2026-11-02-residence-ontology-tree.md` cheat sheet.

## Profile

| Field | Value | Provenance |
|---|---|---|
| Display name | Sam Resident | demo_fixture |
| Area | JLT (Jumeirah Lakes Towers) | demo_fixture |
| Household | Partner + 2 kids (Year 5, Year 3) | demo_fixture |
| Usual t-shirt size | XL | demo_fixture |
| Quiet hours | 22:00–07:00 Dubai | demo_fixture |

## Entities (seed table)

| id | Ontology path | Display | Notes | Demos |
|---|---|---|---|---|
| `gym.ff_marina` | `lifestyle/sports/gym` | Fitness First Marina | Membership active; renewal due | (gym micro); Lifestyle context |
| `school.gems_y5` | `kids_family/school_khda` | GEMS candidate A (Year 5) | Shortlist fixture | 1 KHDA |
| `school.nord_y5` | `kids_family/school_khda` | Nord Anglia candidate B (Year 5) | Shortlist fixture | 1 KHDA |
| `home.jlt_apt` | `household/home_profile` | JLT 2BR apartment | Building amenities known | 1, 5 |
| `ins.network_bp` | `health/insurance_network` | Network category **B+** (source label) | From “emailed list” fixture dated 2026-09 | 2 |
| `clinic.medcare_jlt` | `health/clinics_near` | Medcare JLT branch | Matches B+ in fixture list | 2 |
| `clinic.aster_marina` | `health/clinics_near` | Aster Marina | Matches B+ | 2 |
| `outing.mamzar` | `fun_out/beach_parks` | Al Mamzar Beach Park | Family Saturday | 3 |
| `trip.careem_marina_dxb` | `travel/taxi_recovery/rideshare_path` | Careem Marina → DXB | Last night 22:40; paid in app; Demo trip card | 4 |
| `car.sam_suv` | `cars/vehicle_profile` | Family SUV | Service context only | — |
| `dewa.account` | `money/bills_utilities/dewa` | DEWA account ···4821 | Reminder / pay-bills appendix | F |
| `salik.tag` | `money/salik` | Salik tag | Low-balance reminder fixture | F |
| `internet.du_home` | `tech/home_internet` | du Home Fibre | Plan options context | — |

## Rules

- Every seeded fact is stored as `provenance: demo_fixture` and shows **Demo data** (or Sandbox) in UI when used; never "You told me".
- Journeys **must not** ask for gym name, phone model, plate, insurance tier, or school years already in this pack.
- Founder may rename entities; keep `id`s stable for seed JSON.

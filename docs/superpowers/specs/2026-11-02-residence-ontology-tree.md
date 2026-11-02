# Residence ontology tree (temporal_note layer)

Status: **planning draft** (2 Nov 2026). This is the **huge fine-grained tree** for memory / classifier / demo packs — **not** the user sidebar.

- **User sees** (UI bots, short): Lifestyle · Career · Social · Household · Money · Travel · (Me = profile, not a task bot). Exact short list still founder-owned.
- **Engine holds** this tree; a **subagent** restructures it into temporal_note kinds/edges/`valid_from`–`valid_to`.
- Paths are stable IDs (`lifestyle/sports/gym`). Labels can localize later.
- **Never infer** (rule 9): health conditions, religion, ethnicity, nationality-as-trait, gender, sexuality, politics. Leaves marked `⚠ user-stated only` must not be hypothesized.
- **Civic execution** leaves: draft + portal / sandbox only until a real adapter + approval + evidence.

Rollup legend: each top ontology root maps to one UI bot in `[brackets]`.

---

## identity/ → [Me]

```
identity/
├── profile/                 # preferred name, area, household size — user_supplied
├── documents/               # Emirates ID, passport, visa — refs only, not scraped secrets
│   ├── emirates_id/
│   ├── passport/
│   ├── visa_residency/
│   └── driving_license/
├── preferences/
│   ├── language/
│   ├── quiet_hours/
│   ├── notification_consent/
│   └── accessibility/
├── size_profile/            # cloth sizes etc. — user_supplied or confirmed
└── hypotheses/              # "I noticed" only; Confirm/Forget
```

---

## lifestyle/ → [Lifestyle]

```
lifestyle/
├── sports/
│   ├── gym/                 # membership, freeze, PT, guest pass
│   ├── swimming/
│   ├── classes/             # yoga, pilates, spin, martial arts
│   ├── personal_training/
│   ├── running_outdoors/
│   ├── cycling/
│   ├── team_sports/         # padel, football, basketball pitches
│   └── sports_events/       # races, tickets — user interest
├── food/
│   ├── groceries/
│   ├── restaurants/
│   ├── cafes/
│   ├── delivery/            # Talabat / Noon Now class
│   ├── home_cooking/
│   ├── dietary_prefs/       # ⚠ user-stated only (allergies = user_supplied, not inferred illness)
│   └── water_coffee/        # subscriptions, office/home
├── wellness/
│   ├── salon_barber/
│   ├── spa/
│   ├── massage/
│   ├── sleep_routines/      # ⚠ user-stated only
│   └── fitness_wearables/   # ⚠ consented connect only; no diagnosis
├── cloth/
│   ├── everyday_wear/
│   ├── workwear/
│   ├── occasion_wear/
│   ├── kids_wear/
│   ├── shoes_accessories/
│   ├── laundry_care/        # press/dry-clean as lifestyle habit (also household/laundry)
│   ├── size_memory/         # rollup to identity/size_profile
│   └── ar_tryon/            # optional labelled demo (RTV) — LATER unless unlocked
├── home_life/
│   ├── entertaining/        # hosting people (links social + household)
│   ├── plants/
│   ├── pets/
│   │   ├── vet/
│   │   ├── grooming/
│   │   └── supplies/
│   └── building_amenities/  # building gym, pool, concierge, access cards
├── hobbies/
│   ├── reading_learning/
│   ├── photography/
│   ├── gaming/
│   ├── music/
│   └── maker_diy/
├── faith_culture/           # ⚠ user-stated only — never inferred
│   ├── prayer_reminders/    # Aladhan-style; consented
│   ├── ramadan_routines/    # only if user opted in
│   └── arts_culture_events/
└── subscriptions_lifestyle/ # streaming, boxes — distinct from tech/subscriptions
```

---

## household/ → [Household]

```
household/
├── home_profile/            # address area, building, landlord/owner — user_supplied
├── cleaning/
│   ├── regular_maid/
│   ├── deep_clean/
│   └── post_party/
├── laundry/
│   ├── wash_fold/
│   ├── dry_clean/
│   └── shirt_press/
├── ac_hvac/
│   ├── repair/
│   ├── maintenance_contract/
│   └── filters/
├── maintenance/
│   ├── plumbing/
│   ├── electrical/
│   ├── carpentry/
│   ├── painting/
│   ├── appliances/
│   └── handyman/
├── pest_control/
├── movers/
│   ├── local_move/
│   ├── packing/
│   └── storage/
├── supplies/                # consumables, first-night move kit
├── guests_ready/            # flat ready for visitors (plan leaf; links cleaning/food)
├── building_mgmt/
│   ├── access_cards/
│   ├── NOC_permissions/
│   ├── parking_bay/
│   └── community_rules/
├── tenancy/
│   ├── ejari/
│   ├── lease_renewal/
│   ├── security_deposit/
│   └── landlord_comms/
├── property_search/         # DLD / listings research — not a guarantee of deal
│   ├── rent_compare/
│   ├── buy_research/
│   └── viewing_checklist/
└── home_insurance/          # policy docs user-supplied
```

---

## kids_family/ → [Household] or [Social] (rollup TBD)

```
kids_family/
├── school_khda/             # leading journey
│   ├── shortlist/
│   ├── fees_compare/
│   ├── tours_appointments/
│   ├── applications/
│   ├── term_ready/          # uniform, books, calendar
│   └── transport_school_bus/
├── nursery_early_years/
├── activities/
│   ├── after_school/
│   ├── sports_kids/
│   └── camps/
├── childcare/
├── family_calendar/
├── dependents_profile/      # ⚠ user-stated only; no inference of family structure
└── parenting_admin/         # forms, permissions, vaccinations schedule as documents — not clinical advice
```

---

## career/ → [Career]

```
career/
├── employer_profile/
├── inbox_followups/         # Grok-style chase across mail
│   ├── gmail/
│   ├── outlook/
│   └── other_mail/
├── applications/
│   ├── job_search/
│   ├── active_applications/ # e.g. “Puffy” class chase
│   └── interviews/
├── meetings/
│   ├── calendar/
│   ├── prep_briefs/
│   └── follow_ups/
├── slack_teams/             # connectors later
├── performance_comp/        # ⚠ user-stated / docs only
├── skills_learning/
├── visa_admin/
│   ├── work_permit/
│   ├── labour_card/
│   └── company_docs/
├── expenses/
│   ├── receipt_capture/
│   ├── claim_pack/
│   └── employer_reimbursement/
├── travel_work/             # business trip prep (links travel/)
└── side_projects_work/      # professional side work — not lifestyle hobbies
```

---

## money/ → [Money]

```
money/
├── cashflow_overview/       # user-stated budgets; no bank scrape without connector
├── bills_utilities/
│   ├── dewa/
│   ├── district_cooling/    # Empower class
│   ├── water_other/
│   ├── telecom_home/        # du / etisalat home (links tech/)
│   └── telecom_mobile/
├── salik/
│   ├── balance_reminders/
│   └── tag_renewal/
├── parking_payments/        # Parkin / RTA parking as money event (journey step often under travel/fun)
├── banking/
│   ├── accounts_list/       # user-stated
│   ├── cards/
│   └── transfers_reminders/
├── uae_pass/
│   └── sandbox_demo/        # connect + draft; never fake Paid
├── pay_all_bills/           # orchestrated demo journey leaf
├── reimbursements/          # insurance or employer claim packs
├── insurance_policies/
│   ├── health_policy_meta/  # network category label e.g. B+ — from docs, not inferred illness
│   ├── motor_policy/
│   ├── home_policy/
│   └── life_policy/         # ⚠ docs only
├── taxes_corp/              # if relevant; user-stated
├── subscriptions_money/     # paid recurring (rollup view)
└── charity_donations/       # licensed charities; approval before send
```

---

## health/ → [Lifestyle] or [Money] for insurance admin (rollup TBD)

```
health/                      # access & admin — NOT clinical diagnosis
├── insurance_network/       # leading journey: match card + list → clinics
│   ├── card_capture/
│   ├── network_match/
│   ├── branch_map/
│   └── preauth_checklist/
├── clinics_near/
├── hospitals/
├── pharmacy/
├── appointments/
├── dental/
├── optical/
├── mental_wellbeing_access/ # ⚠ user-stated; directory/access only, no therapy chatbot claims
└── claims_reimbursement/    # links money/reimbursements
```

---

## cars/ → [Travel] or [Household] (recommend [Travel] for mobility; or UI “Travel”)

```
cars/
├── vehicle_profile/         # plate optional user_supplied; make/model from user or booking
├── service/
│   ├── scheduled_service/
│   ├── breakdown_assist/    # policy-linked journey
│   └── tyre_battery/
├── wash_detail/
├── salik_tag/               # links money/salik
├── fines_display/           # display + portal; no fake pay
├── registration_mulkiya/
├── insurance_motor/         # links money/insurance_policies/motor_policy
├── fuel_ev_charging/
├── buy_research/
│   ├── new_car/
│   ├── used_car/
│   └── compare_shortlist/
├── sell_trade_in/
└── rental_temp/             # temporary hire
```

---

## travel/ → [Travel]

```
travel/
├── dxb_arrival/             # airport guide — no invented belt/gate
│   ├── terminal_orient/
│   ├── luggage_belt_user_confirmed/
│   ├── metro_taxi_options/
│   └── late_night_constraints/
├── taxi_recovery/           # lost item — track ride; app/card vs cash; never plate-first
│   ├── rideshare_path/      # Demo trip card + paste receipt (B+A)
│   ├── cash_path/           # where + when → RTA draft
│   └── rta_handoff/
├── flights/
│   ├── book_research/
│   ├── check_in_reminders/
│   └── disruption_replan/
├── trips/
│   ├── weekend_uae/
│   ├── international/
│   └── packing_lists/
├── business_trip/           # links career/travel_work
├── home_holding/            # while away: plants, maid, security
├── visas_travel/
├── hotels_stays/
├── maps_routes/
├── parking_as_step/         # Parkin inside an outing — not a destination app
└── transport_local/
    ├── metro/
    ├── bus/
    ├── careem_uber_hala/
    └── car_share/
```

---

## fun_out/ → [Lifestyle] or [Social]

```
fun_out/
├── beach_parks/             # Mamzar reference journey
│   ├── prepare_supplies/
│   ├── entry_parking/
│   ├── on_site/
│   └── return_meal/
├── dining_out/
├── events_tickets/
├── weekends/
├── attractions/
├── nightlife/               # ⚠ no inference of habits
├── sports_spectating/
└── kids_fun_day/            # links kids_family
```

---

## tech/ → [Lifestyle] or [Household]

```
tech/
├── home_internet/
│   ├── outage_troubleshoot/
│   ├── plan_change/
│   └── router_wifi/
├── mobile_plan/
│   ├── du_etisalat/
│   ├── esim/
│   └── device_installment/
├── devices/
│   ├── phone/
│   ├── laptop/
│   ├── tablet/
│   └── wearables/
├── subscriptions_tech/
├── smart_home/
├── accounts_security/       # password/reset reminders — no storing passwords in chat
└── software_tools/
```

---

## social/ → [Social]

```
social/
├── community_feed/          # Reddit-style surface
│   ├── posts/
│   ├── comments/
│   ├── communities_joined/
│   └── stories/
├── chats/
│   ├── dm/
│   ├── groups/
│   └── calls_log/
├── neighbours_building/
├── friends_circle/          # ⚠ user-stated only
├── hosting_guests/          # people-first; links household/guests_ready + lifestyle/food
├── events_social/
└── reciprocity_reminders/   # birthdays etc. — user-stated dates only
```

---

## civic_gov/ → [Money] / [Travel] / [Household] by leaf

```
civic_gov/                   # feature leaves; honesty rules apply
├── uae_pass_identity/
├── rta/
│   ├── fines/
│   ├── parking/
│   ├── lost_found/
│   └── nol_card/
├── dewa_accounts/
├── police_report_assist/    # draft + official channel; no fake Filed
├── tasjeel/
├── residency_amer/          # admin handoff
├── trade_license/           # if user business — career link
└── donations_licensed/
```

---

## projects/ → rolls up to primary UI bot of the campaign

```
projects/                    # instances, not free-form personality bots
├── templates/
│   ├── move_home/           # tenancy + movers + DEWA + internet + supplies + food
│   ├── school_plus_home/    # KHDA + area + commute leading journey
│   ├── beach_day/           # Mamzar-class
│   ├── business_trip/
│   ├── guests_tonight/
│   ├── renovation/
│   └── wedding_event/
└── instances/               # project_id → links many ontology leaves + tasks
```

---

## meta/ (engine only — never a UI bot)

```
meta/
├── connectors/              # gmail, outlook, maps, uae_pass_sandbox, browser_agent…
├── adapters/                # registered capability ids
├── demo_resident_pack/      # fixture entities so demos never ask stupid questions
├── provenance/
├── outbox_scheduler/        # proactive = deterministic
└── ontology_versions/       # subagent migrations of this tree
```

---

## UI rollup cheat sheet (draft)

| UI bot | Primary ontology roots |
|---|---|
| **Lifestyle** | `lifestyle/`, `fun_out/`, `tech/` (soft), `health/` access UX optional |
| **Career** | `career/` |
| **Social** | `social/`, parts of `kids_family/` people side |
| **Household** | `household/`, `kids_family/` school/home, pets under lifestyle or here |
| **Money** | `money/`, `civic_gov/` payments/reminders, insurance admin |
| **Travel** | `travel/`, `cars/` |
| **Me** | `identity/`, hypotheses UI |

Classifier: ask → finest leaf → rollup UI bot → thread listed under that bot.

---

## Subagent brief (later execution — not now)

When founder unlocks implementation planning for memory:

1. Turn each path into `kind` + allowed attributes + deny-lists.
2. Define edges: `person–uses→gym`, `vehicle–has→salik_tag`, `project–includes→leaf`.
3. Seed `meta/demo_resident_pack` for Fitness First, DEWA account placeholders, one car, one school year group, Careem-style trip fixture.
4. Emit rollup table UI bot ← paths.
5. Version the tree under `meta/ontology_versions/`.

---

## Counts (approx.)

- Roots: 14 (`identity`, `lifestyle`, `household`, `kids_family`, `career`, `money`, `health`, `cars`, `travel`, `fun_out`, `tech`, `social`, `civic_gov`, `projects` + `meta`)
- Leaves: **~200+** paths at depth 3–4 in this draft — expected to grow; subagent may merge synonyms (`laundry_care` vs `household/laundry`).

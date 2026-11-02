"use client";
/**
 * Demo journeys: interactive flows. Schools + gyms load live Google Places;
 * when no adapter exists, buttons open the real business / KHDA site — never a dead click.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Shirt } from "lucide-react";
import { JLT, searchPlaces, type Place } from "../data/places";
import {
  businessHref,
  FITNESS_FIRST_MEMBERSHIP,
  KHDA_DIRECTORY,
  openBusinessSite,
} from "../data/open-business";
import { Button, DemoPill } from "../ui";
import s from "./tasks.module.css";

function Bubble({ role, children }: { role: "user" | "assistant"; children: ReactNode }) {
  return (
    <div className={role === "user" ? s.bubbleUser : s.bubbleAssistant} data-testid={`demo-msg-${role}`}>
      {children}
    </div>
  );
}

function ChoiceCards({
  label,
  options,
  onPick,
}: {
  label: string;
  options: { id: string; title: string; sub?: string }[];
  onPick: (id: string) => void;
}) {
  return (
    <div className={s.choices} role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" className={s.choice} data-testid={`choice-${o.id}`} onClick={() => onPick(o.id)}>
          <strong>{o.title}</strong>
          {o.sub ? <span>{o.sub}</span> : null}
        </button>
      ))}
    </div>
  );
}

function Card({ children, testId }: { children: ReactNode; testId?: string }) {
  return (
    <div className={s.tripCard} data-testid={testId}>
      {children}
    </div>
  );
}

function StatusLine({ children }: { children: ReactNode }) {
  return <div className={s.next} data-testid="demo-status">{children}</div>;
}

function OpenSiteButton({
  href,
  label,
  primary = true,
  testId,
  fallback = KHDA_DIRECTORY,
}: {
  href: string | null | undefined;
  label: string;
  primary?: boolean;
  testId?: string;
  fallback?: string;
}) {
  const url = businessHref(href) || businessHref(fallback);
  return (
    <Button
      variant={primary ? "primary" : "secondary"}
      data-testid={testId}
      onClick={() => openBusinessSite(url)}
    >
      {label}
    </Button>
  );
}

function LivePlaceRow({
  place,
  selected,
  onSelect,
  actionLabel = "Open website",
}: {
  place: Place;
  selected?: boolean;
  onSelect?: () => void;
  actionLabel?: string;
}) {
  const site = businessHref(place.website);
  const maps = businessHref(place.maps_url);
  return (
    <div
      className={`${s.tripCard} ${selected ? s.cardSelected : ""}`}
      data-testid="live-biz-card"
      data-place-id={place.id || place.name}
    >
      <button type="button" className={s.cardHit} onClick={onSelect} disabled={!onSelect}>
        <p className={s.placeNameLine}>
          <strong>{place.name}</strong>
          <span className={s.liveTag}>Live · Google</span>
        </p>
        <p className={s.muted}>
          {place.rating != null ? `★ ${Number(place.rating).toFixed(1)}` : "No rating"}
          {place.short_address || place.address
            ? ` · ${(place.short_address || place.address || "").split(" - ").slice(0, 2).join(", ")}`
            : ""}
          {place.open_now != null ? ` · ${place.open_now ? "Open now" : "Closed"}` : ""}
        </p>
        <p className={s.placeProv}>provider_confirmed · not a booking</p>
      </button>
      <div className={s.approvalActions}>
        <OpenSiteButton href={site || maps} label={site ? actionLabel : "Open in Maps"} testId="open-biz-site" />
        {site && maps && (
          <Button variant="ghost" onClick={() => openBusinessSite(maps)}>Maps</Button>
        )}
      </div>
    </div>
  );
}

export function TaxiDemo() {
  const [path, setPath] = useState<"pick" | "rideshare" | "cash" | "rta" | "driver">("pick");
  return (
    <>
      <Bubble role="user">I left a black backpack in a taxi last night</Bubble>
      <Bubble role="assistant">
        Let’s track your ride. How did you pay or book? I already know you were around Marina — no licence ID asked first. <DemoPill />
      </Bubble>
      {path === "pick" && (
        <ChoiceCards
          label="How did you pay"
          options={[
            { id: "rideshare", title: "Ride-share or card", sub: "Careem / Uber / Hala / card payment" },
            { id: "cash", title: "Cash", sub: "Street or rank taxi" },
          ]}
          onPick={(id) => setPath(id === "cash" ? "cash" : "rideshare")}
        />
      )}
      {path === "rideshare" && (
        <>
          <Card testId="demo-trip-card">
            <p><strong>Careem · Marina → DXB</strong> <DemoPill /></p>
            <p className={s.muted}>Yesterday 22:40 · Paid in app · Trip fixture (demo_fixture)</p>
            <p className={s.muted}>Vehicle class: Comfort · Drop-off Terminal 3 kerb</p>
            <p className={s.muted}>Or paste a trip link / receipt when you have one.</p>
          </Card>
          <div className={s.approvalActions}>
            <Button variant="primary" onClick={() => setPath("driver")}>Contact driver / in-app lost item</Button>
            <Button variant="secondary" onClick={() => setPath("rta")}>Draft RTA report from this trip</Button>
          </div>
          <Button variant="ghost" onClick={() => setPath("pick")}>Back</Button>
        </>
      )}
      {path === "cash" && (
        <>
          <Bubble role="assistant">Roughly where and when? Vehicle details stay optional — never required first.</Bubble>
          <ChoiceCards
            label="Where and when"
            options={[
              { id: "marina-eve", title: "Marina / JBR · evening", sub: "After 18:00" },
              { id: "dxb-late", title: "Toward DXB · after 22:00", sub: "Late night" },
            ]}
            onPick={() => setPath("rta")}
          />
          <Button variant="ghost" onClick={() => setPath("pick")}>Back</Button>
        </>
      )}
      {path === "driver" && (
        <>
          <StatusLine><strong>Status</strong> Waiting / Blocked — Careem lost-item channel needs a live adapter</StatusLine>
          <Card>
            <p><strong>Staged next</strong> <DemoPill /></p>
            <p className={s.muted}>Open the Careem trip → Help → Lost item, or draft an RTA report from the same trip facts.</p>
          </Card>
          <div className={s.approvalActions}>
            <Button variant="primary" disabled>Open Careem (not wired)</Button>
            <Button variant="secondary" onClick={() => setPath("rta")}>Draft RTA instead</Button>
          </div>
        </>
      )}
      {path === "rta" && (
        <>
          <Card>
            <p><strong>RTA lost-property draft</strong> <DemoPill /></p>
            <p className={s.muted}>Item: black backpack · Area: Marina / DXB corridor · Time: last night after 22:00</p>
            <p className={s.muted}>Fields ready to copy — nothing Filed without a registered adapter.</p>
          </Card>
          <StatusLine><strong>Status</strong> Draft ready · Waiting / Blocked</StatusLine>
          <div className={s.approvalActions}>
            <OpenSiteButton href="https://www.rta.ae/" label="Open RTA website" testId="open-rta" fallback="https://www.rta.ae/" />
            <Button variant="secondary" onClick={() => {
              const text = "RTA lost-property draft — black backpack · Marina/DXB · last night after 22:00 (Dubai-io demo draft)";
              void navigator.clipboard?.writeText(text);
            }}>Copy draft text</Button>
            <Button variant="ghost" onClick={() => setPath("pick")}>Start over</Button>
          </div>
          <p className={s.approvalNote}>No RTA adapter — the RTA site is the honest handoff. Nothing Filed in Dubai-io.</p>
        </>
      )}
    </>
  );
}

export function GymDemo() {
  const [places, setPlaces] = useState<Place[]>([]);
  const [asOf, setAsOf] = useState<string>("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [club, setClub] = useState<Place | null>(null);
  const [choice, setChoice] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    searchPlaces("Fitness First Dubai Marina")
      .then((res) => {
        if (!alive) return;
        setPlaces(res.places.slice(0, 5));
        setAsOf(res.as_of);
        setClub(res.places[0] ?? null);
      })
      .catch(() => {
        if (alive) setLoadError("Live gym listings unavailable right now.");
      })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const clubSite = businessHref(club?.website) || FITNESS_FIRST_MEMBERSHIP;
  const labels: Record<string, string> = {
    renew: "Renew / membership plans",
    freeze: "Freeze membership",
    change: "Change plan",
    cancel: "Cancel membership",
  };

  return (
    <>
      <Bubble role="user">Update my gym membership</Bubble>
      <Bubble role="assistant">
        Loading live Fitness First / Marina clubs from Google Places. Dubai-io cannot renew for you — when you approve, I open the club’s real membership site.
      </Bubble>
      {loading && <p className={s.muted} role="status">Finding clubs…</p>}
      {loadError && <StatusLine>{loadError}</StatusLine>}
      {!loading && !loadError && places.map((p) => (
        <LivePlaceRow
          key={p.id || p.name}
          place={p}
          selected={club?.id === p.id || club?.name === p.name}
          onSelect={() => setClub(p)}
          actionLabel="Open club site"
        />
      ))}
      {asOf && <p className={s.approvalNote}>Live from Google · {asOf}. Not a price quote.</p>}

      {club && !choice && (
        <>
          <Bubble role="assistant">
            Selected <strong>{club.name}</strong>. What do you want to do on their site?
          </Bubble>
          <ChoiceCards
            label="Gym options"
            options={[
              { id: "renew", title: "Renew / see plans", sub: "Opens membership page" },
              { id: "freeze", title: "Freeze", sub: "Manage on club site" },
              { id: "change", title: "Change plan", sub: "Manage on club site" },
              { id: "cancel", title: "Cancel", sub: "Manage on club site" },
            ]}
            onPick={setChoice}
          />
        </>
      )}

      {club && choice && (
        <div className={s.approval} data-testid="demo-approval">
          <div className={s.approvalHead}>
            <div>
              <strong>{labels[choice]} — {club.name}</strong>
              <p>No Fitness First adapter — opening their website is the honest next step</p>
            </div>
          </div>
          <StatusLine><strong>Status</strong> Blocked in-app · continue on merchant site</StatusLine>
          <div className={s.approvalActions}>
            <OpenSiteButton
              href={choice === "renew" ? (businessHref(club.website) || FITNESS_FIRST_MEMBERSHIP) : clubSite}
              label={`Open ${choice === "renew" ? "membership" : "club"} website`}
              testId="open-gym-site"
              fallback={FITNESS_FIRST_MEMBERSHIP}
            />
            <OpenSiteButton href={FITNESS_FIRST_MEMBERSHIP} label="Fitness First memberships" primary={false} fallback={FITNESS_FIRST_MEMBERSHIP} />
            <Button variant="ghost" onClick={() => setChoice(null)}>Back</Button>
          </div>
          <p className={s.approvalNote}>Nothing is Paid or Renewed in Dubai-io. The club site is authoritative.</p>
        </div>
      )}
    </>
  );
}

export function LaundryDemo() {
  const [sent, setSent] = useState(false);
  return (
    <>
      <Bubble role="user">Laundry pickup for 3 shirts, needed by tomorrow 9am</Bubble>
      <Bubble role="assistant">Marina Express Laundry can do it at its published price. Review what would be shared before anything is sent.</Bubble>
      {!sent ? (
        <div className={s.approval} data-testid="demo-approval">
          <div className={s.approvalHead}>
            <span className={s.approvalIcon}><Shirt size={18} strokeWidth={2} aria-hidden /></span>
            <div>
              <strong>Send this order to Marina Express Laundry?</strong>
              <p>Published price · AED 18.00 total estimate <DemoPill /></p>
            </div>
          </div>
          <div className={s.shareGrid}>
            <div>
              <h3>Will be shared</h3>
              <ul>
                <li>3× Shirt wash + press</li>
                <li>Area: JLT (you told me)</li>
                <li>Deadline: tomorrow 09:00</li>
              </ul>
            </div>
            <div>
              <h3>Never shared</h3>
              <ul>
                <li>Your name</li>
                <li>Phone number</li>
                <li>Other orders</li>
              </ul>
            </div>
          </div>
          <div className={s.approvalActions}>
            <Button variant="primary" onClick={() => setSent(true)}>Approve and send (demo)</Button>
            <Button variant="secondary" disabled>Not now</Button>
          </div>
          <p className={s.approvalNote}>Demo — tap records a staged send. Real merchant send needs a live mini-app path.</p>
        </div>
      ) : (
        <>
          <StatusLine><strong>Status</strong> Waiting provider · Demo staged order (not Paid / Delivered)</StatusLine>
          <Card>
            <p><strong>Marina Express Laundry</strong> · JLT <DemoPill /></p>
            <p className={s.muted}>Driver on the way — example only · Shirt wash + press AED 6.00 × 3</p>
          </Card>
        </>
      )}
      <aside className={s.detailsPanel} aria-label="Details">
        <h2>Details</h2>
        <p><strong>Marina Express Laundry</strong> · JLT, Dubai <DemoPill /></p>
        <p className={s.muted}>Published price list as of 13 Oct — Shirt wash + press AED 6.00 · Trousers AED 8.00</p>
        <p><strong>Deadline</strong> Tomorrow 09:00 (you told me)</p>
      </aside>
    </>
  );
}

export function KhdaDemo() {
  const [step, setStep] = useState<"constraints" | "schools" | "approve" | "waiting">("constraints");
  const [schools, setSchools] = useState<Place[]>([]);
  const [asOf, setAsOf] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [picked, setPicked] = useState<Place[]>([]);

  const loadSchools = () => {
    setLoading(true);
    setLoadError(null);
    // JLT bias — real British-curriculum schools from Google Places (not invented GEMS stubs).
    searchPlaces("British curriculum school near Jumeirah Lakes Towers Dubai", JLT)
      .then((res) => {
        setSchools(res.places.slice(0, 6));
        setAsOf(res.as_of);
        if (!res.places.length) setLoadError("No live schools matched. Open the KHDA directory instead.");
      })
      .catch(() => setLoadError("Live school search failed."))
      .finally(() => setLoading(false));
  };

  const toggle = (place: Place) => {
    setPicked((cur) => {
      const id = place.id || place.name;
      const exists = cur.some((p) => (p.id || p.name) === id);
      return exists ? cur.filter((p) => (p.id || p.name) !== id) : [...cur, place];
    });
  };

  const openSelectedSites = () => {
    const opened = picked.filter((p) => openBusinessSite(p.website || p.maps_url));
    if (!opened.length) openBusinessSite(KHDA_DIRECTORY);
    setStep("waiting");
  };

  return (
    <>
      <Bubble role="user">Year 5 British curriculum — shortlist schools and a home with a sane school run</Bubble>
      <Bubble role="assistant">
        Using JLT + Year 5 British from what you told me. I will load <strong>live Google Places</strong> schools — ratings are provider_confirmed. Fees and KHDA inspection grades still need the school or KHDA site (I will not invent them).
      </Bubble>

      {step === "constraints" && (
        <>
          <Card testId="demo-constraints">
            <p><strong>Constraints on file</strong></p>
            <ul className={s.planList}>
              <li>Year 5 · British curriculum</li>
              <li>Home area: JLT · work / commute: Marina</li>
              <li>Next: live school shortlist near JLT</li>
            </ul>
          </Card>
          <div className={s.approvalActions}>
            <Button
              variant="primary"
              onClick={() => {
                setStep("schools");
                loadSchools();
              }}
            >
              Find live schools near JLT
            </Button>
            <OpenSiteButton href={KHDA_DIRECTORY} label="Open KHDA directory" primary={false} testId="open-khda-dir" />
          </div>
        </>
      )}

      {step === "schools" && (
        <>
          <Bubble role="assistant">Tap schools to shortlist, then open their admissions sites. Nothing is enquired until you leave Dubai-io.</Bubble>
          {loading && <p className={s.muted} role="status">Searching Google Places…</p>}
          {loadError && <StatusLine>{loadError}</StatusLine>}
          {schools.map((place) => {
            const id = place.id || place.name;
            const selected = picked.some((p) => (p.id || p.name) === id);
            return (
              <LivePlaceRow
                key={id}
                place={place}
                selected={selected}
                onSelect={() => toggle(place)}
                actionLabel="Open school website"
              />
            );
          })}
          {asOf && <p className={s.approvalNote}>Live from Google · {asOf}. Not KHDA official ratings.</p>}
          <div className={s.approvalActions}>
            <Button variant="primary" disabled={picked.length === 0} onClick={() => setStep("approve")}>
              Plan tour enquiries ({picked.length})
            </Button>
            <OpenSiteButton href={KHDA_DIRECTORY} label="KHDA school directory" primary={false} />
            <Button variant="ghost" onClick={() => { setStep("constraints"); setPicked([]); }}>Back</Button>
          </div>
        </>
      )}

      {step === "approve" && (
        <div className={s.approval} data-testid="demo-approval">
          <div className={s.approvalHead}>
            <div>
              <strong>No school-enquiry adapter — open {picked.length} school site(s)?</strong>
              <p>Honest handoff: admissions forms live on the school websites</p>
            </div>
          </div>
          <ul className={s.planList}>
            {picked.map((p) => (
              <li key={p.id || p.name}>{p.name}{p.website ? "" : " (Maps only)"}</li>
            ))}
          </ul>
          <div className={s.approvalActions}>
            <Button variant="primary" data-testid="open-school-sites" onClick={openSelectedSites}>
              Open selected school websites
            </Button>
            <OpenSiteButton href={KHDA_DIRECTORY} label="Also open KHDA directory" primary={false} />
            <Button variant="secondary" onClick={() => setStep("schools")}>Not now</Button>
          </div>
        </div>
      )}

      {step === "waiting" && (
        <>
          <StatusLine>
            <strong>Status</strong> Blocked in-app · school websites opened for you · no seat confirmed in Dubai-io
          </StatusLine>
          <div className={s.approvalActions}>
            {picked.map((p) => (
              <OpenSiteButton
                key={p.id || p.name}
                href={p.website || p.maps_url}
                label={`Re-open ${p.name?.slice(0, 28) || "school"}`}
                primary={false}
              />
            ))}
            <OpenSiteButton href={KHDA_DIRECTORY} label="KHDA directory" />
            <Button variant="ghost" onClick={() => { setStep("constraints"); setPicked([]); setSchools([]); }}>Restart</Button>
          </div>
        </>
      )}
    </>
  );
}

export function InsuranceDemo() {
  const [step, setStep] = useState<"confirm" | "list" | "detail" | "next">("confirm");
  const [clinic, setClinic] = useState<string | null>(null);
  return (
    <>
      <Bubble role="user">Ear pain — which nearby clinic does my insurance cover?</Bubble>
      <Bubble role="assistant">I can match nearby clinics against your network list — network match is not a treatment guarantee.</Bubble>
      {step === "confirm" && (
        <>
          <Card>
            <p><strong>Using your B+ network list</strong> · Demo · as_of Sep 2026 <DemoPill /></p>
            <p className={s.muted}>Member id fixture on file · outpatient only for this pass</p>
          </Card>
          <div className={s.approvalActions}>
            <Button variant="primary" onClick={() => setStep("list")}>Continue</Button>
            <Button variant="secondary" disabled>Not my list</Button>
          </div>
        </>
      )}
      {step === "list" && (
        <>
          <button type="button" className={s.tripCard} data-testid="clinic-medcare" onClick={() => { setClinic("Medcare JLT"); setStep("detail"); }}>
            <p><strong>Medcare JLT</strong> · matches B+ <DemoPill /></p>
            <p className={s.muted}>Estimate ~12 min from JLT home · outpatient checklist next</p>
          </button>
          <button type="button" className={s.tripCard} data-testid="clinic-aster" onClick={() => { setClinic("Aster Marina"); setStep("detail"); }}>
            <p><strong>Aster Marina</strong> · matches B+ <DemoPill /></p>
            <p className={s.muted}>Estimate ~18 min · direct-billing unknown in fixture</p>
          </button>
          <Button variant="ghost" onClick={() => setStep("confirm")}>Back</Button>
        </>
      )}
      {step === "detail" && clinic && (
        <>
          <Card>
            <p><strong>{clinic}</strong> <DemoPill /></p>
            <p className={s.muted}>Network match only — not prior authorization. Ear / ENT outpatient note for your GP if needed.</p>
          </Card>
          <div className={s.approvalActions}>
            <Button variant="primary" onClick={() => setStep("next")}>Next steps</Button>
            <Button variant="ghost" onClick={() => setStep("list")}>Back</Button>
          </div>
        </>
      )}
      {step === "next" && (
        <>
          <StatusLine><strong>Next</strong> Book / Call / Directions — no invented coverage approval</StatusLine>
          <div className={s.approvalActions}>
            <Button variant="primary" disabled>Book (needs adapter)</Button>
            <Button variant="secondary" disabled>Call clinic</Button>
            <Button variant="ghost" onClick={() => setStep("confirm")}>Restart</Button>
          </div>
        </>
      )}
    </>
  );
}

export function MamzarDemo() {
  const [mode, setMode] = useState<"plan" | "yes" | "replan">("plan");
  const steps = mode === "replan"
    ? [
        "Prepare — beach toys basket (fixture prices)",
        "Travel — departure pushed +1h",
        "Parking / entry — extend only if a real pass exists",
        "Return meal — hot meal retimed (+1h)",
      ]
    : [
        "Prepare — beach toys basket (fixture prices)",
        "Travel — route timed to delivery",
        "Parking / entry — only if a real pass exists",
        "Return meal — hot meal on the way home",
      ];
  return (
    <>
      <Bubble role="user">Saturday Mamzar with the kids — toys and a hot meal when we get back</Bubble>
      <Bubble role="assistant">One plan — approve steps or Yes to all. Parking is a step inside the outing, not a separate app.</Bubble>
      <Card>
        <p><strong>Plan</strong> <DemoPill /></p>
        <ul className={s.planList}>
          {steps.map((line) => (
            <li key={line}>
              {mode !== "plan" ? "✓ " : ""}
              {line}
              {mode !== "plan" ? " · Demo staged" : ""}
            </li>
          ))}
        </ul>
      </Card>
      {mode === "plan" && (
        <div className={s.approvalActions}>
          <Button variant="primary" onClick={() => setMode("yes")}>Yes to all</Button>
          <Button variant="secondary" onClick={() => setMode("replan")}>Stay +1h — replan</Button>
        </div>
      )}
      {mode === "yes" && (
        <StatusLine><strong>Status</strong> Running · each step Demo staged — Confirmed only with provider evidence</StatusLine>
      )}
      {mode === "replan" && (
        <>
          <StatusLine><strong>Replanned</strong> Meal + parking shifted +1h · still within approved outing limits</StatusLine>
          <Button variant="primary" onClick={() => setMode("yes")}>Yes to replanned plan</Button>
        </>
      )}
      {(mode === "yes" || mode === "replan") && (
        <Button variant="ghost" onClick={() => setMode("plan")}>Back to plan</Button>
      )}
    </>
  );
}

export function GuestsDemo() {
  const [mode, setMode] = useState<"plan" | "yes" | "dinner">("plan");
  return (
    <>
      <Bubble role="user">Guests at 8 — flat ready and light dinner</Bubble>
      <Bubble role="assistant">JLT 2BR is on file. Multi-step plan — nothing sent without approval.</Bubble>
      <Card>
        <p><strong>Plan</strong> <DemoPill /></p>
        <ul className={s.planList}>
          <li>{mode === "yes" ? "✓ " : ""}Clean 2BR — fixed-price sandbox{mode === "yes" ? " · Demo staged" : ""}</li>
          <li>{mode === "yes" ? "✓ " : ""}Light dinner — {mode === "dinner" ? "cook at home option" : "delivery options"}{mode === "yes" ? " · Demo staged" : ""}</li>
          <li>{mode === "yes" ? "✓ " : ""}Building access — known home{mode === "yes" ? " · Demo staged" : ""}</li>
        </ul>
      </Card>
      {mode === "plan" && (
        <div className={s.approvalActions}>
          <Button variant="primary" onClick={() => setMode("yes")}>Yes to all</Button>
          <Button variant="secondary" onClick={() => setMode("dinner")}>Change dinner</Button>
        </div>
      )}
      {mode === "dinner" && (
        <>
          <ChoiceCards
            label="Dinner"
            options={[
              { id: "delivery", title: "Delivery", sub: "Light mezze · fixture prices" },
              { id: "cook", title: "Cook at home", sub: "Shopping list only" },
            ]}
            onPick={() => setMode("yes")}
          />
          <Button variant="ghost" onClick={() => setMode("plan")}>Back</Button>
        </>
      )}
      {mode === "yes" && (
        <>
          <StatusLine><strong>Status</strong> Needs you / Running per step — no fake “chef confirmed”</StatusLine>
          <Button variant="ghost" onClick={() => setMode("plan")}>Back to plan</Button>
        </>
      )}
    </>
  );
}

export function AcDemo() {
  const [windowId, setWindowId] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  return (
    <>
      <Bubble role="user">Apartment AC is not cooling — fix before Friday</Bubble>
      <Bubble role="assistant">JLT home is on file. Pick a window — I will not invent a booking.</Bubble>
      {!windowId && (
        <ChoiceCards
          label="Service window"
          options={[
            { id: "thu", title: "Thursday afternoon", sub: "Before Friday deadline" },
            { id: "fri-am", title: "Friday morning", sub: "Last slot before weekend" },
          ]}
          onPick={setWindowId}
        />
      )}
      {windowId && !approved && (
        <div className={s.approval} data-testid="demo-approval">
          <div className={s.approvalHead}>
            <div>
              <strong>Request AC visit — {windowId === "thu" ? "Thursday afternoon" : "Friday morning"}?</strong>
              <p>Fixed-price sandbox merchant <DemoPill /></p>
            </div>
          </div>
          <div className={s.shareGrid}>
            <div>
              <h3>Will be shared</h3>
              <ul>
                <li>Address area: JLT</li>
                <li>Issue: not cooling</li>
                <li>Window: {windowId}</li>
              </ul>
            </div>
            <div>
              <h3>Never shared</h3>
              <ul>
                <li>Access PIN</li>
                <li>Other home tasks</li>
              </ul>
            </div>
          </div>
          <div className={s.approvalActions}>
            <Button variant="primary" onClick={() => setApproved(true)}>Approve (demo)</Button>
            <Button variant="secondary" onClick={() => setWindowId(null)}>Back</Button>
          </div>
        </div>
      )}
      {approved && (
        <StatusLine><strong>Status</strong> Waiting / Blocked — AC merchant adapter not connected</StatusLine>
      )}
    </>
  );
}

export function DemoBody({ id }: { id: string }) {
  if (id === "demo-taxi") return <TaxiDemo />;
  if (id === "demo-gym") return <GymDemo />;
  if (id === "demo-laundry") return <LaundryDemo />;
  if (id === "demo-khda") return <KhdaDemo />;
  if (id === "demo-insurance") return <InsuranceDemo />;
  if (id === "demo-mamzar") return <MamzarDemo />;
  if (id === "demo-guests") return <GuestsDemo />;
  if (id === "demo-ac") return <AcDemo />;
  return <p className={s.entry}>This is an example task so you can see how threads look. Nothing was sent or booked.</p>;
}

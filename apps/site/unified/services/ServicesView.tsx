"use client";
import { useMemo, useState } from "react";
import {
  Car,
  Droplets,
  ExternalLink,
  FileText,
  Home,
  Landmark,
  LayoutGrid,
  MapPin,
  MessageCircle,
  MoreHorizontal,
  PawPrint,
  Receipt,
  Star,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useApp } from "../state";
import { Button, DemoPill, ICON, IconButton, SearchField } from "../ui";
import {
  CATEGORY_CHIPS,
  DEMO_REQUESTS,
  DEMO_SERVICES,
  filterServices,
  type CategoryChip,
  type DemoService,
} from "./services-data";
import s from "./services.module.css";

const CHIP_ICON: Record<CategoryChip, LucideIcon> = {
  all: LayoutGrid,
  home: Home,
  laundry: Droplets,
  pets: PawPrint,
  car: Car,
  bills: Receipt,
  government: Landmark,
};

function ServiceCard({ service, onEstimate }: { service: DemoService; onEstimate: (name: string) => void }) {
  if (service.kind === "portal") {
    return (
      <article className={s.card} data-testid="service-card" data-service-id={service.id}>
        <div className={s.cardMediaPortal}>
          <FileText size={40} strokeWidth={1.5} />
          <span className={s.demoOnCard}><DemoPill /></span>
        </div>
        <div className={s.cardBody}>
          <h3 className={s.cardTitle}>{service.name}</h3>
          <p className={s.cardDesc}>{service.description}</p>
          <div className={s.metaRow}>
            <span className={s.area}>
              <MapPin size={14} strokeWidth={2} />
              <span>{service.area}</span>
            </span>
            <ExternalLink size={14} strokeWidth={2} aria-hidden />
          </div>
          <div className={s.portalBtn}>
            <Button
              variant="primary"
              icon={ExternalLink}
              onClick={() => service.portalUrl && window.open(service.portalUrl, "_blank", "noopener,noreferrer")}
            >
              Open official portal
            </Button>
          </div>
          <p className={s.portalNote}>Paying here is not connected yet.</p>
        </div>
      </article>
    );
  }

  return (
    <article className={s.card} data-testid="service-card" data-service-id={service.id}>
      <div className={s.cardMedia}>
        {service.image ? <img src={service.image} alt="" /> : null}
        <span className={s.demoOnCard}><DemoPill /></span>
      </div>
      <div className={s.cardBody}>
        <h3 className={s.cardTitle}>{service.name}</h3>
        <p className={s.cardDesc}>{service.description}</p>
        <div className={s.metaRow}>
          <span className={s.area}>
            <MapPin size={14} strokeWidth={2} />
            <span>{service.area}</span>
          </span>
          <span className={s.rating}>
            <Star size={14} />
            {service.rating.toFixed(1)}
            <span style={{ fontWeight: 450, color: "var(--text-3)" }}>({service.reviewCount})</span>
          </span>
        </div>
        <div className={s.cardFoot}>
          {service.priceFromAed != null && (
            <span className={s.priceFrom}>
              From AED {service.priceFromAed}
              {service.priceUnit ? ` ${service.priceUnit}` : ""}
            </span>
          )}
          <button type="button" className={s.estimate} onClick={() => onEstimate(service.name)}>
            Estimate
          </button>
        </div>
      </div>
    </article>
  );
}

export function ServicesView() {
  const { setScreen, setDraft } = useApp();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CategoryChip>("all");

  const visible = useMemo(
    () => filterServices(DEMO_SERVICES, query, category),
    [query, category],
  );

  const askDubaiIo = (prefill?: string) => {
    if (prefill) setDraft(`I need an estimate for ${prefill}`);
    setScreen("assistant");
  };

  return (
    <div className={s.page} data-testid="services-view">
      <header className={s.toolbar}>
        <div className={s.toolbarSearch}>
          <SearchField
            placeholder="Search services, e.g. laundry, AC repair, DEWA…"
            value={query}
            onChange={setQuery}
          />
        </div>
        <span className={s.location}>
          <MapPin size={16} strokeWidth={ICON.strokeWidth} />
          Dubai
        </span>
        <IconButton icon={MoreHorizontal} label="More options" />
      </header>

      <div className={s.scroll}>
        <div className={s.layout}>
          <div className={s.main}>
            <header className={s.head}>
              <div className={s.headRow}>
                <h1>Services</h1>
                <DemoPill label="Demo data" />
              </div>
              <p className={s.lede}>
                Find trusted local services in Dubai. Real people, real recommendations.
              </p>
            </header>

            <div className={s.chips} role="tablist" aria-label="Categories">
              {CATEGORY_CHIPS.map(({ id, label }) => {
                const I = CHIP_ICON[id];
                const active = category === id;
                return (
                  <button
                    key={id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    className={`${s.chip} ${active ? s.chipActive : ""}`}
                    data-testid={`category-${id}`}
                    onClick={() => setCategory(id)}
                  >
                    <I size={16} strokeWidth={2} />
                    {label}
                  </button>
                );
              })}
            </div>

            {visible.length === 0 ? (
              <p className={s.empty} role="status">No services match your search. Try another category or keyword.</p>
            ) : (
              <div className={s.grid}>
                {visible.map((svc) => (
                  <ServiceCard key={svc.id} service={svc} onEstimate={(name) => askDubaiIo(name)} />
                ))}
              </div>
            )}
          </div>

          <aside className={s.rail} aria-label="Your activity">
            <section className={s.railPanel}>
              <div className={s.railHead}>
                <h2>
                  Your requests
                  <DemoPill label="Demo data" />
                </h2>
                <button type="button" className={s.viewAll}>View all</button>
              </div>
              <ul className={s.reqList}>
                {DEMO_REQUESTS.map((r) => (
                  <li key={r.id} className={s.reqItem} data-testid="service-request">
                    <span className={s.reqIcon}><Wrench size={16} strokeWidth={2} /></span>
                    <div className={s.reqBody}>
                      <div className={s.reqTitle}>{r.title}</div>
                      <div className={s.reqMeta}>{r.at}</div>
                      <span
                        className={`${s.status} ${
                          r.tone === "waiting" ? s.statusWaiting : r.tone === "review" ? s.statusReview : s.statusDraft
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <section className={`${s.railPanel} ${s.askPanel}`}>
              <h2 className={s.cardTitle} style={{ marginBottom: 8 }}>Need something else?</h2>
              <p>Tell Dubai-io what you need and we&apos;ll help you find the right option.</p>
              <div className={s.askBtn}>
                <Button variant="secondary" icon={MessageCircle} onClick={() => askDubaiIo()}>
                  Ask Dubai-io
                </Button>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

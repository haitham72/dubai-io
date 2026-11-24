// One compact flight result row: airline, times, price, Add to calendar, Select → confirm.
import { useState } from "react";
import { CalendarPlus, Check, ChevronRight } from "lucide-react";
import { ICON } from "../../ui";
import { actions } from "../../store";
import type { Flight } from "../../types";
import { addMinutes, cityName, parseDuration, toISO } from "./data";
import { cabinLabel, flightDate } from "./format";
import { flightUi } from "./ui";
import s from "./flights.module.css";

function initials(airline: string) {
  return airline.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

/** `hideDate`: every row departs the same day (e.g. a trip plan's results), so the date column is left out. */
export function FlightRow({ f, query, hideDate }: { f: Flight; query: { depart: string }; hideDate?: boolean }) {
  const [added, setAdded] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [booked, setBooked] = useState(false);

  const start = toISO(query.depart, f.fromTime);
  const end = addMinutes(start, parseDuration(f.duration) || 180);

  const addToCalendar = () => {
    actions.addEvent({
      calendar: "flights",
      title: `${f.fromCode} → ${f.toCode} · ${f.flightNo}`,
      start,
      end,
    });
    setAdded(true);
    window.setTimeout(() => setAdded(false), 3000);
  };

  const confirmBooking = () => {
    flightUi.addBooking({
      airline: f.airline,
      route: `${f.fromCode} → ${f.toCode}`,
      date: flightDate(f.date),
      status: "Upcoming",
    });
    setBooked(true);
  };

  return (
    <div className={expanded ? s.rowExpanded : s.row}>
      <button className={s.rowMain} onClick={() => setExpanded((v) => !v)} aria-expanded={expanded}>
        <span className={s.airlineMark} aria-hidden>{initials(f.airline)}</span>
        <span className={s.rowAirline}>
          <strong>{f.airline}</strong>
          <small>{f.flightNo}</small>
        </span>
        {!hideDate && <span className={s.rowDate}>{flightDate(f.date)}</span>}
        <span className={s.rowLeg}>
          <strong>{f.fromCode}</strong>
          <small>{f.fromTime}</small>
        </span>
        <span className={s.rowDur}>
          <small>{f.duration}</small>
          <span className={s.rowArc} aria-hidden />
          <small className={s.stops}>{f.stops === 0 ? "Nonstop" : `${f.stops} stop`}</small>
        </span>
        <span className={s.rowLeg}>
          <strong>{f.toCode}</strong>
          <small>{f.toTime}</small>
        </span>
        <span className={s.rowPrice}>
          {f.bestPrice && <span className={s.best}>Best price</span>}
          <strong>AED {f.price.toLocaleString()}</strong>
          <small>{cabinLabel(f.cabin)}</small>
        </span>
        <ChevronRight size={16} strokeWidth={ICON.strokeWidth} />
      </button>

      {expanded && (
        <div className={s.rowDetail}>
          <div className={s.rowDetailText}>
            {booked
              ? `Booked — ${f.airline} ${f.flightNo} now shows in My Bookings.`
              : `${f.airline} ${f.flightNo} · ${cityName(f.fromCode)} to ${cityName(f.toCode)} · ${flightDate(f.date)}, departs ${f.fromTime}, arrives ${f.toTime}.`}
          </div>
          <div className={s.rowActions}>
            <button className={s.ghostBtn} onClick={addToCalendar} disabled={added}>
              {added ? <Check size={16} strokeWidth={2} /> : <CalendarPlus size={16} strokeWidth={2} />}
              {added ? "Added to calendar" : "Add to calendar"}
            </button>
            {!booked && (
              <button className={s.primaryBtn} onClick={confirmBooking}>
                Select this flight
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

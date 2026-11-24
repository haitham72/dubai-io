// Flights sidebar: title, search, New Booking, My Bookings, Quick Search, Popular.
import { useState } from "react";
import { ArrowRightLeft, ChevronRight, Plane, Plus } from "lucide-react";
import { ICON, SearchField, SectionTitle, SidebarHeader } from "../../ui";
import { flightDate } from "./format";
import { DESTINATIONS } from "./data";
import { flightUi, useFlightsUi } from "./ui";
import s from "./flights.module.css";

export function FlightsSidebar() {
  const [q, setQ] = useState("");
  const trip = useFlightsUi((u) => u.trip);
  const bookings = useFlightsUi((u) => u.bookings);
  const needle = q.trim().toLowerCase();

  const shownBookings = bookings.filter(
    (b) =>
      !needle ||
      `${b.airline} ${b.route} ${flightDate(b.date)}`.toLowerCase().includes(needle),
  );
  const shownPopular = DESTINATIONS.filter(
    (d) => !needle || d.name.toLowerCase().includes(needle) || d.code.toLowerCase().includes(needle),
  );

  return (
    <>
      <SidebarHeader title="Flights" />
      <div className={s.sideBody}>
        <SearchField placeholder="Search flights, bookings, airlines..." value={q} onChange={setQ} />

        <button className={s.newBooking} onClick={() => flightUi.newSearch()}>
          <span className={s.newBookingIcon}><Plus {...ICON} /></span>
          <span className={s.newBookingText}>
            <strong>New Booking</strong>
            <small>Search and book your next trip</small>
          </span>
          <ChevronRight size={16} strokeWidth={ICON.strokeWidth} />
        </button>

        <SectionTitle action="View all" onAction={() => setQ("")}>My Bookings</SectionTitle>
        <div className={s.bookings}>
          {shownBookings.map((b) => (
            <button key={b.id} className={s.booking} onClick={() => setQ(b.route.split(" ")[0])}>
              <span className={s.airlineMark}><Plane {...ICON} /></span>
              <span className={s.bookingBody}>
                <strong>{b.airline}</strong>
                <small>{b.route} · {flightDate(b.date)}</small>
              </span>
              <span className={b.status === "Confirmed" ? s.pillConfirmed : s.pillUpcoming}>{b.status}</span>
            </button>
          ))}
          {shownBookings.length === 0 && <div className={s.muted}>No bookings match.</div>}
        </div>

        <SectionTitle>Quick Search</SectionTitle>
        <div className={s.quick}>
          <button
            className={trip === "return" ? s.quickActive : s.quickBtn}
            onClick={() => flightUi.request({ trip: "return" })}
          >
            <ArrowRightLeft size={16} strokeWidth={ICON.strokeWidth} />
            <span><strong>Return Trip</strong><small>Book a round trip</small></span>
            <ChevronRight size={16} strokeWidth={ICON.strokeWidth} />
          </button>
          <button
            className={trip === "oneway" ? s.quickActive : s.quickBtn}
            onClick={() => flightUi.request({ trip: "oneway" })}
          >
            <Plane size={16} strokeWidth={ICON.strokeWidth} />
            <span><strong>One Way</strong><small>Book a single trip</small></span>
            <ChevronRight size={16} strokeWidth={ICON.strokeWidth} />
          </button>
        </div>

        <SectionTitle>Popular</SectionTitle>
        <div className={s.popular}>
          {shownPopular.map((d) => (
            <button
              key={d.code}
              className={s.popularRow}
              onClick={() => flightUi.request({ to: d.code, search: true })}
            >
              <img src={d.photo} alt={d.name} loading="lazy" />
              <span className={s.popularBody}>
                <strong>{d.name}</strong>
                <small>Flights from {d.code}</small>
              </span>
              <ChevronRight size={16} strokeWidth={ICON.strokeWidth} />
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

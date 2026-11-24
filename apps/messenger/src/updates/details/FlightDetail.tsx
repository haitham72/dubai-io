import { useState, type ReactNode } from "react";
import { CalendarPlus, ChevronRight, Plane } from "lucide-react";
import { cabinLabel, flightDate, passengerLabel } from "../../screens/flights/format";
import { actions } from "../../store";
import type { Flight, TaskResult } from "../../types";
import { Badge, Button, ICON } from "../../ui";
import type { Notify } from "./Detail";
import s from "../updates.module.css";

function minutes(time: string) {
  const match = time.match(/^(\d{1,2}):(\d{2})(?:\s*(AM|PM))?$/i);
  if (!match) return null;
  let hour = Number(match[1]);
  const minute = Number(match[2]);
  if (minute > 59 || (match[3] ? hour < 1 || hour > 12 : hour > 23)) return null;
  if (match[3]) hour = hour % 12 + (match[3].toUpperCase() === "PM" ? 12 : 0);
  return hour * 60 + minute;
}
function calendarTimes(date: string, flight: Flight) {
  const departure = minutes(flight.fromTime);
  const duration = flight.duration.match(/^(?:(\d+)h)?\s*(?:(\d+)m)?$/);
  if (departure === null || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !duration || (!duration[1] && !duration[2])) return null;
  // The demo has no airport timezone metadata: retain departure-local wall time for both endpoints.
  const start = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(start.getTime())) return null;
  start.setUTCMinutes(departure);
  const end = new Date(start.getTime() + (Number(duration[1] ?? 0) * 60 + Number(duration[2] ?? 0)) * 60_000);
  return { start: start.toISOString().slice(0, 19), end: end.toISOString().slice(0, 19) };
}
export function FlightDetail({ result, notify, actions: controls }: {
  result: Extract<TaskResult, { type: "flight" }>; notify: Notify; actions: ReactNode;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [added, setAdded] = useState<string[]>([]);
  return <div className={s.flightContent}>
    {result.flights.length === 0 && <p className={s.empty}>No flights were returned. View all flights to search again.</p>}
    {result.flights.map(flight => <div className={s.flightRow} key={flight.id}>
      <div className={s.airline}><span className={s.airlineInitial}>{flight.airlineLogo ? <img src={flight.airlineLogo} alt="" /> : flight.airline.charAt(0)}</span><span><strong>{flight.airline}</strong><small>{flight.flightNo}</small></span></div>
      <span className={s.flightDate}>{flightDate(flight.date)}</span>
      <span className={s.airport}><strong>{flight.fromCode}</strong><small>{flight.fromTime}</small></span>
      <span className={s.duration}><small>{flight.duration} · {flight.stops === 0 ? "Non-stop" : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}</small><span className={s.routeLine}><Plane {...ICON} /></span></span>
      <span className={s.airport}><strong>{flight.toCode}</strong><small>{flight.toTime}</small></span>
      <span className={s.fare}>{flight.bestPrice && <Badge tone="muted">Best price</Badge>}<strong>{flight.currency} {flight.price.toLocaleString()}</strong><small>{cabinLabel(flight.cabin)}</small></span>
      <button className={s.flightExpand} aria-label={`Flight details for ${flight.flightNo}`} aria-expanded={expanded === flight.id} onClick={() => setExpanded(expanded === flight.id ? null : flight.id)}><ChevronRight {...ICON} /></button>
      <div className={s.flightCalendar}><Button icon={CalendarPlus} variant="ghost" onClick={() => {
        if (added.includes(flight.id)) { notify("This flight is already in your calendar"); return; }
        const times = calendarTimes(result.query.depart, flight);
        if (!times) { notify("This flight has no valid departure date or duration"); return; }
        actions.addEvent({ ...times, calendar: "flights", title: `${flight.airline} ${flight.flightNo} · ${flight.fromCode} → ${flight.toCode}`,
          location: `${flight.fromCode} → ${flight.toCode}`, notes: `${cabinLabel(flight.cabin)} · ${flight.duration}. Times use departure-local time; confirm with airline.` });
        setAdded(ids => [...ids, flight.id]); notify("Flight added to calendar");
      }}>{added.includes(flight.id) ? "Added to calendar" : "Add to calendar"}</Button></div>
      {expanded === flight.id && <p className={s.flightNote}>{flight.flightNo} · {passengerLabel(result.query.passengers)} · {cabinLabel(flight.cabin)} · Departure {flightDate(result.query.depart)}. Demo fare; confirm availability with the airline.</p>}
    </div>)}
    {controls}
  </div>;
}

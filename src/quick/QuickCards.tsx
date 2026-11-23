// Cards that open over the current screen instead of switching to a workspace: flight results from a trip
// plan's "All flights", and a mail draft (e.g. the plan's leave email). Desktop: a centred card; phone: a
// bottom sheet. Rendered once by the desktop shell and once by the phone layout.
import { useEffect, useMemo, useState } from "react";
import { Plane, Send, X } from "lucide-react";
import { Backdrop, ICON, Segmented, Spinner } from "../ui";
import { actions, useStore } from "../store";
import { searchFlights } from "../api";
import type { Flight, FlightQuery } from "../types";
import { FlightRow } from "../screens/flights/FlightRow";
import { cabinLabel, flightDates, passengerLabel } from "../screens/flights/format";
import { mail, useMail } from "../screens/mail/state";
import s from "./quick.module.css";

export function QuickCards() {
  const quick = useStore((st) => st.quick);
  const onMail = useStore((st) => st.screen === "mail");
  const toast = useMail().toast;
  return (
    <>
      {quick && (
        <Backdrop backdrop={s.backdrop} onClose={actions.closeQuick}>
          <div className={s.card} role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            {quick.kind === "flights"
              ? <FlightsCard key={JSON.stringify(quick.query)} query={quick.query} initial={quick.flights ?? []} />
              : <DraftCard key={quick.id} id={quick.id} />}
          </div>
        </Backdrop>
      )}
      {/* Mail's own toast shows inside Mail; elsewhere (a draft sent from a card) it shows here. */}
      {!onMail && toast && <div className={s.toast} role="status">{toast}</div>}
    </>
  );
}

function Head({ title, sub }: { title: string; sub: string }) {
  return (
    <header className={s.head}>
      <span><strong>{title}</strong><small>{sub}</small></span>
      <button className={s.close} aria-label="Close" onClick={actions.closeQuick}><X {...ICON} /></button>
    </header>
  );
}

const minutes = (d: string) => {
  const m = d.match(/(?:(\d+)h)?\s*(?:(\d+)m)?/);
  return m ? Number(m[1] ?? 0) * 60 + Number(m[2] ?? 0) : 0;
};

/** Every result for the plan's search, newest search wins; the plan's own top picks show while it loads. */
function FlightsCard({ query, initial }: { query: FlightQuery; initial: Flight[] }) {
  const [flights, setFlights] = useState<Flight[]>(initial);
  const [status, setStatus] = useState<"loading" | "done" | "error">("loading");
  const [sort, setSort] = useState<"price" | "time">("price");
  useEffect(() => {
    let live = true;
    searchFlights(query)
      .then((list) => { if (live) { setFlights(list.length ? list : initial); setStatus("done"); } })
      .catch(() => { if (live) setStatus(initial.length ? "done" : "error"); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const sorted = useMemo(() => [...flights].sort((a, b) =>
    sort === "price" ? a.price - b.price : minutes(a.duration) - minutes(b.duration) || a.price - b.price), [flights, sort]);
  return (
    <>
      <Head title={`${query.from} → ${query.to}`}
        sub={`${flightDates(query.depart, query.return || undefined)} · ${passengerLabel(query.passengers)} · ${cabinLabel(query.cabin)}`} />
      <div className={s.tools}>
        <Segmented<"price" | "time"> options={[{ value: "price", label: "Cheapest" }, { value: "time", label: "Fastest" }]}
          value={sort} onChange={setSort} />
        <span>{status === "loading" ? <><Spinner />Searching…</> : `${sorted.length} flights`}</span>
      </div>
      <div className={s.body}>
        {status === "error" && !sorted.length && <p className={s.empty}>Flight search is unavailable right now.</p>}
        {status === "done" && !sorted.length && <p className={s.empty}><Plane {...ICON} />No flights found for these dates.</p>}
        {sorted.map((f) => <FlightRow key={f.id} f={f} query={{ depart: query.depart }} hideDate />)}
      </div>
    </>
  );
}

/** A saved draft, editable in place. Send goes through Mail (the button is the confirmation); nothing leaves otherwise. */
function DraftCard({ id }: { id: string }) {
  const draft = useStore((st) => st.mailDrafts.find((d) => d.id === id));
  const [to, setTo] = useState(draft?.to ?? "");
  const [subject, setSubject] = useState(draft?.subject ?? "");
  const [body, setBody] = useState(draft?.body ?? "");
  if (!draft) {
    return <><Head title="Draft" sub="Already sent or deleted" /><p className={s.empty}>This draft is no longer in Mail › Drafts.</p></>;
  }
  const save = () => { mail.saveDraft({ to, subject, body, draftId: id }); actions.closeQuick(); };
  return (
    <form className={s.draft} onSubmit={(e) => { e.preventDefault(); void mail.send(to, subject, body, id); actions.closeQuick(); }}>
      <Head title="Draft" sub={draft.by === "mirsal" ? "Written by Mirsal · not sent" : "Not sent"} />
      <label>To<input type="email" required value={to} onChange={(e) => setTo(e.target.value)} /></label>
      <label>Subject<input required value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
      <textarea required aria-label="Email message" value={body} onChange={(e) => setBody(e.target.value)} />
      <footer>
        <button type="button" className={s.secondary} onClick={save}>Save draft</button>
        <button type="submit" className={s.primary}><Send size={16} strokeWidth={2} />Send</button>
      </footer>
    </form>
  );
}

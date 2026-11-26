// The six Settings tabs. Each holds its own state (initialised from ../data) and reports actions through `say` (toast).
import { useState } from "react";
import {
  Ban, ChevronDown, Cpu, Download, Globe, KeyRound, Languages, LogOut, Mail, MapPin, Moon, ShieldCheck, Trash2, Fingerprint,
  type LucideIcon,
} from "lucide-react";
import { Avatar, Button, ICON, Segmented } from "../../ui";
import { actions, useStore } from "../../store";
import { completePairingCode, googleSignInStartUrl } from "../../apiclient/chatCore";
import { applyFrost, loadFrost } from "../../frost";
import { Group, Row, ToggleRow } from "../shared";
import MemorySettings from "./MemorySettings";
import { apps, me, responseStyles, sessions, toggleGroups } from "../data";
import p from "../profile.module.css";
import st from "./settings.module.css";

export interface TabProps { say: (text: string) => void }

/* ---------- helpers ---------- */

function useToggles(group: keyof typeof toggleGroups) {
  const [on, setOn] = useState<Record<string, boolean>>(() => Object.fromEntries(toggleGroups[group].map((t) => [t.id, t.on])));
  const set = (id: string, v: boolean) => setOn((o) => ({ ...o, [id]: v }));
  return [on, set] as const;
}

function ToggleList({ group, say }: { group: keyof typeof toggleGroups } & TabProps) {
  const [on, set] = useToggles(group);
  return <>
    {toggleGroups[group].map((t) => (
      <ToggleRow key={t.id} label={t.label} detail={t.detail} on={on[t.id]}
        onChange={(v) => { set(t.id, v); say(`${t.label} ${v ? "on" : "off"}`); }} />
    ))}
  </>;
}

function Select({ value, options, onChange, label }: { value: string; options: string[]; onChange: (v: string) => void; label: string }) {
  return (
    <span className={p.selectWrap}>
      <select className={p.select} value={value} aria-label={label} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => <option key={o}>{o}</option>)}
      </select>
      <ChevronDown size={16} strokeWidth={ICON.strokeWidth} />
    </span>
  );
}

/* ---------- Account ---------- */

const sessionIcons: LucideIcon[] = [KeyRound, ShieldCheck, Fingerprint, Mail];

export function AccountTab({ say }: TabProps) {
  const [language, setLanguage] = useState(me.language);
  const [region, setRegion] = useState("United Arab Emirates");
  const [dateFmt, setDateFmt] = useState("DD/MM/YYYY");
  const [pairCode, setPairCode] = useState("");
  const [pairing, setPairing] = useState(false);

  async function handlePair() {
    const clean = pairCode.trim().toUpperCase();
    if (!clean) {
      say("Enter the 6-character pairing code from Dubai-io");
      return;
    }
    setPairing(true);
    try {
      const out = await completePairingCode(clean);
      await actions.signInWithSessionToken(out.session_token, { displayName: out.display_name });
      setPairCode("");
      say(out.display_name ? `Paired as ${out.display_name}` : "Device paired");
    } catch (err) {
      say(err instanceof Error && err.message ? err.message : "Pairing code invalid or expired");
    } finally {
      setPairing(false);
    }
  }

  return <>
    <div className={st.summary}>
      <Avatar src={me.avatar} size={56} online />
      <span className={p.twoLine}>
        <strong className={st.summaryName}>{me.fullName}</strong>
        <small>{me.email} · {me.handle}</small>
      </span>
      <Button onClick={() => actions.openModal("profile")}>Edit profile</Button>
    </div>

    <Group title="Sign-in & security">
      <Row icon={KeyRound} label="Continue with Google" value="Same account as Quest and Community"
        onClick={() => { window.location.href = googleSignInStartUrl(`${window.location.origin}/`); }} />
      <Row icon={KeyRound} label="Pair with PC code">
        <span className={p.editActions}>
          <input
            type="text"
            className={p.editField}
            value={pairCode}
            onChange={(e) => setPairCode(e.target.value.toUpperCase())}
            placeholder="6-char code"
            aria-label="Pair with PC code"
            maxLength={6}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            style={{ width: 120, letterSpacing: "0.1em", fontFamily: "ui-monospace, monospace" }}
          />
          <Button disabled={pairing} onClick={() => { void handlePair(); }}>
            {pairing ? "Pairing..." : "Pair"}
          </Button>
        </span>
      </Row>
      {sessions.map((x, i) => (
        <Row key={x.label} icon={sessionIcons[i % sessionIcons.length]} label={x.label} value={x.value} action={x.action}
          onClick={() => say(`${x.label}: we'll email you a secure link`)} />
      ))}
    </Group>

    <Group title="Language & region">
      <Row icon={Languages} label="App language">
        <Select label="App language" value={language} options={["English", "العربية", "Français", "Español"]}
          onChange={(v) => { setLanguage(v); say(`Language set to ${v}`); }} />
      </Row>
      <Row icon={MapPin} label="Region">
        <Select label="Region" value={region} options={["United Arab Emirates", "Saudi Arabia", "Egypt", "United Kingdom"]}
          onChange={(v) => { setRegion(v); say(`Region set to ${v}`); }} />
      </Row>
      <Row icon={Globe} label="Date format">
        <Select label="Date format" value={dateFmt} options={["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]}
          onChange={(v) => { setDateFmt(v); say(`Dates will show as ${v}`); }} />
      </Row>
    </Group>

    <Group title="Danger zone">
      <Row icon={LogOut} label={<span className={st.danger}>Sign out of all devices</span>}
        onClick={() => say("Signed out of 3 other devices")} />
      <Row icon={Trash2} label={<span className={st.danger}>Delete account</span>}
        onClick={() => say("Account deletion is disabled in this demo")} />
    </Group>
  </>;
}

/* ---------- Appearance ---------- */

type Theme = "light" | "system" | "dark";
const themes: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "system", label: "System" },
  { value: "dark", label: "Dark" },
];

/** A tiny drawing of the app (nav + chat bubbles) in the given theme. */
function MiniUI({ dark }: { dark?: boolean }) {
  return (
    <span className={`${st.mini} ${dark ? st.miniDark : ""}`}>
      <span className={st.miniNav}><i /><i /><i /></span>
      <span className={st.miniMain}>
        <span className={st.miniIn} />
        <span className={st.miniOut} />
        <span className={`${st.miniIn} ${st.miniShort}`} />
        <span className={st.miniBar} />
      </span>
    </span>
  );
}

const wallpapers = [
  { id: "plain", label: "Plain", cls: st.wpPlain },
  { id: "sky", label: "Sky", cls: st.wpSky },
  { id: "lavender", label: "Lavender", cls: st.wpLavender },
  { id: "mist", label: "Mist", cls: st.wpMist },
  { id: "dots", label: "Dots", cls: st.wpDots },
  { id: "dusk", label: "Dusk", cls: st.wpDusk },
];

type TextSize = "small" | "default" | "large";
const textSizes: { value: TextSize; label: string }[] = [
  { value: "small", label: "Small" }, { value: "default", label: "Default" }, { value: "large", label: "Large" },
];

export function AppearanceTab({ say }: TabProps) {
  const theme = useStore((st) => st.theme);
  const [size, setSize] = useState<TextSize>("default");
  const [wallpaper, setWallpaper] = useState("sky");
  const [reduceMotion, setReduceMotion] = useState(false);
  const [frost, setFrost] = useState(loadFrost);
  const wp = wallpapers.find((w) => w.id === wallpaper) ?? wallpapers[0];

  const tuneFrost = (patch: Partial<typeof frost>) => {
    setFrost((f) => {
      const next = { ...f, ...patch };
      applyFrost(next);
      return next;
    });
  };

  const pickTheme = (t: Theme) => {
    actions.setTheme(t);
    say(t === "light" ? "Light theme on" : t === "dark" ? "Dark theme on" : "Following your system theme");
  };

  return <>
    <Group title="Theme">
      <div className={st.themes}>
        <div className={p.themeCards}>
          {themes.map((t) => (
            <button key={t.value} className={`${p.themeCard} ${st.themeCard}`} aria-pressed={theme === t.value} onClick={() => pickTheme(t.value)}>
              {t.value === "system"
                ? <span className={st.split}><MiniUI /><MiniUI dark /></span>
                : <MiniUI dark={t.value === "dark"} />}
              <span className={st.themeFoot}>
                <span className={p.themeLabel}>{t.label}</span>
                <span className={`${st.radio} ${theme === t.value ? st.radioOn : ""}`} />
              </span>
            </button>
          ))}
        </div>
      </div>
    </Group>

    <Group title="Frosted glass">
      <div className={st.frostRow}>
        <span>Solidity</span>
        <input type="range" min={50} max={100} value={Math.round(frost.opacity * 100)}
          aria-label="Frost solidity"
          onChange={(e) => tuneFrost({ opacity: Number(e.target.value) / 100 })} />
        <span className={st.frostVal}>{Math.round(frost.opacity * 100)}%</span>
      </div>
      <div className={st.frostRow}>
        <span>Blur</span>
        <input type="range" min={10} max={60} value={frost.blur}
          aria-label="Frost blur"
          onChange={(e) => tuneFrost({ blur: Number(e.target.value) })} />
        <span className={st.frostVal}>{frost.blur}px</span>
      </div>
    </Group>

    <Group title="Chats">
      <Row label="Text size">
        <Segmented options={textSizes} value={size} onChange={(v) => { setSize(v); say(`Text size: ${v}`); }} />
      </Row>
      <div className={st.wpBlock}>
        <span className={p.rowLabel}>Chat wallpaper</span>
        <div className={st.swatches}>
          {wallpapers.map((w) => (
            <button key={w.id} className={`${st.swatch} ${w.cls}`} aria-pressed={wallpaper === w.id} aria-label={w.label} title={w.label}
              onClick={() => { setWallpaper(w.id); say(`Wallpaper: ${w.label}`); }} />
          ))}
        </div>
        <div className={`${st.preview} ${wp.cls} ${st[size]}`} aria-label="Chat preview">
          <span className={st.bubbleIn}>Are you free this weekend?</span>
          <span className={st.bubbleOut}>Yes! Let's go to the beach.</span>
        </div>
      </div>
      <ToggleRow label="Reduce motion" detail="Fewer animations and transitions" on={reduceMotion}
        onChange={(v) => { setReduceMotion(v); say(v ? "Animations reduced" : "Animations restored"); }} />
    </Group>
  </>;
}

/* ---------- Notifications ---------- */

const times = ["8:00 PM", "9:00 PM", "10:00 PM", "11:00 PM", "12:00 AM", "6:00 AM", "7:00 AM", "8:00 AM", "9:00 AM"];

export function NotificationsTab({ say }: TabProps) {
  const [quiet, setQuiet] = useState(true);
  const [from, setFrom] = useState("10:00 PM");
  const [to, setTo] = useState("7:00 AM");

  return <>
    <Group title="Alerts">
      <ToggleList group="notifications" say={say} />
    </Group>
    <Group title="Schedule">
      <ToggleRow label="Quiet hours" detail="Silence notifications overnight, calls from favourites still ring" on={quiet}
        onChange={(v) => { setQuiet(v); say(v ? `Quiet hours ${from} – ${to}` : "Quiet hours off"); }} />
      {quiet && (
        <Row icon={Moon} label="Silent between">
          <span className={st.timeRange}>
            <Select label="From" value={from} options={times} onChange={(v) => { setFrom(v); say(`Quiet hours start at ${v}`); }} />
            <span className={st.to}>to</span>
            <Select label="To" value={to} options={times} onChange={(v) => { setTo(v); say(`Quiet hours end at ${v}`); }} />
          </span>
        </Row>
      )}
    </Group>
  </>;
}

/* ---------- Privacy ---------- */

export function PrivacyTab({ say }: TabProps) {
  return <>
    <Group title="Visibility & security">
      <ToggleList group="privacy" say={say} />
    </Group>
    <Group title="Your data">
      <Row icon={Ban} label="Blocked contacts" value="2" onClick={() => say("Blocked: Unknown +971 55 *** 0193, Promo Deals")} />
      <Row icon={Download} label="Download my data" value="Chats, media and settings" action="Request"
        onClick={() => say("We'll email your archive within 24 hours")} />
    </Group>
  </>;
}

/* ---------- Connected Apps ---------- */

export function AppsTab({ say }: TabProps) {
  const [linked, setLinked] = useState<Record<string, boolean>>(() => Object.fromEntries(apps.map((a) => [a.id, a.connected])));
  const count = Object.values(linked).filter(Boolean).length;

  return (
    <Group title={`${count} of ${apps.length} connected`}>
      {apps.map((a) => {
        const on = linked[a.id];
        return (
          <div key={a.id} className={p.row}>
            <span className={`${p.tile} ${on ? p.tileBlue : ""}`}>{a.name[0]}</span>
            <span className={p.twoLine}>{a.name}<small>{a.detail}</small></span>
            <button className={`${p.pill} ${on ? p.pillOn : ""}`} aria-pressed={on}
              onClick={() => { setLinked((l) => ({ ...l, [a.id]: !on })); say(on ? `${a.name} disconnected` : `${a.name} connected`); }}>
              {on ? "Connected" : "Connect"}
            </button>
          </div>
        );
      })}
    </Group>
  );
}

/* ---------- AI Preferences ---------- */

type Style = (typeof responseStyles)[number];

export function AiTab({ say }: TabProps) {
  const [style, setStyle] = useState<Style>("Balanced");

  return <>
    <Group title="Capabilities & permissions">
      <ToggleList group="ai" say={say} />
    </Group>
    <Group title="Responses">
      <Row label="Response style">
        <Segmented options={responseStyles.map((r) => ({ value: r, label: r }))} value={style}
          onChange={(v) => { setStyle(v); say(`Messenger will answer in a ${v.toLowerCase()} style`); }} />
      </Row>
      <Row icon={Cpu} label="Model" value="GPT-5 · Messenger default" onClick={() => say("Messenger picks the best model for each task")} />
    </Group>
    <MemorySettings />
  </>;
}

// Profile modal (R11): ten tabs, all with working fake content.
import { useState } from "react";
import {
  Bell, Calendar, ChevronDown, Cloud, Crown, Database, Globe, HardDrive, KeyRound, Languages, Laptop, Link2,
  Mail, MapPin, Monitor, Palette, Phone, ShieldCheck, Smartphone, Sparkles, Tablet, User, UserCircle,
} from "lucide-react";
import { ICON, Button } from "../ui";
import { actions, useStore } from "../store";
import {
  apps, billing, devices as seedDevices, me, plan, sessions, statuses, storage, toggleGroups, responseStyles,
  type DeviceKind, type Status,
} from "./data";
import { Group, Row, Shell, ToggleRow, useToast, type Tab } from "./shared";
import s from "./profile.module.css";

const tabs: (Tab & { sub: string })[] = [
  { id: "profile", label: "Profile", icon: UserCircle, sub: "Manage your personal information and account details." },
  { id: "account", label: "Account", icon: User, sub: "Sign-in, security and recovery." },
  { id: "subscription", label: "Subscription", icon: Crown, sub: "Your plan, usage this month and billing." },
  { id: "devices", label: "Devices", icon: Monitor, sub: "Where you're signed in to Mirsal." },
  { id: "storage", label: "Storage", icon: HardDrive, sub: "What's using your Mirsal Cloud space." },
  { id: "privacy", label: "Data & Privacy", icon: ShieldCheck, sub: "Control what others see and what Mirsal keeps." },
  { id: "apps", label: "Connected Apps", icon: Link2, sub: "Services Mirsal can read from or send to." },
  { id: "notifications", label: "Notifications", icon: Bell, sub: "Choose what reaches you, and when." },
  { id: "appearance", label: "Appearance", icon: Palette, sub: "Theme and text size." },
  { id: "ai", label: "AI Preferences", icon: Sparkles, sub: "How Mirsal AI works for you." },
];

// Module-level so edits survive closing and reopening the modal during the session.
let saved = { name: me.name, bio: me.bio, status: "online" as Status };

export function ProfileModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState("profile");
  const [toast, notify] = useToast();
  const current = tabs.find((t) => t.id === tab)!;
  return (
    <Shell title="Profile" tabs={tabs} active={tab} onTab={setTab} onClose={onClose}
      heading={current.label} subheading={current.sub} toast={toast}>
      {tab === "profile" && <ProfileTab notify={notify} />}
      {tab === "account" && <AccountTab notify={notify} />}
      {tab === "subscription" && <SubscriptionTab notify={notify} />}
      {tab === "devices" && <DevicesTab notify={notify} />}
      {tab === "storage" && <StorageTab notify={notify} />}
      {tab === "privacy" && <Toggles group="privacy" extra={<Group title="Your data">
        <Row icon={Database} label="Download my data" onClick={() => notify("We'll email you a download link within 24 hours.")} />
        <Row icon={Globe} label="Delete chat history older than 1 year" onClick={() => notify("Older history scheduled for deletion.")} />
      </Group>} />}
      {tab === "apps" && <AppsTab notify={notify} />}
      {tab === "notifications" && <Toggles group="notifications" />}
      {tab === "appearance" && <AppearanceTab notify={notify} />}
      {tab === "ai" && <AiTab notify={notify} />}
    </Shell>
  );
}

type Notify = { notify: (text: string) => void };

function ProfileTab({ notify }: Notify) {
  const [profile, setProfile] = useState(saved);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(profile);
  const update = (next: typeof profile) => { saved = next; setProfile(next); };
  const statusLabel = statuses.find((x) => x.value === profile.status)!.label;
  return <>
    <div className={s.hero}>
      <span className={s.heroAvatar}><img src={me.avatar} alt="" /><span className={`${s.heroDot} ${s[profile.status]}`} /></span>
      <div className={s.heroText}>
        {editing ? <>
          <input className={s.editField} aria-label="Display name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          <input className={s.editField} aria-label="Bio" value={draft.bio} onChange={(e) => setDraft({ ...draft, bio: e.target.value })} />
        </> : <>
          <h4 className={s.heroName}>{profile.name}</h4>
          <span className={s.heroStatus}><span className={`${s.dot} ${s[profile.status]}`} />{statusLabel}</span>
          <p className={s.heroBio}>{profile.bio}</p>
        </>}
      </div>
      {editing
        ? <div className={s.editActions}>
            <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
            <Button variant="primary" onClick={() => { update({ ...profile, name: draft.name.trim() || profile.name, bio: draft.bio.trim() }); setEditing(false); notify("Profile updated."); }}>Save</Button>
          </div>
        : <Button onClick={() => { setDraft(profile); setEditing(true); }}>Edit</Button>}
    </div>
    <Group>
      <Row icon={User} label="Full name" value={me.fullName} onClick={() => notify("Full name can be changed from Account.")} />
      <Row icon={Mail} label="Email" value={me.email} onClick={() => notify("Verification sent to your new email.")} />
      <Row icon={Phone} label="Phone" value={me.phone} onClick={() => notify("We'll text a code to confirm a new number.")} />
      <Row icon={MapPin} label="Location" value={me.location} onClick={() => notify("Location updated from this device.")} />
      <Row icon={Calendar} label="Date of birth" value={me.birthday} onClick={() => notify("Date of birth is only visible to you.")} />
      <Row icon={Languages} label="Language" value={me.language} onClick={() => notify("العربية is also available.")} />
    </Group>
    <Group>
      <Row label={<span className={s.twoLine}>Status<small>This will be visible to your contacts.</small></span>}>
        <span className={s.selectWrap}>
          <span className={`${s.dot} ${s[profile.status]}`} />
          <select className={s.select} aria-label="Status" value={profile.status}
            onChange={(e) => { update({ ...profile, status: e.target.value as Status }); notify(`Status set to ${statuses.find((x) => x.value === e.target.value)!.label}.`); }}>
            {statuses.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
          </select>
          <ChevronDown size={16} strokeWidth={ICON.strokeWidth} />
        </span>
      </Row>
    </Group>
    <Group>
      <Row icon={UserCircle} label={<span className={s.twoLine}>About<small>{profile.bio || "Add a short bio"} · {me.joined}</small></span>}
        onClick={() => { setDraft(profile); setEditing(true); }} />
    </Group>
  </>;
}

function AccountTab({ notify }: Notify) {
  return <>
    <Group title="Sign-in">
      <Row icon={Mail} label="Mirsal ID" value={me.email} />
      <Row icon={User} label="Username" value={me.handle} onClick={() => notify("Usernames can be changed once every 30 days.")} />
      {sessions.map((x) => <Row key={x.label} icon={KeyRound} label={<span className={s.twoLine}>{x.label}<small>{x.value}</small></span>}
        action={x.action} onClick={() => notify(`${x.label}: we've sent a confirmation to your phone.`)} />)}
    </Group>
    <Group title="Danger zone">
      <Row label={<span className={s.pillDanger}>Sign out of all devices</span>} onClick={() => notify("Signed out everywhere except this Mac.")} />
      <Row label={<span className={s.pillDanger}>Delete account</span>} onClick={() => notify("Account deletion needs a confirmation from your phone.")} />
    </Group>
  </>;
}

function SubscriptionTab({ notify }: Notify) {
  return <>
    <div className={s.planCard}>
      <span className={s.planIcon}><Crown {...ICON} /></span>
      <div className={s.planText}><h4 className={s.planName}>{plan.name}</h4><p className={s.planMeta}>{plan.price} · {plan.renews}</p></div>
      <Button onClick={() => notify("Plan options opened.")}>Change plan</Button>
    </div>
    <Group title="Usage this month">
      <div className={s.meters}>
        {plan.usage.map((u) => <div key={u.label} className={s.meter}>
          <span className={s.meterHead}>{u.label}<strong>{u.used.toLocaleString()} / {u.total.toLocaleString()}</strong></span>
          <span className={s.track}><span className={s.fill} style={{ width: `${(u.used / u.total) * 100}%` }} /></span>
        </div>)}
      </div>
    </Group>
    <Group title="Billing history">
      {billing.map((b) => <Row key={b.id} label={<span className={s.twoLine}>{b.item}<small>{b.date}</small></span>}
        value={<>{b.amount} · <span className={s.paid}>{b.status}</span></>} onClick={() => notify(`Receipt for ${b.date} downloaded.`)} />)}
    </Group>
  </>;
}

const deviceIcons: Record<DeviceKind, typeof Laptop> = { laptop: Laptop, phone: Smartphone, tablet: Tablet, desktop: Monitor };
function DevicesTab({ notify }: Notify) {
  const [list, setList] = useState(seedDevices);
  return <Group title={`${list.length} devices`}>
    {list.map((d) => { const I = deviceIcons[d.kind]; return <Row key={d.id}
      label={<span className={s.twoLine}>{d.name}<small>{d.detail}</small></span>}
      value={d.current ? <span className={s.current}>This device</span> : d.active}>
      <span className={`${s.tile} ${d.current ? s.tileBlue : ""}`} style={{ order: -1 }}><I {...ICON} /></span>
      {!d.current && <button className={`${s.pill} ${s.pillDanger}`} onClick={() => { setList(list.filter((x) => x.id !== d.id)); notify(`Signed out of ${d.name}.`); }}>Sign out</button>}
    </Row>; })}
  </Group>;
}

function StorageTab({ notify }: Notify) {
  return <>
    <Group>
      <div className={s.storageHead}><strong>{storage.used} GB used</strong><span>of {storage.total} GB · Mirsal Cloud</span></div>
      <span className={`${s.track} ${s.storageBar}`}>
        {storage.categories.map((c) => <span key={c.id} className={`${s.fill} ${s[c.tone]}`} style={{ width: `${(c.size / storage.total) * 100}%` }} />)}
      </span>
    </Group>
    <Group title="Categories">
      {storage.categories.map((c) => <Row key={c.id} label={c.label} value={`${c.size} GB`} action="Review" onClick={() => notify(`Opening ${c.label.toLowerCase()} you can clean up.`)}>
        <span className={`${s.swatch} ${s[c.tone]}`} style={{ order: -1 }} />
      </Row>)}
    </Group>
    <Group>
      <Row icon={Cloud} label="Upgrade to 1 TB" action="AED 15 / mo" onClick={() => notify("Storage upgrade options opened.")} />
    </Group>
  </>;
}

function Toggles({ group, extra }: { group: keyof typeof toggleGroups; extra?: React.ReactNode }) {
  const [values, setValues] = useState(() => Object.fromEntries(toggleGroups[group].map((t) => [t.id, t.on])));
  return <>
    <Group>{toggleGroups[group].map((t) => <ToggleRow key={t.id} label={t.label} detail={t.detail} on={values[t.id]} onChange={(on) => setValues({ ...values, [t.id]: on })} />)}</Group>
    {extra}
  </>;
}

function AppsTab({ notify }: Notify) {
  const [state, setState] = useState(() => Object.fromEntries(apps.map((a) => [a.id, a.connected])));
  return <Group>
    {apps.map((a) => <Row key={a.id} label={<span className={s.twoLine}>{a.name}<small>{a.detail}</small></span>}>
      <span className={s.tile} style={{ order: -1 }}>{a.name[0]}</span>
      <button className={`${s.pill} ${state[a.id] ? s.pillOn : ""}`} onClick={() => {
        setState({ ...state, [a.id]: !state[a.id] }); notify(state[a.id] ? `${a.name} disconnected.` : `${a.name} connected.`);
      }}>{state[a.id] ? "Connected" : "Connect"}</button>
    </Row>)}
  </Group>;
}

const themes = [
  { id: "light", label: "Light" }, { id: "system", label: "System" }, { id: "dark", label: "Dark" },
] as const;
function AppearanceTab({ notify }: Notify) {
  const theme = useStore((st) => st.theme);
  const [size, setSize] = useState("Default");
  return <>
    <Group title="Theme">
      <div className={s.themeCards} style={{ padding: "var(--s-3)" }}>
        {themes.map((t) => <button key={t.id} className={s.themeCard} aria-pressed={theme === t.id}
          onClick={() => { actions.setTheme(t.id); notify(t.id === "system" ? "Following your system theme." : `${t.label} theme on.`); }}>
          <span className={s.themePreview} data-theme-preview={t.id}>
            <span style={{ background: t.id === "dark" ? "#0b0f17" : "#eef3fa" }} />
            <span style={{ background: t.id === "dark" ? "#111827" : t.id === "system" ? "linear-gradient(90deg, #ffffff 50%, #111827 50%)" : "#ffffff" }} />
          </span>
          <span className={s.themeLabel}>{t.label}</span>
        </button>)}
      </div>
    </Group>
    <Group title="Text size">
      {["Small", "Default", "Large"].map((x) => <Row key={x} label={x} value={size === x ? "✓" : ""} onClick={() => setSize(x)} />)}
    </Group>
  </>;
}

function AiTab({ notify }: Notify) {
  const [style, setStyle] = useState<string>("Balanced");
  return <>
    <Toggles group="ai" />
    <Group title="Response style">
      {responseStyles.map((x) => <Row key={x} label={x} value={style === x ? "✓" : ""} onClick={() => { setStyle(x); notify(`Mirsal AI will answer in a ${x.toLowerCase()} style.`); }} />)}
    </Group>
  </>;
}

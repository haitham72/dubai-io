// e& yearly renewal contract (demo) in English / Arabic, signed by typing "Haitham Mohamed" or "هيثم محمد".
import { useState } from "react";
import { BadgeCheck, Fingerprint } from "lucide-react";
import type { MessengerTask } from "../types";
import { Spinner } from "../ui";
import { esign, isArabic, isValidSignature, useEsign } from "./state";
import s from "./esign.module.css";

type Lang = "en" | "ar";

const copy = {
  en: {
    title: "Postpaid Plan Renewal Agreement",
    provider: "Service provider", providerV: "e& (formerly Etisalat)",
    customer: "Customer", customerV: "Haitham Mohamed Ibrahim",
    account: "Account no.", mobile: "Mobile number",
    plan: "Plan", planV: "Freedom Postpaid 300 · 5G",
    term: "Term", termV: "12 months · 1 Nov 2026 – 31 Oct 2027",
    fee: "Monthly fee", feeV: "AED 300 (incl. 5% VAT)",
    includes: "Includes", includesV: "50 GB data · 1,500 flexi minutes · e& TV Basic",
    terms: [
      "The plan renews for 12 months from the start date above.",
      "Early termination: remaining monthly fees up to a maximum of AED 600.",
      "Charges are billed monthly to the account above.",
      "Signed electronically with UAE PASS; an electronic signature has the same effect as a handwritten one.",
    ],
    signLabel: "Type your full name to sign", signHint: "Type Haitham Mohamed or هيثم محمد",
    signBtn: "Sign with UAE PASS", signed: "Signed with UAE PASS", demo: "Demo document",
  },
  ar: {
    title: "اتفاقية تجديد الباقة الآجلة",
    provider: "مزود الخدمة", providerV: "إي آند (اتصالات سابقاً)",
    customer: "العميل", customerV: "هيثم محمد إبراهيم",
    account: "رقم الحساب", mobile: "رقم الهاتف المتحرك",
    plan: "الباقة", planV: "فريدم الآجلة 300 · الجيل الخامس",
    term: "المدة", termV: "12 شهراً · 1 نوفمبر 2026 – 31 أكتوبر 2027",
    fee: "الرسوم الشهرية", feeV: "300 درهم (شاملة ضريبة القيمة المضافة 5%)",
    includes: "تشمل", includesV: "50 جيجابايت بيانات · 1,500 دقيقة مرنة · e& TV الأساسية",
    terms: [
      "تُجدَّد الباقة لمدة 12 شهراً اعتباراً من تاريخ البدء المذكور أعلاه.",
      "الإنهاء المبكر: الرسوم الشهرية المتبقية بحد أقصى 600 درهم.",
      "تُصدر الفواتير شهرياً على الحساب المذكور أعلاه.",
      "تم التوقيع إلكترونياً عبر الهوية الرقمية (UAE PASS)، وللتوقيع الإلكتروني أثر التوقيع الخطي نفسه.",
    ],
    signLabel: "اكتب اسمك الكامل للتوقيع", signHint: "اكتب هيثم محمد أو Haitham Mohamed",
    signBtn: "التوقيع عبر الهوية الرقمية", signed: "تم التوقيع عبر الهوية الرقمية", demo: "مستند تجريبي",
  },
} as const;

export function Signature({ name, className }: { name: string; className?: string }) {
  return <span className={`${s.signature} ${isArabic(name) ? s.sigAr : s.sigEn} ${className ?? ""}`}>{name}</span>;
}

export function EsignDocument({ task }: { task: MessengerTask }) {
  const result = task.result?.type === "esign" ? task.result : undefined;
  const [lang, setLang] = useState<Lang>("en");
  const [typed, setTyped] = useState("");
  const stage = useEsign((st) => (st.taskId === task.id ? st.stage : "idle"));
  if (!result) return null;
  const t = copy[lang];
  const valid = isValidSignature(typed);
  const signedAt = result.signedAt ? new Date(result.signedAt) : undefined;

  return (
    <article className={s.doc} dir={lang === "ar" ? "rtl" : "ltr"} lang={lang}>
      <div className={s.langs} role="tablist" dir="ltr">
        <button role="tab" aria-selected={lang === "en"} className={lang === "en" ? s.langOn : ""} onClick={() => setLang("en")}>English</button>
        <button role="tab" aria-selected={lang === "ar"} className={lang === "ar" ? s.langOn : ""} onClick={() => setLang("ar")}>العربية</button>
      </div>

      <header className={s.head}>
        <span className={s.wordmark} dir="ltr">e<span>&</span></span>
        <span className={s.demo}>{t.demo}</span>
      </header>
      <h2 className={s.title}>{t.title}</h2>

      <dl className={s.facts}>
        <dt>{t.provider}</dt><dd>{t.providerV}</dd>
        <dt>{t.customer}</dt><dd>{t.customerV}</dd>
        <dt>{t.account}</dt><dd dir="ltr">1.29384756</dd>
        <dt>{t.mobile}</dt><dd dir="ltr">+971 50 123 4567</dd>
        <dt>{t.plan}</dt><dd>{t.planV}</dd>
        <dt>{t.term}</dt><dd>{t.termV}</dd>
        <dt>{t.fee}</dt><dd><strong>{t.feeV}</strong></dd>
        <dt>{t.includes}</dt><dd>{t.includesV}</dd>
      </dl>

      <ol className={s.terms}>{t.terms.map((x) => <li key={x}>{x}</li>)}</ol>

      {result.signature && signedAt ? (
        <div className={s.signedBox}>
          <Signature name={result.signature} />
          <span className={s.signedMeta}>
            <BadgeCheck size={18} strokeWidth={2} />
            {t.signed} · <span dir="ltr">{signedAt.toLocaleString(lang === "ar" ? "ar-AE" : "en-AE", { dateStyle: "medium", timeStyle: "short" })}</span>
          </span>
        </div>
      ) : (
        <div className={s.signArea}>
          <label className={s.signLabel}>
            {t.signLabel}
            <input className={s.signInput} value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={t.signHint}
              dir={isArabic(typed) ? "rtl" : "ltr"} aria-invalid={typed.length > 3 && !valid} />
          </label>
          <div className={s.sigPreview} aria-live="polite">
            {typed.trim() ? <Signature name={typed} className={valid ? "" : s.sigDim} /> : <span className={s.sigLine} />}
          </div>
          <button className={s.uaepass} disabled={!valid || stage !== "idle"} onClick={() => esign.request(task.id, typed)}>
            {stage === "scanning" ? <Spinner /> : <Fingerprint size={20} strokeWidth={2} />}{t.signBtn}
          </button>
        </div>
      )}
    </article>
  );
}

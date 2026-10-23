"use client";
import s from "./assistant.module.css";

/** Hero line illustration: Burj Khalifa, Burj Al Arab sail, a palm, a few towers. Vector only. */
export function HeroSkyline() {
  return (
    <svg className={s.skyline} viewBox="0 0 240 120" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 114H236" />
      {/* towers */}
      <path d="M20 114V72h16v42M24 80h8M24 88h8M24 96h8M24 104h8" />
      <path d="M42 114V56h14v58M46 64h6M46 72h6M46 80h6M46 88h6M46 96h6M46 104h6" />
      <path d="M62 114V80h12v34M66 88h4M66 96h4M66 104h4" />
      <path d="M82 114V64h14v50M86 72h6M86 80h6M86 88h6M86 96h6M86 104h6" />
      {/* Burj Khalifa */}
      <path d="M120 4l2 22 3 16 4 14 5 14 4 12v32M120 4l-2 22-3 16-4 14-5 14-4 12v32" />
      <path d="M115 44h10M112 58h16M109 72h22M107 88h26M120 4V2" />
      {/* towers right */}
      <path d="M144 114V76h10v38M147 84h4M147 92h4M147 100h4" />
      <path d="M158 114V90h8v24" />
      {/* Burj Al Arab sail */}
      <path d="M172 114V38M172 38c20 8 28 42 26 76M172 38V26M172 56c12 6 20 28 22 58M172 78c6 6 12 18 14 36" />
      {/* palm */}
      <path d="M216 114c0-14 2-28 6-40M222 74c-10-8-20-8-28-2M222 74c-4-12-14-18-24-18M222 74c8-10 18-12 26-8M222 74c4-12 14-16 22-12M222 74c-8-2-16 4-20 14" />
    </svg>
  );
}

const BLOCKS: [number, number, number][] = [
  [0, 40, 70], [46, 30, 110], [82, 36, 84], [124, 28, 130], [158, 34, 96], [198, 30, 150], [234, 40, 104], [280, 34, 126],
  [324, 30, 90], [360, 38, 142], [404, 30, 108], [440, 36, 160], [484, 28, 118], [520, 40, 96], [566, 30, 134],
  [650, 36, 120], [694, 30, 92], [730, 40, 112], [776, 24, 76],
];

/** Very faint large skyline silhouette along the bottom-right of the main area. */
export function BackdropSkyline() {
  const base = 240;
  const blocks = BLOCKS.map(([x, w, h]) => `M${x} ${base}V${base - h}h${w}V${base}z`).join("");
  const burj = `M612 ${base}L606 ${base - 40}L610 ${base - 90}L613 ${base - 140}L615 ${base - 190}L617 ${base - 232}L619 ${base - 190}L621 ${base - 140}L624 ${base - 90}L628 ${base - 40}L622 ${base}z`;
  const sail = `M454 ${base - 160}C510 ${base - 150} 530 ${base - 80} 526 ${base}H454z`;
  return (
    <svg className={s.backdrop} viewBox="0 0 800 240" preserveAspectRatio="xMaxYMax meet" fill="currentColor" aria-hidden="true" data-testid="backdrop-skyline">
      <path d={blocks} />
      <path d={burj} />
      <path d={sail} />
    </svg>
  );
}

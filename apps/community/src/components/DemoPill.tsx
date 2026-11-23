export default function DemoPill({ label = "Demo data" }: { label?: string }) {
  return <span className="demo-pill" data-testid="demo-pill">{label}</span>;
}

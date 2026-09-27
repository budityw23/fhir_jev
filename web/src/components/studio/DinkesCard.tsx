export interface DinkesCardProps { disease: string; urgency: string; }

/** Present the mandatory public-health reporting action. */
export function DinkesCard({ disease, urgency }: DinkesCardProps) {
  return (
    <aside className="dinkes-card">
      <strong>⚑ Report to Dinkes · {urgency}</strong>
      <span>{disease}</span>
    </aside>
  );
}

export interface FlatStateTableProps { state: Record<string, unknown>; }

/** Display the serializer's exact flat state without hiding absent values. */
export function FlatStateTable({ state }: FlatStateTableProps) {
  return (
    <table className="flat-state"><tbody>{Object.entries(state).map(([key, value]) => (
      <tr className={value === null ? "is-null" : ""} key={key}>
        <th>{key}</th><td>{display(value)}</td>
      </tr>
    ))}</tbody></table>
  );
}

function display(value: unknown): React.ReactNode {
  if (typeof value === "boolean") {
    return <span className="boolean-chip">{value ? "✓ true" : "✗ false"}</span>;
  }
  if (value === null) return <span className="null-chip">null</span>;
  return typeof value === "string" ? value : JSON.stringify(value);
}

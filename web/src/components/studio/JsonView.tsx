import ReactJsonView from "@uiw/react-json-view";

export interface JsonViewProps { value: unknown; collapsedDepth?: number; }

/** Show structured JSON in a read-only, collapsible tree. */
export function JsonView({ value, collapsedDepth = 2 }: JsonViewProps) {
  const safeValue = value !== null && typeof value === "object" ? value : { value };
  return <ReactJsonView value={safeValue} collapsed={collapsedDepth} displayDataTypes={false} />;
}

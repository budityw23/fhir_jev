import ReactJsonView from "@uiw/react-json-view";
import type { CSSProperties } from "react";

export interface JsonViewProps { value: unknown; collapsedDepth?: number; }

/** Show structured JSON in a read-only, collapsible tree. */
export function JsonView({ value, collapsedDepth = 2 }: JsonViewProps) {
  const safeValue = value !== null && typeof value === "object" ? value : { value };
  const theme = {
    "--w-rjv-background-color": "var(--c-surface)",
    "--w-rjv-color": "var(--c-text)",
    "--w-rjv-key-string": "var(--c-json-key)",
    "--w-rjv-string": "var(--c-json-value)",
  } as CSSProperties;
  return (
    <ReactJsonView
      value={safeValue}
      collapsed={collapsedDepth}
      displayDataTypes={false}
      style={theme}
    />
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import { useFixtures } from "../../api/queries";
import { ApiError } from "../../api/client";
import { ErrorCard } from "../shell/ErrorCard";
import type { DemoModule, FixtureEntry } from "../../api/types";

export interface FixturePickerProps {
  module: DemoModule;
  value: string | null;
  onChange: (id: string) => void;
}

/** Select a labelled fixture, grouped by its data source. */
export function FixturePicker({ module, value, onChange }: FixturePickerProps) {
  const [search, setSearch] = useState("");
  const list = useRef<HTMLDivElement>(null);
  const fixtures = useFixtures({ module });
  const groups = useMemo(() => {
    const filtered = (fixtures.data ?? []).filter((entry) => matches(entry, search));
    return filtered.reduce<Record<string, FixtureEntry[]>>((groups, entry) => {
      (groups[entry.source] ??= []).push(entry);
      return groups;
    }, {});
  }, [fixtures.data, search]);
  useEffect(() => {
    const selected = list.current?.querySelector<HTMLInputElement>("input:checked");
    if (typeof selected?.scrollIntoView === "function")
      selected.scrollIntoView({ block: "nearest" });
  }, [value, groups]);
  return (
    <section aria-label="Fixture picker">
      <h3>Input</h3>
      <label>
        Search fixtures
        <input value={search} onChange={(event) => setSearch(event.target.value)} />
      </label>
      {fixtures.error instanceof ApiError && <ErrorCard error={fixtures.error.body} />}
      <div className="fixture-picker-list" ref={list}>
      {Object.entries(groups).length === 0 && <p>no fixtures match</p>}
      {Object.entries(groups).map(([source, entries]) => (
        <fieldset key={source}>
          <legend>{source}</legend>
          {entries.map((entry) => {
            const duplicate = entries.some(
              (item) => item.id !== entry.id && item.name === entry.name,
            );
            const displayName = duplicate ? `${entry.name} · ${entry.resource_type}` : entry.name;
            return (
              <label className="fixture-option" key={entry.id}>
                <input aria-label={displayName} checked={value === entry.id} type="radio"
                  name="fixture" onChange={() => onChange(entry.id)} />
                <span className="fixture-name">{displayName}</span>
                <span className="fixture-label">{entry.label}</span>
                {entry.difficulty === "hard" && <small className="fixture-tag">hard</small>}
                {!entry.approved && <small className="fixture-tag">draft</small>}
              </label>
            );
          })}
        </fieldset>
      ))}
      </div>
    </section>
  );
}

function matches(entry: FixtureEntry, search: string): boolean {
  const needle = search.trim().toLowerCase();
  return needle.length === 0 || `${entry.name} ${entry.label}`.toLowerCase().includes(needle);
}

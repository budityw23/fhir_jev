import { useMemo, useState } from "react";
import { useFixtures } from "../../api/queries";
import type { DemoModule, FixtureEntry } from "../../api/types";

export interface FixturePickerProps {
  module: DemoModule;
  value: string | null;
  onChange: (id: string) => void;
}

/** Select a labelled fixture, grouped by its data source. */
export function FixturePicker({ module, value, onChange }: FixturePickerProps) {
  const [search, setSearch] = useState("");
  const fixtures = useFixtures({ module });
  const groups = useMemo(() => {
    const filtered = (fixtures.data ?? []).filter((entry) => matches(entry, search));
    return filtered.reduce<Record<string, FixtureEntry[]>>((groups, entry) => {
      (groups[entry.source] ??= []).push(entry);
      return groups;
    }, {});
  }, [fixtures.data, search]);
  return (
    <section aria-label="Fixture picker">
      <h3>Input</h3>
      <label>
        Search fixtures
        <input value={search} onChange={(event) => setSearch(event.target.value)} />
      </label>
      {Object.entries(groups).map(([source, entries]) => (
        <fieldset key={source}>
          <legend>{source}</legend>
          {entries.map((entry) => (
            <label className="fixture-option" key={entry.id}>
              <input aria-label={entry.name} checked={value === entry.id} type="radio"
                name="fixture" onChange={() => onChange(entry.id)} />
              <span>{entry.label}</span>
              {entry.difficulty === "hard" && <small>hard</small>}
              {!entry.approved && <small>draft</small>}
            </label>
          ))}
        </fieldset>
      ))}
    </section>
  );
}

function matches(entry: FixtureEntry, search: string): boolean {
  const needle = search.trim().toLowerCase();
  return needle.length === 0 || `${entry.name} ${entry.label}`.toLowerCase().includes(needle);
}

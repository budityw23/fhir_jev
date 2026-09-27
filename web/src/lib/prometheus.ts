/** Parse Prometheus exposition samples used by the observability drawer. */
export function parsePrometheus(
  text: string,
): Array<{ name: string; labels: Record<string, string>; value: number }> {
  return text.split("\n").flatMap((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return [];
    const match = trimmed.match(/^([A-Za-z_:][\w:]*)((?:\{.*\})?)\s+(\S+)/);
    if (!match) return [];
    const [, name, labelText, rawValue] = match;
    const labels: Record<string, string> = {};
    if (labelText) {
      const source = labelText.slice(1, -1);
      const labelPattern = /([A-Za-z_][\w]*)="((?:\\.|[^"\\])*)"/g;
      let matched: RegExpExecArray | null;
      let consumed = "";
      while ((matched = labelPattern.exec(source)) !== null) {
        labels[matched[1]] = matched[2].replace(/\\([\\"n])/g, (_, escaped: string) => (
          escaped === "n" ? "\n" : escaped
        ));
        consumed += `${matched[0]},`;
      }
      if (consumed.slice(0, -1) !== source) return [];
    }
    const value = rawValue === "+Inf"
      ? Infinity
      : rawValue === "-Inf" ? -Infinity : Number(rawValue);
    return [{ name, labels, value }];
  });
}

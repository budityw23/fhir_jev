import { describe, expect, it } from "vitest";
import { noulView } from "../lib/noul";
describe("noulView boundaries: 0, 0.5, 1, 0.08, 0.94.", () => {
  it.each([
    [0, "✗ 100%"],
    [0.5, "✓ 50%"],
    [1, "✓ 100%"],
    [0.08, "✗ 92%"],
    [0.94, "✓ 94%"],
  ])("formats %s", (p, label) => expect(noulView(p)).toMatchObject({ label }));
});

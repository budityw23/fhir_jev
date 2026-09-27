import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UiPrefsProvider, useUiPrefs } from "../state/uiPrefs";

describe("uiPrefs", () => {
  it("keeps working when localStorage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const { result } = renderHook(() => useUiPrefs(), {
      wrapper: UiPrefsProvider,
    });
    act(() => {
      result.current.setFontScale("125");
      result.current.setPresenterNotes(true);
    });
    expect(result.current.fontScale).toBe("125");
    expect(result.current.presenterNotes).toBe(true);
  });
});

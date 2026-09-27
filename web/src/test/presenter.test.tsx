import { fireEvent, render, screen } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import catalog from "./fixtures/catalog.json";
import { SCENES } from "../scenes";
import { PresenterNotes, PresenterProvider } from "../state/presenter";
import { UiPrefsProvider } from "../state/uiPrefs";

describe("presenter scenes", () => {
  it("Every `SCENES[*].fixtureId` and step fixture exists in a committed catalog snapshot", () => {
    const ids = new Set(catalog.map((entry) => entry.id));
    for (const scene of SCENES) {
      if (scene.fixtureId) expect(ids.has(scene.fixtureId)).toBe(true);
      for (const step of scene.steps ?? []) {
        if (step.fixtureId) expect(ids.has(step.fixtureId)).toBe(true);
      }
    }
  });

  it("The key handler ignores keystrokes inside inputs.", () => {
    render(<Harness />);
    for (const label of ["text", "textarea", "select", "editable", "editor"]) {
      fireEvent.keyDown(screen.getByLabelText(label), { key: "ArrowRight" });
      expect(screen.getByTestId("location")).toHaveTextContent("/");
    }
    fireEvent.keyDown(window, { key: "ArrowRight", ctrlKey: true });
    expect(screen.getByTestId("location")).toHaveTextContent("/");
  });

  it("keeps shortcuts active for range and radio inputs", () => {
    const view = render(<Harness />);
    fireEvent.keyDown(view.container.querySelector("input[type='range']")!, {
      key: "ArrowRight",
    });
    expect(view.container.querySelector("output")!).toHaveTextContent(
      "/studio/quality",
    );
    fireEvent.keyDown(view.container.querySelector("input[type='radio']")!, {
      key: "r",
    });
    expect(view.container.querySelector("output")!).toHaveTextContent(
      "/studio/quality",
    );
  });

  it("ignores textarea, editable, and CodeMirror keys without changing state", () => {
    const view = render(<Harness />);
    for (const target of [
      view.container.querySelector("textarea")!,
      view.container.querySelector("[contenteditable='true']")!,
      view.container.querySelector(".cm-content span")!,
    ]) {
      fireEvent.keyDown(target, { key: "r" });
      fireEvent.keyDown(target, { key: "f" });
      fireEvent.keyDown(target, { key: "ArrowRight" });
    }
    expect(view.container.querySelector("output")!).toHaveTextContent("/");
    expect(document.documentElement.dataset.scale).toBe("100");
  });

  it("toggles notes and drawer with N and O", () => {
    const view = render(<Harness />);
    fireEvent.keyDown(window, { key: "n" });
    expect(
      view.container.querySelector("[aria-label='Presenter notes']")!,
    ).toBeVisible();
    fireEvent.keyDown(window, { key: "n" });
    expect(
      view.container.querySelector("[aria-label='Presenter notes']"),
    ).toBeNull();
    fireEvent.keyDown(window, { key: "o" });
    expect(
      view.container.querySelector("[data-testid='drawer']")!,
    ).toHaveTextContent("open");
    fireEvent.keyDown(window, { key: "o" });
    expect(
      view.container.querySelector("[data-testid='drawer']")!,
    ).toHaveTextContent("closed");
  });
});

function Harness() {
  return (
    <MemoryRouter>
      <UiPrefsProvider>
        <DrawerHarness>
          <label>
            text
            <input type="text" />
          </label>
          <label>
            textarea
            <textarea />
          </label>
          <label>
            select
            <select>
              <option>one</option>
            </select>
          </label>
          <div aria-label="editable" contentEditable="true" />
          <div aria-label="editor" className="cm-content">
            <span>editor</span>
          </div>
          <label>
            range
            <input type="range" />
          </label>
          <label>
            radio
            <input type="radio" />
          </label>
          <Location />
        </DrawerHarness>
      </UiPrefsProvider>
    </MemoryRouter>
  );
}

function DrawerHarness({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <PresenterProvider onDrawer={() => setOpen(!open)}>
      {children}
      <output data-testid="drawer">{open ? "open" : "closed"}</output>
      <PresenterNotes />
    </PresenterProvider>
  );
}

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}

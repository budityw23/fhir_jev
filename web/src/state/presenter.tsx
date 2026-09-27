import {
  useCallback,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { SCENES, type Scene } from "../scenes";
import { useUiPrefs } from "./uiPrefs";

type Presenter = {
  scene: Scene;
  step: number;
  next(): void;
  previous(): void;
  reset(): void;
};
const fallbackPresenter: Presenter = {
  scene: SCENES[0]!,
  step: 0,
  next: () => undefined,
  previous: () => undefined,
  reset: () => undefined,
};
const PresenterContext = createContext<Presenter>(fallbackPresenter);

function states(scene: Scene): Array<{
  fixtureId?: string;
  thresholds?: Scene["thresholds"];
  note: string;
}> {
  return [
    {
      fixtureId: scene.fixtureId,
      thresholds: scene.thresholds,
      note: scene.note,
    },
    ...(scene.steps ?? []),
  ];
}
function isTypingTarget(target: EventTarget | null): boolean {
  const element = target instanceof HTMLElement ? target : null;
  if (!element) return false;
  if (
    element.closest("textarea, select, [contenteditable='true'], .cm-content")
  )
    return true;
  const input = element.closest("input");
  if (!(input instanceof HTMLInputElement)) return false;
  return [
    "",
    "text",
    "search",
    "email",
    "number",
    "password",
    "url",
    "tel",
  ].includes(input.type);
}

/** Apply scenes by URL so presentation state remains shareable and locally interactive. */
export function PresenterProvider({
  children,
  onDrawer,
}: {
  children: ReactNode;
  onDrawer(): void;
}) {
  const navigate = useNavigate();
  const { fontScale, setFontScale, presenterNotes, setPresenterNotes } =
    useUiPrefs();
  const [position, setPosition] = useState({ scene: 0, step: 0 });
  const scene = SCENES[position.scene]!;
  const apply = useCallback(
    (next: { scene: number; step: number }): void => {
      const nextScene = SCENES[next.scene]!;
      const state = states(nextScene)[next.step]!;
      const query = new URLSearchParams();
      if (state.fixtureId) query.set("fixture", state.fixtureId);
      for (const [key, value] of Object.entries(state.thresholds ?? {}))
        query.set(key, String(value));
      if (nextScene.autoAction === "startPipeline") {
        query.set("autostart", "1");
        query.set("source", nextScene.pipeline!.source);
        query.set("rate", String(nextScene.pipeline!.ratePerS));
      }
      setPosition(next);
      navigate(
        { pathname: nextScene.route, search: query.toString() },
        { replace: false },
      );
    },
    [navigate],
  );
  const next = useCallback((): void => {
    const count = states(scene).length;
    if (position.step + 1 < count)
      apply({ ...position, step: position.step + 1 });
    else if (position.scene + 1 < SCENES.length)
      apply({ scene: position.scene + 1, step: 0 });
  }, [apply, position, scene]);
  const previous = useCallback((): void => {
    if (position.step > 0) apply({ ...position, step: position.step - 1 });
    else if (position.scene > 0) {
      const prior = position.scene - 1;
      apply({ scene: prior, step: states(SCENES[prior]!).length - 1 });
    }
  }, [apply, position]);
  const reset = useCallback((): void => apply(position), [apply, position]);
  useEffect(() => {
    const handle = (event: KeyboardEvent): void => {
      if (
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        isTypingTarget(event.target)
      )
        return;
      if (event.key === "ArrowRight") next();
      else if (event.key === "ArrowLeft") previous();
      else if (/^[1-6]$/.test(event.key))
        apply({ scene: Number(event.key), step: 0 });
      else if (event.key.toLowerCase() === "r") reset();
      else if (event.key.toLowerCase() === "f")
        setFontScale(fontScale === "100" ? "125" : "100");
      else if (event.key.toLowerCase() === "o") onDrawer();
      else if (event.key.toLowerCase() === "n")
        setPresenterNotes(!presenterNotes);
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [
    apply,
    fontScale,
    next,
    onDrawer,
    presenterNotes,
    previous,
    reset,
    setFontScale,
    setPresenterNotes,
  ]);
  const value = useMemo(
    () => ({ scene, step: position.step, next, previous, reset }),
    [next, position.step, previous, reset, scene],
  );
  return (
    <PresenterContext.Provider value={value}>
      {children}
    </PresenterContext.Provider>
  );
}
/** Read the current applied scene for global shell controls. */
export function usePresenter(): Presenter {
  return useContext(PresenterContext);
}
/** Render current scene talk track only when the persisted preference requests it. */
export function PresenterNotes(): ReactNode {
  const { presenterNotes } = useUiPrefs();
  const { scene, step } = usePresenter();
  if (!presenterNotes) return null;
  return (
    <aside className="presenter-notes" aria-label="Presenter notes">
      {states(scene)[step]!.note}
    </aside>
  );
}

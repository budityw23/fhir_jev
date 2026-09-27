import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type FontScale = "100" | "125";
interface UiPrefs {
  fontScale: FontScale;
  presenterNotes: boolean;
  setFontScale(scale: FontScale): void;
  setPresenterNotes(value: boolean): void;
}
const UiPrefsContext = createContext<UiPrefs | null>(null);

function readPreference(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}
function writePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* Storage can be disabled in privacy modes. */
  }
}

/** Store presentation preferences while remaining usable when browser storage is unavailable. */
export function UiPrefsProvider({ children }: { children: ReactNode }) {
  const [fontScale, setFontScale] = useState<FontScale>(() =>
    readPreference("jev-font-scale") === "125" ? "125" : "100",
  );
  const [presenterNotes, setPresenterNotes] = useState(
    () => readPreference("jev-presenter-notes") === "true",
  );
  useEffect(() => {
    document.documentElement.dataset.scale = fontScale;
    writePreference("jev-font-scale", fontScale);
  }, [fontScale]);
  useEffect(() => {
    writePreference("jev-presenter-notes", String(presenterNotes));
  }, [presenterNotes]);
  return (
    <UiPrefsContext.Provider
      value={{ fontScale, presenterNotes, setFontScale, setPresenterNotes }}
    >
      {children}
    </UiPrefsContext.Provider>
  );
}
/** Access presentational UI preferences. */
export function useUiPrefs(): UiPrefs {
  const value = useContext(UiPrefsContext);
  if (!value) throw new Error("useUiPrefs must be used within UiPrefsProvider");
  return value;
}

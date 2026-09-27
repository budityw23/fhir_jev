import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { ObservabilityDrawer } from "./components/shell/ObservabilityDrawer";
import { TopBar } from "./components/shell/TopBar";
import { Benchmarks } from "./pages/Benchmarks";
import { Overview } from "./pages/Overview";
import { Playground } from "./pages/Playground";
import { Pipeline } from "./pages/Pipeline";
import { Studio } from "./pages/Studio";
import { PresenterNotes, PresenterProvider } from "./state/presenter";
import { UiPrefsProvider } from "./state/uiPrefs";

/** Route-level application shell for the D2 incremental implementation. */
export function App() {
  return (
    <UiPrefsProvider>
      <AppShell />
    </UiPrefsProvider>
  );
}

/** Keep application preferences available for both production and isolated shell tests. */
function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const toggleDrawer = (): void => setDrawerOpen((open) => !open);
  return (
    <PresenterProvider onDrawer={toggleDrawer}>
      <TopBar onObservability={toggleDrawer} observabilityOpen={drawerOpen} />
      <ObservabilityDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/studio/:module" element={<Studio />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="/pipeline" element={<Pipeline />} />
        <Route path="/benchmarks" element={<Benchmarks />} />
      </Routes>
      <PresenterNotes />
    </PresenterProvider>
  );
}

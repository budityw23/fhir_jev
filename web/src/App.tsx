import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/shell/TopBar";
import { Overview } from "./pages/Overview";
import { Studio } from "./pages/Studio";

function Placeholder({ heading, phase }: { heading: string; phase: string }) {
  return (
    <main>
      <h2>{heading}</h2>
      <p>Coming in {phase}</p>
    </main>
  );
}
/** Route-level application shell for the D2 incremental implementation. */
export function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route
          path="/"
          element={<Overview />}
        />
        <Route
          path="/studio/:module"
          element={<Studio />}
        />
        <Route
          path="/playground"
          element={<Placeholder heading="Playground" phase="D2c" />}
        />
        <Route
          path="/pipeline"
          element={<Placeholder heading="Pipeline" phase="D3" />}
        />
        <Route
          path="/benchmarks"
          element={<Placeholder heading="Benchmarks" phase="D4" />}
        />
      </Routes>
    </>
  );
}

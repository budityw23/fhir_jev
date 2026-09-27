import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/shell/TopBar";

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
          element={<Placeholder heading="Overview" phase="D2b" />}
        />
        <Route
          path="/studio/:module"
          element={<Placeholder heading="Studio" phase="D2b" />}
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

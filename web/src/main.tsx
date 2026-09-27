import "@fontsource-variable/inter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import "./index.css";
import { UiPrefsProvider } from "./state/uiPrefs";

const queryClient = new QueryClient();
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <UiPrefsProvider>
        <BrowserRouter basename="/demo">
          <App />
        </BrowserRouter>
      </UiPrefsProvider>
    </QueryClientProvider>
  </StrictMode>,
);

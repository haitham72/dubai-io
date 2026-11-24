import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { actions, getState } from "./store";
import "./tokens.css";

(window as unknown as Record<string, unknown>).__messenger = { actions, getState };
void actions.restoreSession();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

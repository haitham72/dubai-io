"use client";
import dynamic from "next/dynamic";

// Client-only: the app reads window/matchMedia/localStorage and never server-renders.
const App = dynamic(() => import("./App"), { ssr: false });

export default function Mount() {
  return <App />;
}

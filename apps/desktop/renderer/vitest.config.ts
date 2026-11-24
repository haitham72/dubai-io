import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const rendererRoot = path.dirname(fileURLToPath(import.meta.url));

const nm = (name: string) => path.resolve(rendererRoot, "node_modules", name);

export default defineConfig({
  root: rendererRoot,
  plugins: [react()],
  resolve: {
    alias: [
      { find: "react/jsx-dev-runtime", replacement: nm("react/jsx-dev-runtime") },
      { find: "react/jsx-runtime", replacement: nm("react/jsx-runtime") },
      { find: "@testing-library/react", replacement: nm("@testing-library/react") },
      { find: "react-dom/client", replacement: nm("react-dom/client") },
      { find: "react-dom", replacement: nm("react-dom") },
      { find: "react", replacement: nm("react") },
    ],
  },
  server: { fs: { allow: [path.resolve(rendererRoot, ".."), rendererRoot] } },
  test: {
    environment: "jsdom",
    include: ["../tests/renderer/**/*.test.tsx"],
    setupFiles: ["./vitest.setup.ts"],
  },
});

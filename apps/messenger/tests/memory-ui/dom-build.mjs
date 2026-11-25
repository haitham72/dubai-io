import { build } from "esbuild";
import { writeFileSync } from "node:fs";

// Bundle the DOM click-through entry for the browser (IIFE, no modules -> works from file://).
await build({
  entryPoints: ["tests/memory-ui/dom-entry.tsx"],
  bundle: true,
  platform: "browser",
  format: "iife",
  outfile: "tests/memory-ui/bundle.dom.js",
  logLevel: "error",
  loader: { ".css": "local-css", ".png": "dataurl", ".jpg": "dataurl", ".svg": "dataurl" },
  jsx: "automatic",
});

writeFileSync(
  "tests/memory-ui/dom-test.html",
  `<!doctype html><html><head><meta charset="utf-8"><title>memory-dom-test</title></head>` +
    `<body><div id="root"></div><script src="./bundle.dom.js"></script></body></html>`,
);
console.log("BUNDLED MEMORY-UI DOM");

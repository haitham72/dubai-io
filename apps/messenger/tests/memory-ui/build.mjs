import { build } from "esbuild";

await build({
  entryPoints: ["tests/memory-ui/entry.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: "tests/memory-ui/bundle.mjs",
  logLevel: "error",
  loader: { ".css": "local-css", ".png": "dataurl", ".jpg": "dataurl", ".svg": "dataurl" },
  jsx: "automatic",
  banner: { js: "import { createRequire as __cr } from \"node:module\"; const require = __cr(import.meta.url);" },
});
console.log("BUNDLED MEMORY-UI");

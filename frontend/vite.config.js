import { defineConfig } from "vite";

// The page talks to the Python backend. In dev, Vite forwards /api to it.
const backend = `http://127.0.0.1:${process.env.SAFEBOARD_PORT || process.env.PANO_PORT || 3195}`;

export default defineConfig({
  server: { host: "127.0.0.1", proxy: { "/api": backend } },
  build: { outDir: "dist", emptyOutDir: true, assetsInlineLimit: 0 },
});

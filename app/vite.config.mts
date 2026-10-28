import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Strict CSP for the packaged renderer only (the dev server needs inline scripts for React Fast Refresh).
const CSP =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; " +
  "connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; font-src 'self' data:";

export default defineConfig({
  plugins: [
    react(),
    {
      name: "opendgus-csp",
      apply: "build",
      transformIndexHtml: (html) =>
        html.replace("<head>", `<head>\n    <meta http-equiv="Content-Security-Policy" content="${CSP}" />`),
    },
  ],
  base: "./",
  server: { port: 5173, strictPort: true, host: "127.0.0.1" },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 1500 },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});

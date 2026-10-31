/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const api = process.env.API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  // "/" locally; the Pages build serves from a subfolder (`make demo-build BASE=/repo/`).
  base: process.env.VITE_BASE || "/",
  // Same-origin /graphql in dev: no CORS, and the same path works behind a proxy in prod.
  server: { port: 5173, proxy: { "/graphql": api } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});

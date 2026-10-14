import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to the FastAPI backend, so the browser talks to a single
// origin and the session cookie stays first-party. Override the backend with
// SKILLFORGE_API (e.g. SKILLFORGE_API=http://127.0.0.1:8001 npm run dev).
const target = process.env.SKILLFORGE_API || "http://127.0.0.1:8000";
const backend = { "/api": target };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: backend },
  preview: { port: 4173, proxy: backend },
});

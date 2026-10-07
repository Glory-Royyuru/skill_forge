import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to the FastAPI backend so the app works from either the
// dev server or `vite preview` without CORS configuration.
const backend = { "/api": "http://127.0.0.1:8000" };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: backend },
  preview: { port: 4173, proxy: backend },
});

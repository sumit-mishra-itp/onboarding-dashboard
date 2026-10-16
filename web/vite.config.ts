import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: { usePolling: true }, // Docker bind mounts on Windows don't deliver file-change events
    // Same-origin /api keeps the session cookie simple (no CORS).
    proxy: { "/api": process.env.API_URL ?? "http://localhost:8000" },
  },
});

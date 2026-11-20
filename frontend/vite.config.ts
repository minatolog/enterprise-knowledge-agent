import { defineConfig } from "vite";

// Local service (app.api) on 8020, enterprise service (app.enterprise.api) on 8030.
export default defineConfig({
  base: "/studio/",
  server: {
    port: 5173,
    proxy: {
      "/api/v1": "http://127.0.0.1:8020",
      "/health": "http://127.0.0.1:8020",
      "/api/v2": "http://127.0.0.1:8030",
    },
  },
  build: { outDir: "dist" },
});

import { defineConfig } from "vite";
import reactRefresh from "@vitejs/plugin-react";

export default defineConfig({
  base: "/",
  build: {
    target: "esnext",
    outDir: "dist",
  },
  plugins: [reactRefresh()],
  server: {
    host: "0.0.0.0",
    port: 3001,
  },
  optimizeDeps: {
    esbuildOptions: {
      target: "esnext",
    },
  },
  define: {
    APP_VERSION: JSON.stringify(process.env.npm_package_version)
  },
});

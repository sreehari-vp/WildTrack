import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
var vite_config_default = defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true
      }
    }
  }
});
export {
  vite_config_default as default
};

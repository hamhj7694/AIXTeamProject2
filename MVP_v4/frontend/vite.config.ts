import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  envDir: false,
  server: {
    proxy: {
      '/api': { target: process.env.GENERAL_API_BASE_URL || 'http://127.0.0.1:8100' },
    },
  },
});

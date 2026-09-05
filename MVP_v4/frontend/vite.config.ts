import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const testActorId = process.env.CSR_V4_TEST_PROXY_ACTOR_ID;
const testActorRole = process.env.CSR_V4_TEST_PROXY_ACTOR_ROLE;

export default defineConfig({
  plugins: [react()],
  envDir: false,
  server: {
    proxy: {
      '/api': {
        target: process.env.GENERAL_API_BASE_URL || 'http://127.0.0.1:8100',
        configure(proxy) {
          // This is a local Vite test harness only. Production Nginx never supplies client authority.
          if (testActorId && testActorRole) {
            proxy.on('proxyReq', (request) => {
              request.setHeader('X-CSR-Test-Actor-ID', testActorId);
              request.setHeader('X-CSR-Test-Actor-Role', testActorRole);
            });
          }
        },
      },
    },
  },
});

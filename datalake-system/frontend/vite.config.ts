import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: {
    port: 8503,
    host: true,
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});

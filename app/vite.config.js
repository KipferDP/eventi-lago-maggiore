import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' = relative Pfade: läuft unter https://kipferdp.github.io/eventi-lago-maggiore/
// genauso wie lokal (npm run preview).
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})

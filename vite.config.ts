import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// `npm run build` emits dist/index.html as a single self-contained file — all JS,
// CSS and assets inlined — so it can be opened straight from disk, no server needed.
export default defineConfig({
  base: './',
  plugins: [react(), viteSingleFile()],
})

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // three is the bulk and rarely changes: its own chunk stays cached across app deploys
    rolldownOptions: { output: { codeSplitting: { groups: [{ name: 'three', test: /node_modules[\\/]three[\\/]/ }] } } },
  },
  test: {
    include: ['tests/unit/**/*.test.ts'],
  },
})

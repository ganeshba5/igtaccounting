import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow access from other devices on the network
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001', // Development proxy - production uses VITE_API_BASE_URL
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'azure-vendor': ['@azure/msal-browser'],
          'axios-vendor': ['axios']
        }
      }
    }
  }
})


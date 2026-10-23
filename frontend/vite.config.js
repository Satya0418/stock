/**
 * ==============================================================================
 * Vite Configuration
 * ==============================================================================
 * 
 * Vite is a modern build tool that provides:
 * - Fast development server with Hot Module Replacement (HMR)
 * - Optimized production builds
 * - Easy configuration
 * 
 * This file configures:
 * - React plugin for JSX support
 * - Development server settings
 * - Build output settings
 * ==============================================================================
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // React plugin enables JSX transformation and Fast Refresh
  plugins: [react()],
  
  // Development server configuration
  server: {
    // Port for development server
    port: 5173,
    
    // Open browser automatically on start
    open: true,
    
    // Proxy API requests to Django backend
    // This avoids CORS issues during development
    proxy: {
      // Forward /api requests to Django
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Forward auth and stock requests to Django
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/stocks': {
        target: 'http://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  
  // Build configuration
  build: {
    // Output directory for production build
    outDir: 'dist',
    
    // Generate source maps for debugging
    sourcemap: true,
    
    // Minify for production
    minify: 'esbuild',
  },
  
  // Path resolution
  resolve: {
    alias: {
      // Allow importing from '@/components/...' instead of '../components/...'
      '@': '/src',
    },
  },
});

import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.GITHUB_PAGES === 'true' ? '/AI-Coding-Workspace/' : '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // 拆分大依赖，减少首屏加载体积
        manualChunks(id) {
          if (id.includes('monaco-editor')) return 'monaco'
          if (id.includes('element-plus') || id.includes('@element-plus')) return 'element'
          if (id.includes('node_modules/vue') || id.includes('vue-router') || id.includes('pinia') || id.includes('vue-i18n')) return 'vue-vendor'
        },
      },
    },
  },
})

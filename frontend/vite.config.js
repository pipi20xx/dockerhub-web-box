import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  // ✨ 核心修改：将 base 设置为 './'
  // 这确保所有生成的<script>和<link>标签都使用相对路径 (例如 <script src="./assets/index-....js">)
  // 无论应用被部署在哪个子目录下，都能正确加载资源。
  base: './',
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
})
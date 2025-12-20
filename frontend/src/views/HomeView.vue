<template>
  <div>
    <header class="main-header">
      <h1>Docker Web Pusher</h1>
      <!-- ✨ 新增一个伸缩的空白div，将切换器推到右边 -->
      <div class="header-spacer"></div>
      <!-- ✨ 引入我们的主题切换器组件 -->
      <ThemeToggle />
    </header>

    <main class="main-content">
      <div class="content-wrapper">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="项目管理" name="projects">
            <ProjectManager @switch-tab="switchToTab" />
          </el-tab-pane>
          <el-tab-pane label="凭证管理" name="credentials">
            <CredentialManager />
          </el-tab-pane>
          <el-tab-pane label="代理管理" name="proxies">
            <ProxyManager />
          </el-tab-pane>
          <el-tab-pane label="执行日志" name="logs">
            <LogViewer />
          </el-tab-pane>
        </el-tabs>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ProjectManager from '@/components/ProjectManager.vue'
import CredentialManager from '@/components/CredentialManager.vue'
import ProxyManager from '@/components/ProxyManager.vue'
import LogViewer from '@/components/LogViewer.vue'
// ✨ 引入主题切换器组件
import ThemeToggle from '@/components/ThemeToggle.vue'

const activeTab = ref('projects')

const switchToTab = (tabName) => {
  activeTab.value = tabName
}
</script>

<style scoped>
/* ✨ 在全局样式中定义的 .main-header 默认不是flex，我们在这里覆盖一下 */
.main-header {
  display: flex;
  align-items: center;
}

.header-spacer {
  flex-grow: 1; /* 这个div会占据所有剩余空间 */
}
</style>
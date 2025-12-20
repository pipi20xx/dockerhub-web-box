import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/services/api'
import { ElMessage } from 'element-plus'

export const useProjectStore = defineStore('projects', () => {
  const projects = ref([])
  const isLoading = ref(false)

  async function fetchProjects() {
    isLoading.value = true
    try {
      const response = await apiClient.get('/projects/')
      // ✨ 核心修改：为每个从API获取的项目对象添加一个默认的tag属性
      projects.value = response.data.map(p => ({ ...p, tag: 'latest' }))
    } catch (error) {
      console.error('Failed to fetch projects:', error)
      ElMessage.error('获取项目列表失败')
    } finally {
      isLoading.value = false
    }
  }
  
  async function startBuildTask(projectId, tag) {
    try {
        const response = await apiClient.post(`/tasks/execute/${projectId}?tag=${tag}`);
        ElMessage.success('构建任务已成功启动！');
        return response.data.task_id;
    } catch (error) {
        ElMessage.error(`任务启动失败: ${error.response?.data?.detail || error.message}`);
        return null;
    }
  }

  return { projects, isLoading, fetchProjects, startBuildTask }
})
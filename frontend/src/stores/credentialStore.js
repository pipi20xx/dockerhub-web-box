import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/services/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export const useCredentialStore = defineStore('credentials', () => {
  const credentials = ref([])
  const isLoading = ref(false)

  async function fetchCredentials() {
    isLoading.value = true
    try {
      const response = await apiClient.get('/credentials/')
      credentials.value = response.data
    } catch (error) {
      console.error('Failed to fetch credentials:', error)
      ElMessage.error('获取凭证列表失败')
    } finally {
      isLoading.value = false
    }
  }

  async function addCredential(credential) {
    try {
      await apiClient.post('/credentials/', credential)
      await fetchCredentials()
    } catch (error) {
      throw error
    }
  }

  async function updateCredential(id, credential) {
    try {
      await apiClient.put(`/credentials/${id}`, credential)
      await fetchCredentials()
    } catch (error) {
      throw error
    }
  }

  async function deleteCredential(id) {
    try {
      await apiClient.delete(`/credentials/${id}`)
      await fetchCredentials()
    } catch (error) {
      throw error
    }
  }

  return { credentials, fetchCredentials, addCredential, updateCredential, deleteCredential }
})
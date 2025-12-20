import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/services/api'

export const useProxyStore = defineStore('proxies', () => {
  const proxies = ref([])

  async function fetchProxies() {
    try {
      const response = await apiClient.get('/proxies/')
      proxies.value = response.data
    } catch (error) {
      console.error('Failed to fetch proxies:', error)
    }
  }

  async function addProxy(proxy) {
    try {
      await apiClient.post('/proxies/', proxy)
      await fetchProxies()
    } catch (error) {
      throw error
    }
  }

  async function updateProxy(id, proxy) {
    try {
      await apiClient.put(`/proxies/${id}`, proxy)
      await fetchProxies()
    } catch (error) {
      throw error
    }
  }

  async function deleteProxy(id) {
    try {
      await apiClient.delete(`/proxies/${id}`)
      await fetchProxies()
    } catch (error) {
      throw error
    }
  }

  return { proxies, fetchProxies, addProxy, updateProxy, deleteProxy }
})
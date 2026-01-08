import { defineStore } from 'pinia';
import api from '../services/api';

export const useRegistryStore = defineStore('registryStore', {
  state: () => ({
    registries: [],
    loading: false,
    error: null,
  }),
  actions: {
    async fetchRegistries() {
      this.loading = true;
      try {
        const response = await api.get('/registries/');
        this.registries = response.data;
      } catch (err) {
        this.error = 'Failed to fetch registries';
        console.error(err);
      } finally {
        this.loading = false;
      }
    },
    async addRegistry(registry) {
      try {
        const response = await api.post('/registries/', registry);
        this.registries.push(response.data);
        return response.data;
      } catch (err) {
        throw err;
      }
    },
    async updateRegistry(id, registry) {
      try {
        const response = await api.put(`/registries/${id}`, registry);
        const index = this.registries.findIndex((r) => r.id === id);
        if (index !== -1) {
          this.registries[index] = response.data;
        }
        return response.data;
      } catch (err) {
        throw err;
      }
    },
    async deleteRegistry(id) {
      try {
        await api.delete(`/registries/${id}`);
        this.registries = this.registries.filter((r) => r.id !== id);
      } catch (err) {
        throw err;
      }
    },
  },
});

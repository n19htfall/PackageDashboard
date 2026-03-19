import { acceptHMRUpdate, defineStore } from 'pinia'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || ''

export const useGlobalStore = defineStore('global', () => {
  return {
    backendUrl: apiBaseUrl,
  }
})

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useGlobalStore as any, import.meta.hot))

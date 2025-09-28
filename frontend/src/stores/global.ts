import { acceptHMRUpdate, defineStore } from 'pinia'

const DEFAULT_BACKEND_URL = import.meta.env.VITE_DEFAULT_BACKEND_URL as string

export const useGlobalStore = defineStore('global', () => {
  if (!localStorage.getItem('backendUrl') || localStorage.getItem('backendUrl') !== DEFAULT_BACKEND_URL)
    localStorage.setItem('backendUrl', DEFAULT_BACKEND_URL)
  const backendUrl = localStorage.getItem('backendUrl') || DEFAULT_BACKEND_URL
  function setBackendUrl(url: string) {
    localStorage.setItem('backendUrl', url)
  }
  return {
    backendUrl,
    setBackendUrl,
  }
})

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useGlobalStore as any, import.meta.hot))

import { useCounter } from '@vueuse/core'
import { ref } from 'vue'
import { useLoadingBar } from 'naive-ui'

/**
 * useLoading: wraps naive-ui's useLoadingBar
 * finishes when all loading calls are finished
 */
export function useLoading() {
  const bar = useLoadingBar()
  const loading = ref(false)
  const { inc, dec, get } = useCounter()

  function start() {
    // if is the first one, start
    if (!loading.value && get() === 0) {
      loading.value = true
      bar.start()
    }
    inc()
  }

  function finish() {
    dec()
    // if is the last one, finish
    if (loading.value && get() === 0) {
      loading.value = false
      bar.finish()
    }
  }

  function error() {
    dec()
    // if is the last one, error
    if (loading.value && get() === 0) {
      loading.value = false
      bar.error()
    }
  }

  return {
    isLoading: loading,
    startLoading: start,
    finishLoading: finish,
    errorLoading: error,
  }
}

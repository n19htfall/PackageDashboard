import type { MessageApiInjection } from 'naive-ui/es/message/src/MessageProvider'

export async function useFetch<T>(
  p: Promise<T>,
  messageProvider: MessageApiInjection,
  loadingProvider: { isLoading: boolean; startLoading: () => void; finishLoading: () => void; errorLoading: () => void },
) {
  loadingProvider.startLoading()
  try {
    loadingProvider.finishLoading()
    return await p
  }
  catch (e) {
    loadingProvider.errorLoading()
    showError(messageProvider, e as Error)
  }
  return null
}

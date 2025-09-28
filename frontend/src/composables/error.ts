import { useMessage } from 'naive-ui'
import { AxiosError } from 'axios'
import type { MessageApiInjection } from 'naive-ui/es/message/src/MessageProvider'

// showErrorMsg({
//     type: 'backend',
//     code: axiosError.status ?? '',
//     msg: 'Unable to retrieve data.',
//   })

export interface ErrorMsgProps {
  type: 'backend' | 'frontend'
  code: string
  msg: string
}

/** showErrorMsg: to keep api compatibility with soybean, discouraged */
export function showErrorMsg(e: ErrorMsgProps) {
  const message = useMessage()
  message.error(`[${e.type}] Error ${e.code}: ${e.msg}`)
}

export function showError(messager: MessageApiInjection, e: string | Error) {
  if (typeof e === 'string') {
    messager.error(e)
  }
  else if (e instanceof AxiosError && e.response?.data?.detail) {
    console.error(e.response?.data)
    messager.error(`${e.message}: ${e.response.data.detail}`)
  }
  else if (e instanceof Error && e.message) {
    console.error(e)
    messager.error(e.message)
  }
  else {
    console.error(e)
    messager.error(`Unknown error: ${e}`)
  }
}

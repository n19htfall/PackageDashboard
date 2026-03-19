import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'

export type RequestMethod = 'get' | 'post' | 'put' | 'delete'

export interface RequestParam {
  url: string
  method?: RequestMethod
  data?: any
  axiosConfig?: AxiosRequestConfig
  headers?: any
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || undefined

/**
   * async request
   * @param param - request param
   * @returns response data
   */
export async function asyncRequest<T>(param: RequestParam): Promise<T> {
  const { url } = param
  const method = param.method || 'get'
  const headers = param.headers || {}

  let response = null

  if (method === 'get' || method === 'delete') {
    response = await axios.request<T | ValidationError>(
      {
        url,
        baseURL: API_BASE_URL,
        params: param.data,
        method,
        headers,
        paramsSerializer: {
          indexes: null, // by default: false
        },
      })
  }
  else {
    response = await axios.request<T | ValidationError>(
      { url, baseURL: API_BASE_URL, data: param.data, method, headers })
  }

  // is status code 2xx?
  if (response?.status >= 200 && response?.status < 300) {
    return response.data as T
  }
  else if (response?.status === 422) {
    // should be a validation error
    const err = response.data as ValidationError
    throw new Error(`${err.loc}: ${err.msg}`)
  }
  else {
    throw new Error(`${response?.status}: ${response?.data}`)
  }
}

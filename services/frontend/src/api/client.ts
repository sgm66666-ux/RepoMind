import axios, { AxiosError } from 'axios'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
    public readonly code: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string; error?: string }>) => {
    if (!error.response) {
      return Promise.reject(new ApiError('Java Gateway is unavailable.', null, 'GATEWAY_UNAVAILABLE'))
    }
    const body = error.response.data
    const message = body?.detail || body?.message || `Request failed with status ${error.response.status}`
    return Promise.reject(new ApiError(message, error.response.status, body?.error || null))
  },
)

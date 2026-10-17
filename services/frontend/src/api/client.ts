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
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string; error?: string }>) => {
    if (!error.response) {
      return Promise.reject(new ApiError('FastAPI service is unavailable.', null, 'API_UNAVAILABLE'))
    }
    const body = error.response.data
    const message = body?.detail || body?.message || `Request failed with status ${error.response.status}`
    return Promise.reject(new ApiError(message, error.response.status, body?.error || null))
  },
)

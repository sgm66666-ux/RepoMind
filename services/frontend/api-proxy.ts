import type { ProxyOptions } from 'vite'

export function createApiProxy(target: string): Record<string, ProxyOptions> {
  return {
    '/api': {
      target,
      changeOrigin: true,
      configure(proxy) {
        proxy.on('error', (_error, _request, response) => {
          if ('writeHead' in response && !response.headersSent && !response.writableEnded) {
            response.writeHead(503, { 'Content-Type': 'application/json' })
            response.end(JSON.stringify({
              error: 'PYTHON_SERVICE_ERROR',
              message: 'Python service is unavailable',
            }))
          }
        })
      },
    },
  }
}

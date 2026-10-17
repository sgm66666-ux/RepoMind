// @vitest-environment node
import { createServer as createHttpServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { afterEach, describe, expect, it } from 'vitest'
import { createServer, resolveConfig, type ViteDevServer } from 'vite'
import { createApiProxy } from '../../api-proxy'

let vite: ViteDevServer | undefined
let upstream: Server | undefined

async function listen(server: Server): Promise<number> {
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  return (server.address() as AddressInfo).port
}

async function startProxy(target: string): Promise<string> {
  vite = await createServer({
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, cors: false, proxy: createApiProxy(target) },
  })
  await vite.listen()
  return `http://127.0.0.1:${(vite.httpServer!.address() as AddressInfo).port}`
}

afterEach(async () => {
  await vite?.close()
  vite = undefined
  if (upstream?.listening) await new Promise<void>((resolve) => upstream!.close(() => resolve()))
  upstream = undefined
})

describe('Vite to FastAPI transport', () => {
  it('does not broaden the backend CORS allowlist with Vite localhost defaults', async () => {
    const config = await resolveConfig({ logLevel: 'silent' }, 'serve')
    expect(config.server.host).toBe('127.0.0.1')
    expect(config.server.cors).toBe(false)
    expect(config.preview.host).toBe('127.0.0.1')
    expect(config.preview.cors).toBe(false)
    upstream = createHttpServer((_request, response) => {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify({ status: 'ok' }))
    })
    const base = await startProxy(`http://127.0.0.1:${await listen(upstream)}`)
    for (const origin of ['http://localhost:25374', 'https://untrusted.example']) {
      const response = await fetch(base + '/api/health', { headers: { Origin: origin } })
      expect(response.headers.get('access-control-allow-origin')).toBeNull()
    }
  })

  it('keeps browser paths, request bodies, query strings and successful JSON intact', async () => {
    const received: { url?: string; body?: string }[] = []
    upstream = createHttpServer((request, response) => {
      let body = ''
      request.on('data', (chunk) => { body += chunk })
      request.on('end', () => {
        received.push({ url: request.url, body })
        response.writeHead(200, { 'Content-Type': 'application/json' })
        response.end(JSON.stringify({ status: 'ok', unchanged: true }))
      })
    })
    const base = await startProxy(`http://127.0.0.1:${await listen(upstream)}`)
    const payload = { path: 'D:/源码/仓库' }
    const response = await fetch(base + '/api/repositories/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    })
    expect(await response.json()).toEqual({ status: 'ok', unchanged: true })
    const suffix = '/api/symbols/src%2FService.java%3A8%3AMETHOD%3Arun/callers?name=a%2Bb'
    expect((await fetch(base + suffix)).status).toBe(200)
    expect(received[0]).toEqual({ url: '/api/repositories/analyze', body: JSON.stringify(payload) })
    expect(received[1]?.url).toBe(suffix)
  })

  it('returns the existing structured 503 when FastAPI is unavailable', async () => {
    upstream = createHttpServer()
    const port = await listen(upstream)
    await new Promise<void>((resolve) => upstream!.close(() => resolve()))
    const base = await startProxy(`http://127.0.0.1:${port}`)
    const response = await fetch(base + '/api/health')
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({
      error: 'PYTHON_SERVICE_ERROR', message: 'Python service is unavailable',
    })
  })
})

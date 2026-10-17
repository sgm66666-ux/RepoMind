import MockAdapter from 'axios-mock-adapter'
import { afterEach, describe, expect, it } from 'vitest'
import { apiClient } from '../api/client'
import { repositoryApi } from '../api/repository'
import { analysisFixture } from './fixtures'

const mock = new MockAdapter(apiClient)

afterEach(() => mock.reset())

describe('API client', () => {
  it('posts the existing browser contract through the same-origin API', async () => {
    expect(apiClient.defaults.baseURL).toBe('')
    mock.onPost('/api/repositories/analyze', { path: 'D:/repo' }).reply(200, analysisFixture)
    await expect(repositoryApi.analyze('D:/repo')).resolves.toEqual(analysisFixture)
  })

  it('normalizes an offline API error', async () => {
    mock.onPost('/api/repositories/analyze').networkError()
    await expect(repositoryApi.analyze('D:/repo')).rejects.toMatchObject({
      message: 'FastAPI service is unavailable.',
      code: 'API_UNAVAILABLE',
    })
  })

  it('preserves FastAPI provider errors using the browser envelope', async () => {
    mock.onPost('/api/repositories/analyze').reply(503, {
      error: 'PYTHON_SERVICE_ERROR', message: 'No LLM provider configured',
    })
    await expect(repositoryApi.analyze('D:/repo')).rejects.toMatchObject({
      status: 503, message: 'No LLM provider configured', code: 'PYTHON_SERVICE_ERROR',
    })
  })
})

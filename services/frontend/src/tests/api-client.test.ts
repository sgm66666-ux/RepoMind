import MockAdapter from 'axios-mock-adapter'
import { afterEach, describe, expect, it } from 'vitest'
import { apiClient } from '../api/client'
import { repositoryApi } from '../api/repository'
import { analysisFixture } from './fixtures'

const mock = new MockAdapter(apiClient)

afterEach(() => mock.reset())

describe('API client', () => {
  it('posts repository analysis to the Java Gateway', async () => {
    mock.onPost('/api/repositories/analyze', { path: 'D:/repo' }).reply(200, analysisFixture)
    await expect(repositoryApi.analyze('D:/repo')).resolves.toEqual(analysisFixture)
  })

  it('normalizes an offline Java Gateway error', async () => {
    mock.onPost('/api/repositories/analyze').networkError()
    await expect(repositoryApi.analyze('D:/repo')).rejects.toMatchObject({
      message: 'Java Gateway is unavailable.',
      code: 'GATEWAY_UNAVAILABLE',
    })
  })
})

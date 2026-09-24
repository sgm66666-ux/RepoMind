import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RepositoryView from '../views/RepositoryView.vue'
import { repositoryApi } from '../api/repository'
import { symbolsApi } from '../api/symbols'
import { graphApi } from '../api/graph'
import { analysisFixture, controllerSymbol, graphFixture } from './fixtures'

vi.mock('../api/repository', () => ({ repositoryApi: { analyze: vi.fn() } }))
vi.mock('../api/symbols', () => ({ symbolsApi: { list: vi.fn() } }))
vi.mock('../api/graph', () => ({ graphApi: { get: vi.fn() } }))
vi.mock('../api/demo', () => ({ demoApi: { getOrderDemo: vi.fn() } }))

beforeEach(() => {
  vi.mocked(repositoryApi.analyze).mockResolvedValue(analysisFixture)
  vi.mocked(symbolsApi.list).mockResolvedValue([controllerSymbol])
  vi.mocked(graphApi.get).mockResolvedValue(graphFixture)
})

describe('Repository page', () => {
  it('analyzes an entered path and renders real returned counts', async () => {
    const wrapper = mount(RepositoryView, { global: { plugins: [createPinia()] } })
    await wrapper.find('input').setValue('D:/repo')
    const analyzeButton = wrapper.findAll('button').find((button) => button.text() === '开始分析')
    await analyzeButton?.trigger('click')
    await flushPromises()

    expect(repositoryApi.analyze).toHaveBeenCalledWith('D:/repo')
    expect(wrapper.text()).toContain('14')
    expect(wrapper.text()).toContain('Resolved Calls')
  })
})

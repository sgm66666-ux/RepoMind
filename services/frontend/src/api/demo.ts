import { apiClient } from './client'
import type { DemoInfo } from '../models'

export const demoApi = {
  async getOrderDemo(): Promise<DemoInfo> {
    const { data } = await apiClient.get<DemoInfo>('/api/demo/order-demo')
    return data
  },
}

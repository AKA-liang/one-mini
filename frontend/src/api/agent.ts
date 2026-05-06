import api from './index'

export interface AgentDTO {
  id?: number
  name: string
  role: string
  position: string
  avatar?: string
  status?: string
  currentTask?: string
  recentOutput?: string
  isOnDuty?: boolean
  schedule?: string
  category: string
  skills?: string
  tasksCompleted?: number
  accuracy?: string
  avgResponseTime?: string
  prompt?: string
}

export interface AgentVO {
  id: number
  name: string
  role: string
  position: string
  avatar: string
  status: string
  currentTask: string
  recentOutput: string
  isOnDuty: boolean
  schedule: string
  category: string
  skills: string
  tasksCompleted: number
  accuracy: string
  avgResponseTime: string
  prompt: string
  createTime: string
  updateTime: string
}

export const agentApi = {
  list(category?: string) {
    return api.get<AgentVO[]>('/agents', { params: { category } })
  },
  getById(id: number) {
    return api.get<AgentVO>(`/agents/${id}`)
  },
  create(data: AgentDTO) {
    return api.post<AgentVO>('/agents', data)
  },
  update(id: number, data: Partial<AgentDTO>) {
    return api.put<AgentVO>(`/agents/${id}`, data)
  },
  delete(id: number) {
    return api.delete(`/agents/${id}`)
  }
}
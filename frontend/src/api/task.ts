import api from './index'

export interface CreateTaskDTO {
  type: 'product_analysis' | 'finance_review'
  inputJson: Record<string, unknown>
}

export interface TaskStepVO {
  id: number
  taskId: string
  agentName: string
  status: string
  inputJson: string
  outputJson: string
  errorMessage: string
  createdAt: string
  updatedAt: string
}

export interface TaskVO {
  id: number
  taskId: string
  traceId: string
  type: string
  status: string
  inputJson: string
  outputJson: string
  steps: TaskStepVO[]
  createTime: string
  updateTime: string
}

export interface AgentLogVO {
  id: number
  taskId: string
  agentName: string
  action: string
  level: string
  message: string
  createdAt: string
}

export const taskApi = {
  create(data: CreateTaskDTO) {
    return api.post<TaskVO>('/tasks', data)
  },
  getById(taskId: string) {
    return api.get<TaskVO>(`/tasks/${taskId}`)
  },
  list(params?: { type?: string; status?: string }) {
    return api.get<TaskVO[]>('/tasks', { params })
  }
}

export const logApi = {
  list(taskId?: string) {
    return api.get<AgentLogVO[]>('/agent-logs', { params: { taskId } })
  }
}
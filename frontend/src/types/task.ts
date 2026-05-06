export interface Task {
  id: number
  taskId: string
  traceId: string
  type: string
  status: string
  inputJson: string
  outputJson: string
  steps: TaskStep[]
  createdAt: string
  updatedAt: string
}

export interface TaskStep {
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

export interface AgentLog {
  id: number
  taskId: string
  agentName: string
  action: string
  level: string
  message: string
  createdAt: string
}

export const taskTypeMap: Record<string, { label: string; icon: string }> = {
  product_analysis: { label: '选品分析', icon: '🔍' },
  finance_review: { label: '财务审核', icon: '💰' }
}

export const taskStatusMap: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: '#8e8e93' },
  running: { label: '运行中', color: '#007aff' },
  completed: { label: '已完成', color: '#34c759' },
  failed: { label: '失败', color: '#ff3b30' }
}
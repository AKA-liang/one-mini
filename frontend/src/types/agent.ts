export interface Agent {
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
}

export interface Category {
  id: string
  name: string
  icon: string
  description: string
}

export interface Boss {
  name: string
  position: string
  email: string
  phone: string
  department: string
  avatar: string
  bio: string
  joinDate: string
  teamSize: number
  projectsCompleted: number
  efficiency: string
}

export const statusMap: Record<string, { label: string; color: string; bgColor: string }> = {
  working: { label: '工作中', color: '#34c759', bgColor: '#d4edda' },
  online: { label: '在线', color: '#007aff', bgColor: '#d1ecf1' },
  offline: { label: '离线', color: '#8e8e93', bgColor: '#e5e5ea' },
  busy: { label: '忙碌', color: '#ff9500', bgColor: '#fff3cd' }
}
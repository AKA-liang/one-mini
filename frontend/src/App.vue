<template>
  <div class="min-h-screen bg-gradient-dark">
    <!-- Top Navigation -->
    <nav class="sticky top-0 z-50 glass-card border-b border-white/5 rounded-none">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
              <Zap :size="18" class="text-white" />
            </div>
            <span class="text-lg font-bold gradient-text">One Mini</span>
            <span class="text-xs text-gray-500 hidden sm:inline">智能体协作平台</span>
          </div>
          <div class="flex items-center gap-1">
            <button
              v-for="nav in navItems"
              :key="nav.key"
              @click="currentView = nav.key"
              :class="[
                'px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                currentView === nav.key
                  ? 'bg-primary-500/20 text-primary-300'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
              ]"
            >
              <component :is="nav.icon" :size="16" class="inline mr-1.5" />
              {{ nav.label }}
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <DashboardView
        v-if="currentView === 'dashboard'"
        :agents="agents"
        :categories="categoriesList"
        :selectedCategory="selectedCategory"
        @select-category="selectedCategory = $event"
        @card-click="selectedAgent = $event"
      />
      <TaskBoardView v-if="currentView === 'tasks'" />
    </main>

    <!-- Agent Detail Slide Panel -->
    <Transition name="slide-up">
      <AgentDetail
        v-if="selectedAgent"
        :agent="selectedAgent"
        @close="selectedAgent = null"
      />
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agentApi } from './api/agent'
import type { Agent } from './types/agent'
import DashboardView from './views/Dashboard.vue'
import TaskBoardView from './views/TaskBoard.vue'
import AgentDetail from './components/AgentDetail.vue'
import { Zap, LayoutDashboard, ClipboardList } from 'lucide-vue-next'

import { categories } from './data/agents'

const categoriesList = categories
const currentView = ref<'dashboard' | 'tasks'>('tasks')
const selectedCategory = ref('all')
const selectedAgent = ref<Agent | null>(null)
const agents = ref<Agent[]>([])

const navItems = [
  { key: 'dashboard' as const, label: '工作台', icon: LayoutDashboard },
  { key: 'tasks' as const, label: '任务中心', icon: ClipboardList },
]

onMounted(async () => {
  try {
    const res = await agentApi.list()
    agents.value = res.data || []
  } catch {
    agents.value = []
  }
})
</script>
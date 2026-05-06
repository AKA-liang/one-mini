<template>
  <div class="glass-card-hover p-6 cursor-pointer" @click="$emit('click', agent)">
    <div class="flex items-center gap-3.5 mb-4">
      <img :src="agent.avatar" :alt="agent.name" class="w-14 h-14 rounded-2xl object-cover" />
      <div class="flex-1 min-w-0">
        <h3 class="text-lg font-bold text-white m-0">{{ agent.name }}</h3>
        <span class="text-sm text-gray-400 font-medium">{{ agent.role }}</span>
      </div>
      <span :class="['px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap', statusClass]">
        {{ statusLabel }}
      </span>
    </div>

    <p class="text-sm text-gray-300 mb-4 leading-relaxed">{{ agent.position }}</p>

    <div v-if="agent.currentTask" class="flex items-center gap-2 mb-2 text-sm">
      <span class="text-gray-500 font-medium whitespace-nowrap">当前任务</span>
      <span class="text-gray-200 font-medium">{{ agent.currentTask }}</span>
    </div>

    <div v-if="agent.recentOutput" class="flex items-center gap-2 mb-2 text-sm">
      <span class="text-gray-500 font-medium whitespace-nowrap">近期产出</span>
      <span class="text-gray-200 font-medium">{{ agent.recentOutput }}</span>
    </div>

    <div class="flex items-center gap-4 mt-4 pt-4 border-t border-white/5">
      <div class="flex flex-col items-center gap-0.5">
        <span class="text-base font-bold text-white">{{ agent.tasksCompleted }}</span>
        <span class="text-xs text-gray-500">任务</span>
      </div>
      <div class="flex flex-col items-center gap-0.5">
        <span class="text-base font-bold text-white">{{ agent.accuracy }}</span>
        <span class="text-xs text-gray-500">准确率</span>
      </div>
      <div class="flex flex-col items-center gap-0.5">
        <span class="text-base font-bold text-white">{{ agent.avgResponseTime }}</span>
        <span class="text-xs text-gray-500">响应</span>
      </div>
      <button class="ml-auto btn-primary text-xs px-3 py-1.5" @click.stop="$emit('edit', agent)">
        编辑
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Agent } from '../types/agent'
import { statusMap } from '../types/agent'

const props = defineProps<{ agent: Agent }>()

defineEmits<{
  click: [agent: Agent]
  edit: [agent: Agent]
}>()

const statusLabel = computed(() => {
  return statusMap[props.agent.status]?.label || props.agent.status
})

const statusClass = computed(() => {
  const map: Record<string, string> = {
    working: 'bg-emerald-500/20 text-emerald-400',
    online: 'bg-primary-500/20 text-primary-400',
    offline: 'bg-gray-500/20 text-gray-500',
    busy: 'bg-amber-500/20 text-amber-400',
  }
  return map[props.agent.status] || 'bg-gray-500/20 text-gray-400'
})
</script>
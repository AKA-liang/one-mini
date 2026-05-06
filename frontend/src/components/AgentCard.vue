<template>
  <div class="agent-card" @click="$emit('click', agent)">
    <div class="card-header">
      <img :src="agent.avatar" :alt="agent.name" class="agent-avatar" />
      <div class="agent-info">
        <h3 class="agent-name">{{ agent.name }}</h3>
        <span class="agent-role">{{ agent.role }}</span>
      </div>
      <span :class="['agent-status', agent.status]">{{ statusLabel }}</span>
    </div>

    <p class="agent-position">{{ agent.position }}</p>

    <div class="agent-task" v-if="agent.currentTask">
      <span class="task-label">当前任务</span>
      <span class="task-value">{{ agent.currentTask }}</span>
    </div>

    <div class="agent-output" v-if="agent.recentOutput">
      <span class="output-label">近期产出</span>
      <span class="output-value">{{ agent.recentOutput }}</span>
    </div>

    <div class="card-footer">
      <div class="stat">
        <span class="stat-value">{{ agent.tasksCompleted }}</span>
        <span class="stat-label">任务</span>
      </div>
      <div class="stat">
        <span class="stat-value">{{ agent.accuracy }}</span>
        <span class="stat-label">准确率</span>
      </div>
      <div class="stat">
        <span class="stat-value">{{ agent.avgResponseTime }}</span>
        <span class="stat-label">响应</span>
      </div>
      <button class="edit-btn" @click.stop="$emit('edit', agent)">
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
</script>

<style scoped>
.agent-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;
}

.agent-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.agent-avatar {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  object-fit: cover;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 18px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0 0 2px;
}

.agent-role {
  font-size: 13px;
  color: #86868b;
  font-weight: 500;
}

.agent-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.agent-status.working { background: #d4edda; color: #34c759; }
.agent-status.online { background: #d1ecf1; color: #007aff; }
.agent-status.offline { background: #e5e5ea; color: #8e8e93; }
.agent-status.busy { background: #fff3cd; color: #ff9500; }

.agent-position {
  font-size: 14px;
  color: #495057;
  margin-bottom: 16px;
  line-height: 1.5;
}

.agent-task,
.agent-output {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.task-label,
.output-label {
  color: #86868b;
  font-weight: 500;
  white-space: nowrap;
}

.task-value,
.output-value {
  color: #1d1d1f;
  font-weight: 500;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: #1d1d1f;
}

.stat-label {
  font-size: 11px;
  color: #86868b;
}

.edit-btn {
  margin-left: auto;
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.edit-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
</style>
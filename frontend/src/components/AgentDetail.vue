<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="detail-panel">
      <div class="detail-header">
        <img :src="agent.avatar" :alt="agent.name" class="detail-avatar" />
        <div class="detail-info">
          <h2 class="detail-name">{{ agent.name }}</h2>
          <span class="detail-role">{{ agent.role }}</span>
          <span :class="['detail-status', agent.status]">{{ statusLabel }}</span>
        </div>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="detail-body">
        <div class="detail-section">
          <h3>岗位职责</h3>
          <p>{{ agent.position }}</p>
        </div>

        <div class="detail-section">
          <h3>技能标签</h3>
          <div class="skill-tags">
            <span v-for="skill in agent.skills.split(',')" :key="skill" class="skill-tag">
              {{ skill.trim() }}
            </span>
          </div>
        </div>

        <div class="detail-section">
          <h3>当前任务</h3>
          <p>{{ agent.currentTask }}</p>
        </div>

        <div class="detail-section">
          <h3>近期产出</h3>
          <p>{{ agent.recentOutput }}</p>
        </div>

        <div class="detail-section">
          <h3>工作时段</h3>
          <p>{{ agent.schedule }}</p>
        </div>

        <div class="detail-section">
          <h3>绩效数据</h3>
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ agent.tasksCompleted }}</span>
              <span class="stat-label">完成任务</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ agent.accuracy }}</span>
              <span class="stat-label">准确率</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ agent.avgResponseTime }}</span>
              <span class="stat-label">平均响应</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="agent.prompt">
          <h3>角色提示词</h3>
          <div class="prompt-box">{{ agent.prompt }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Agent } from '../types/agent'
import { statusMap } from '../types/agent'

const props = defineProps<{ agent: Agent }>()
defineEmits<{ close: [] }>()

const statusLabel = computed(() => {
  return statusMap[props.agent.status]?.label || props.agent.status
})
</script>

<style scoped>
.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
}

.detail-panel {
  width: 480px;
  max-width: 100%;
  background: #ffffff;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.detail-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 32px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
}

.detail-avatar {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
}

.detail-info {
  flex: 1;
}

.detail-name {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 4px;
}

.detail-role {
  display: block;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 8px;
}

.detail-status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  color: #ffffff;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.detail-body {
  padding: 32px;
}

.detail-section {
  margin-bottom: 28px;
}

.detail-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.detail-section p {
  font-size: 15px;
  color: #1d1d1f;
  line-height: 1.6;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag {
  padding: 6px 14px;
  background: linear-gradient(135deg, #f0f2f5 0%, #e9ecef 100%);
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: #495057;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.stat-card .stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #667eea;
}

.stat-card .stat-label {
  display: block;
  font-size: 12px;
  color: #86868b;
  margin-top: 4px;
}

.prompt-box {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 16px;
  font-size: 13px;
  line-height: 1.8;
  color: #495057;
  border: 1px solid rgba(0, 0, 0, 0.06);
  max-height: 300px;
  overflow-y: auto;
}
</style>
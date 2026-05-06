<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="form-panel">
      <div class="form-header">
        <h2>{{ agent ? '编辑智能体' : '添加智能体' }}</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="form-body">
        <div class="form-group">
          <label>名称</label>
          <input v-model="form.name" type="text" placeholder="输入智能体名称" />
        </div>

        <div class="form-group">
          <label>分类</label>
          <select v-model="form.category">
            <option v-for="cat in categoryOptions" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>职位</label>
          <input v-model="form.position" type="text" placeholder="输入岗位职责" />
        </div>

        <div class="form-group">
          <label>技能标签</label>
          <input v-model="form.skills" type="text" placeholder="技能1, 技能2, ..." />
        </div>

        <div class="form-group">
          <label>角色提示词</label>
          <textarea v-model="form.prompt" placeholder="输入AI角色提示词" rows="4"></textarea>
        </div>

        <div class="form-group">
          <label>工作时段</label>
          <input v-model="form.schedule" type="text" placeholder="08:00-20:00" />
        </div>
      </div>

      <div class="form-footer">
        <button class="btn-secondary" @click="$emit('close')">取消</button>
        <button v-if="agent" class="btn-danger" @click="$emit('delete', agent.id)">删除</button>
        <button class="btn-primary" @click="handleSave">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'
import type { Agent } from '../types/agent'

const props = defineProps<{
  agent: Agent | null
  categories: Array<{ id: string; name: string }>
}>()

const emit = defineEmits<{
  close: []
  save: [data: Partial<Agent>]
  delete: [id: number]
}>()

const categoryOptions = computed(() => {
  return props.categories
})

const form = reactive({
  name: props.agent?.name || '',
  category: props.agent?.category || 'ecommerce',
  position: props.agent?.position || '',
  skills: props.agent?.skills || '',
  prompt: props.agent?.prompt || '',
  schedule: props.agent?.schedule || '09:00-18:00'
})

function handleSave() {
  emit('save', { ...form })
}
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
  justify-content: center;
  align-items: center;
}

.form-panel {
  width: 520px;
  max-width: 90vw;
  max-height: 90vh;
  background: #ffffff;
  border-radius: 20px;
  overflow-y: auto;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.form-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  background: #f8f9fa;
  border: none;
  border-radius: 50%;
  color: #86868b;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #e9ecef;
}

.form-body {
  padding: 24px 32px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 16px;
  border: 2px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  font-size: 14px;
  transition: border-color 0.2s;
  outline: none;
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #667eea;
}

.form-body {
  max-height: 60vh;
  overflow-y: auto;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 32px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: 10px 24px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #f8f9fa;
  color: #495057;
}

.btn-secondary:hover {
  background: #e9ecef;
}

.btn-danger {
  background: #ff3b30;
  color: #ffffff;
  margin-right: auto;
}

.btn-danger:hover {
  background: #ff453a;
}
</style>
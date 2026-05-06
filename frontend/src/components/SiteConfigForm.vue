<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="config-panel">
      <div class="config-header">
        <h2>站点配置</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>
      <div class="config-body">
        <div class="form-group">
          <label>站点名称</label>
          <input v-model="form.siteName" type="text" placeholder="输入站点名称" />
        </div>
        <div class="form-group">
          <label>站点副标题</label>
          <input v-model="form.siteSubtitle" type="text" placeholder="输入站点副标题" />
        </div>
      </div>
      <div class="config-footer">
        <button class="btn-secondary" @click="$emit('close')">取消</button>
        <button class="btn-primary" @click="$emit('update', { ...form })">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

defineEmits<{
  close: []
  update: [data: { siteName: string; siteSubtitle: string }]
}>()

const form = reactive({
  siteName: '',
  siteSubtitle: ''
})
</script>

<style scoped>
.overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.config-panel {
  width: 480px;
  max-width: 90vw;
  background: #ffffff;
  border-radius: 20px;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.config-header h2 { font-size: 20px; font-weight: 700; color: #1d1d1f; margin: 0; }

.close-btn {
  width: 32px; height: 32px;
  background: #f8f9fa; border: none; border-radius: 50%;
  color: #86868b; font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}

.config-body { padding: 24px 32px; }

.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-size: 14px; font-weight: 600; color: #1d1d1f; margin-bottom: 8px; }
.form-group input {
  width: 100%; padding: 10px 16px;
  border: 2px solid rgba(0, 0, 0, 0.06); border-radius: 10px;
  font-size: 14px; outline: none;
}
.form-group input:focus { border-color: #667eea; }

.config-footer {
  display: flex; justify-content: flex-end; gap: 12px;
  padding: 20px 32px; border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.btn-primary, .btn-secondary {
  padding: 10px 24px; border: none; border-radius: 10px;
  cursor: pointer; font-size: 14px; font-weight: 600;
  transition: all 0.3s ease;
}
.btn-primary { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(102,126,234,0.4); }
.btn-secondary { background: #f8f9fa; color: #495057; }
</style>
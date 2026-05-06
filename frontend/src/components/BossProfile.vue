<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="profile-panel">
      <div class="profile-header">
        <img :src="boss.avatar || defaultAvatar" :alt="boss.name" class="profile-avatar" />
        <div class="profile-info">
          <h2>{{ boss.name || '管理员' }}</h2>
          <p>{{ boss.position }}</p>
          <p class="dept">{{ boss.department }}</p>
        </div>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="profile-body">
        <div class="profile-stats">
          <div class="profile-stat">
            <span class="stat-value">{{ boss.teamSize }}</span>
            <span class="stat-label">团队成员</span>
          </div>
          <div class="profile-stat">
            <span class="stat-value">{{ boss.projectsCompleted }}</span>
            <span class="stat-label">完成项目</span>
          </div>
          <div class="profile-stat">
            <span class="stat-value">{{ boss.efficiency }}</span>
            <span class="stat-label">运营效率</span>
          </div>
        </div>

        <div class="profile-section">
          <p class="profile-bio">{{ boss.bio }}</p>
        </div>

        <div class="profile-section">
          <div class="profile-row">
            <span class="row-label">邮箱</span>
            <span class="row-value">{{ boss.email }}</span>
          </div>
          <div class="profile-row">
            <span class="row-label">电话</span>
            <span class="row-value">{{ boss.phone }}</span>
          </div>
          <div class="profile-row">
            <span class="row-label">入职日期</span>
            <span class="row-value">{{ boss.joinDate }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  boss: {
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
}>()

defineEmits<{ close: [] }>()

const defaultAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=boss&backgroundColor=c0aede&radius=50'
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

.profile-panel {
  width: 480px;
  max-width: 90vw;
  background: #ffffff;
  border-radius: 20px;
  overflow-y: auto;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.profile-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 32px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
}

.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.3);
}

.profile-info h2 {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 4px;
}

.profile-info p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.profile-info .dept {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
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
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.profile-body {
  padding: 24px 32px;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.profile-stat {
  text-align: center;
  padding: 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.profile-stat .stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #667eea;
}

.profile-stat .stat-label {
  display: block;
  font-size: 12px;
  color: #86868b;
  margin-top: 4px;
}

.profile-section {
  margin-bottom: 20px;
}

.profile-bio {
  font-size: 14px;
  color: #495057;
  line-height: 1.6;
}

.profile-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.row-label {
  font-size: 14px;
  color: #86868b;
}

.row-value {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}
</style>
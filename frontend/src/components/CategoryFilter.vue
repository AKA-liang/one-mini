<template>
  <div class="category-filter">
    <button
      v-for="cat in categories"
      :key="cat.id"
      :class="['cat-btn', { active: selected === cat.id }]"
      @click="$emit('select', cat.id)"
    >
      <span class="cat-icon">{{ cat.icon }}</span>
      <span class="cat-name">{{ cat.name }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  categories: Array<{ id: string; name: string; icon: string; description: string }>
  selected: string
}>()

defineEmits<{
  select: [id: string]
}>()
</script>

<style scoped>
.category-filter {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.cat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: #ffffff;
  border: 2px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
  font-weight: 500;
  color: #495057;
}

.cat-btn:hover {
  border-color: #667eea;
  color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.cat-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.cat-icon {
  font-size: 18px;
}

.cat-name {
  font-weight: 600;
}
</style>
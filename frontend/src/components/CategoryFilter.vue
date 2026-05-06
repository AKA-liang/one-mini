<template>
  <div class="flex flex-wrap gap-3">
    <button
      v-for="cat in categories"
      :key="cat.id"
      :class="[
        'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300',
        selected === cat.id
          ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/25'
          : 'bg-surface-200/50 text-gray-300 border border-white/10 hover:border-primary-400/40 hover:text-primary-400 hover:-translate-y-0.5'
      ]"
      @click="$emit('select', cat.id)"
    >
      <span class="text-lg">{{ cat.icon }}</span>
      <span class="font-semibold">{{ cat.name }}</span>
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
<template>
  <div class="dashboard">
    <CategoryFilter
      :categories="categories"
      :selected="selectedCategory"
      @select="$emit('selectCategory', $event)"
    />
    <div class="agents-grid">
      <AgentCard
        v-for="agent in filteredAgents"
        :key="agent.id"
        :agent="agent"
        @click="$emit('cardClick', agent)"
        @edit="$emit('editAgent', agent)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Agent } from '../types/agent'
import CategoryFilter from '../components/CategoryFilter.vue'
import AgentCard from '../components/AgentCard.vue'

const props = defineProps<{
  agents: Agent[]
  categories: Array<{ id: string; name: string; icon: string; description: string }>
  selectedCategory: string
}>()

defineEmits<{
  selectCategory: [category: string]
  cardClick: [agent: Agent]
  editAgent: [agent: Agent]
}>()

const filteredAgents = computed(() => {
  if (props.selectedCategory === 'all') return props.agents
  return props.agents.filter(a => a.category === props.selectedCategory)
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 24px;
  margin-top: 32px;
}

@media (max-width: 768px) {
  .agents-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
</style>
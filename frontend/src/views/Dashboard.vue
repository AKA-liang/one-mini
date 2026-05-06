<template>
  <div class="w-full">
    <CategoryFilter
      :categories="categories"
      :selected="selectedCategory"
      @select="$emit('selectCategory', $event)"
    />
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mt-8">
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
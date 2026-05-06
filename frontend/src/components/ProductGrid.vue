<template>
  <div class="space-y-4">
    <h4 class="text-sm font-medium text-gray-300 flex items-center gap-2">
      <TrendingUp :size="16" class="text-primary-400" />
      选品推荐 ({{ products.length }} 个商品)
    </h4>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <div
        v-for="(product, idx) in products"
        :key="idx"
        class="glass-card-hover p-4"
      >
        <!-- Product Name -->
        <div class="font-medium text-white text-sm mb-2 line-clamp-2">
          {{ product.name || product.title || '未知商品' }}
        </div>

        <!-- Category & Score -->
        <div class="flex items-center gap-2 mb-3">
          <span v-if="product.category" class="px-2 py-0.5 rounded text-xs bg-primary-500/20 text-primary-300">
            {{ product.category }}
          </span>
          <span v-if="product.potential_score" class="flex items-center gap-1 text-xs">
            <Star :size="12" class="text-yellow-400" />
            <span class="text-yellow-300 font-medium">{{ product.potential_score }}/10</span>
          </span>
        </div>

        <!-- Price Range -->
        <div v-if="product.price_range || product.selling_price" class="text-sm text-emerald-400 mb-2">
          💰 {{ product.price_range || `¥${product.selling_price}` }}
        </div>

        <!-- Metrics -->
        <div class="grid grid-cols-2 gap-2 text-xs text-gray-400 mb-3">
          <div v-if="product.competition_level">
            竞争: <span :class="levelColor(product.competition_level)">{{ product.competition_level }}</span>
          </div>
          <div v-if="product.supply_difficulty">
            供应: <span :class="levelColor(product.supply_difficulty)">{{ product.supply_difficulty }}</span>
          </div>
          <div v-if="product.roi_expectation">
            ROI: <span class="text-emerald-400">{{ product.roi_expectation }}</span>
          </div>
          <div v-if="product.target_audience">
            客群: {{ product.target_audience?.slice(0, 10) }}
          </div>
        </div>

        <!-- Risk & Promotion (collapsible) -->
        <div v-if="product.risk_notes || product.promotion_suggestion" class="border-t border-white/5 pt-2 mt-2">
          <p v-if="product.risk_notes" class="text-xs text-red-400/80 line-clamp-1">
            ⚠️ {{ product.risk_notes }}
          </p>
          <p v-if="product.promotion_suggestion" class="text-xs text-primary-300/80 line-clamp-1 mt-1">
            💡 {{ product.promotion_suggestion }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { TrendingUp, Star } from 'lucide-vue-next'

defineProps<{
  products: any[]
}>()

function levelColor(level: string): string {
  const map: Record<string, string> = {
    '低': 'text-emerald-400',
    '中': 'text-yellow-400',
    '高': 'text-red-400',
  }
  return map[level] || 'text-gray-400'
}
</script>
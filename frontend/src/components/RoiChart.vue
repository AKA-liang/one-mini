<template>
  <div class="glass-card p-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h4 class="text-sm font-medium text-gray-300 flex items-center gap-2">
          <BarChart3 :size="16" class="text-primary-400" />
          ROI 分析
        </h4>
        <p class="text-xs text-gray-500 mt-1">基于已完成的选品与审核数据</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-for="mode in chartModes"
          :key="mode.key"
          :class="[
            'px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200',
            activeMode === mode.key
              ? 'bg-primary-500/20 text-primary-300'
              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
          ]"
          @click="activeMode = mode.key"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-3 gap-3 mb-5">
      <div class="bg-surface-200/30 rounded-xl p-3">
        <div v-if="loading" class="h-6 w-16 bg-surface-200/50 rounded animate-pulse"></div>
        <div v-else class="text-xl font-bold" :class="avgRoi >= 0 ? 'text-emerald-400' : 'text-red-400'">
          {{ avgRoi >= 0 ? '+' : '' }}{{ avgRoi.toFixed(1) }}x
        </div>
        <div class="text-xs text-gray-500 mt-0.5">平均 ROI</div>
      </div>
      <div class="bg-surface-200/30 rounded-xl p-3">
        <div v-if="loading" class="h-6 w-16 bg-surface-200/50 rounded animate-pulse"></div>
        <div v-else class="text-xl font-bold text-primary-400">{{ completedCount }}</div>
        <div class="text-xs text-gray-500 mt-0.5">已完成任务</div>
      </div>
      <div class="bg-surface-200/30 rounded-xl p-3">
        <div v-if="loading" class="h-6 w-16 bg-surface-200/50 rounded animate-pulse"></div>
        <div v-else class="text-xl font-bold text-amber-400">{{ highPotentialCount }}</div>
        <div class="text-xs text-gray-500 mt-0.5">高潜力商品</div>
      </div>
    </div>

    <!-- Chart Area -->
    <div v-if="loading" class="h-64 flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></div>
    </div>
    <div v-else-if="chartData.products.length === 0" class="h-64 flex flex-col items-center justify-center">
      <BarChart3 :size="48" class="text-gray-600" />
      <p class="text-gray-400 mt-3">暂无 ROI 数据</p>
      <p class="text-xs text-gray-500 mt-1">完成选品任务后自动生成</p>
    </div>
    <div v-else class="relative" style="height: 280px;">
      <Bar :data="barData" :options="barOptions" />
    </div>

    <!-- Product ROI Ranking -->
    <div v-if="chartData.products.length > 0" class="mt-4 border-t border-white/5 pt-4">
      <h5 class="text-xs text-gray-500 mb-3">ROI 排行</h5>
      <div class="space-y-2">
        <div
          v-for="(p, idx) in topProducts"
          :key="idx"
          class="flex items-center gap-3 p-2.5 rounded-lg bg-surface-200/20 hover:bg-surface-200/40 transition-colors"
        >
          <span class="w-5 h-5 flex items-center justify-center rounded-md text-xs font-bold"
            :class="idx < 3 ? 'bg-primary-500/20 text-primary-400' : 'bg-gray-500/20 text-gray-500'">
            {{ idx + 1 }}
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-sm text-gray-200 truncate">{{ p.name }}</div>
            <div class="text-xs text-gray-500">{{ p.category }}</div>
          </div>
          <div class="text-sm font-bold" :class="p.roiValue >= 2.5 ? 'text-emerald-400' : p.roiValue >= 1.5 ? 'text-amber-400' : 'text-red-400'">
            {{ p.roiValue.toFixed(1) }}x
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { BarChart3 } from 'lucide-vue-next'
import { taskApi, type TaskVO } from '../api/task'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

interface ProductROI {
  name: string
  category: string
  roiValue: number
  potentialScore: number
  competitionLevel: string
}

const loading = ref(true)
const tasks = ref<TaskVO[]>([])
const activeMode = ref<'roi' | 'score' | 'competition'>('roi')

const chartModes = [
  { key: 'roi' as const, label: 'ROI' },
  { key: 'score' as const, label: '潜力分' },
  { key: 'competition' as const, label: '竞争度' },
]

const chartData = computed(() => {
  const products: ProductROI[] = []
  for (const task of tasks.value) {
    if (task.status !== 'completed' || !task.outputJson) continue
    try {
      const data = JSON.parse(task.outputJson)
      if (Array.isArray(data.products)) {
        for (const p of data.products) {
          const roiStr = (p.roi_expectation || '').replace(/[^\d.~\-]/g, '')
          const roiLow = parseFloat(roiStr.split('~')[0] || '0')
          const roiHigh = parseFloat((roiStr.split('~')[1] || roiStr.split('-')[1] || '0'))
          const roiValue = roiHigh > 0 ? (roiLow + roiHigh) / 2 : roiLow || 0
          products.push({
            name: (p.name || '未知').slice(0, 20),
            category: p.category || '',
            roiValue,
            potentialScore: p.potential_score || 0,
            competitionLevel: p.competition_level || '',
          })
        }
      }
    } catch { /* skip */ }
  }
  return { products }
})

const topProducts = computed(() => {
  return [...chartData.value.products]
    .sort((a, b) => b.roiValue - a.roiValue)
    .slice(0, 8)
})

const avgRoi = computed(() => {
  const prods = chartData.value.products
  if (prods.length === 0) return 0
  return prods.reduce((sum, p) => sum + p.roiValue, 0) / prods.length
})

const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)

const highPotentialCount = computed(() =>
  chartData.value.products.filter(p => p.potentialScore >= 8).length
)

const barData = computed(() => {
  const prods = chartData.value.products.slice(0, 10)
  const labels = prods.map(p => p.name.length > 8 ? p.name.slice(0, 8) + '…' : p.name)

  if (activeMode.value === 'roi') {
    return {
      labels,
      datasets: [{
        label: 'ROI (倍)',
        data: prods.map(p => p.roiValue),
        backgroundColor: prods.map(p =>
          p.roiValue >= 2.5 ? 'rgba(52, 197, 94, 0.7)' :
          p.roiValue >= 1.5 ? 'rgba(245, 158, 11, 0.7)' :
          'rgba(239, 68, 68, 0.7)'
        ),
        borderRadius: 6,
        borderSkipped: false,
      }]
    }
  }

  if (activeMode.value === 'score') {
    return {
      labels,
      datasets: [{
        label: '潜力分',
        data: prods.map(p => p.potentialScore),
        backgroundColor: 'rgba(129, 140, 248, 0.7)',
        borderRadius: 6,
        borderSkipped: false,
      }]
    }
  }

  return {
    labels,
    datasets: [{
      label: '竞争度',
      data: prods.map(p => {
        const m: Record<string, number> = { '低': 1, '中低': 2, '中': 3, '中高': 4, '高': 5 }
        return m[p.competitionLevel] || 3
      }),
      backgroundColor: prods.map(p => {
        const m: Record<string, string> = { '低': 'rgba(52, 197, 94, 0.7)', '中低': 'rgba(52, 197, 94, 0.5)', '中': 'rgba(245, 158, 11, 0.7)', '中高': 'rgba(245, 158, 11, 0.5)', '高': 'rgba(239, 68, 68, 0.7)' }
        return m[p.competitionLevel] || 'rgba(245, 158, 11, 0.7)'
      }),
      borderRadius: 6,
      borderSkipped: false,
    }]
  }
})

const barOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(17, 18, 37, 0.95)',
      titleColor: '#e2e8f0',
      bodyColor: '#94a3b8',
      borderColor: 'rgba(255,255,255,0.1)',
      borderWidth: 1,
      cornerRadius: 8,
      padding: 12,
    },
  },
  scales: {
    x: {
      ticks: { color: '#6b7280', font: { size: 11 } },
      grid: { color: 'rgba(255,255,255,0.04)' },
      border: { color: 'rgba(255,255,255,0.06)' },
    },
    y: {
      ticks: { color: '#6b7280', font: { size: 11 } },
      grid: { color: 'rgba(255,255,255,0.04)' },
      border: { color: 'rgba(255,255,255,0.06)' },
    },
  },
}))

async function loadTasks() {
  loading.value = true
  try {
    const res = await taskApi.list()
    tasks.value = res.data || []
  } catch {
    tasks.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>
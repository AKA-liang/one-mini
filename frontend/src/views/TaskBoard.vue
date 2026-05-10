<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-white">任务中心</h2>
        <p class="text-sm text-gray-400 mt-1">AI 智能体协作 · 选品分析 → 财务审核</p>
      </div>
      <button class="btn-primary flex items-center gap-2" @click="showCreateModal = true">
        <Plus :size="16" />
        新建任务
      </button>
    </div>

    <!-- Stats Bar -->
    <div class="grid grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <div class="text-2xl font-bold text-white">{{ tasks.length }}</div>
        <div class="text-xs text-gray-400 mt-1">总任务数</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-2xl font-bold text-primary-400">{{ runningCount }}</div>
        <div class="text-xs text-gray-400 mt-1">运行中</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-2xl font-bold text-emerald-400">{{ completedCount }}</div>
        <div class="text-xs text-gray-400 mt-1">已完成</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-2xl font-bold text-red-400">{{ failedCount }}</div>
        <div class="text-xs text-gray-400 mt-1">失败</div>
      </div>
    </div>

    <!-- Task List -->
    <div v-if="loading" class="glass-card p-12 flex flex-col items-center">
      <div class="w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-gray-400 mt-4">加载任务列表...</p>
    </div>

    <div v-else-if="tasks.length === 0" class="glass-card p-12 flex flex-col items-center">
      <ClipboardList :size="48" class="text-gray-600" />
      <p class="text-gray-400 mt-4">暂无任务</p>
      <p class="text-xs text-gray-500 mt-1">点击「新建任务」开始</p>
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="task in (showAllTasks ? tasks : tasks.slice(0, 3))"
        :key="task.taskId"
        class="glass-card-hover p-5 cursor-pointer"
        @click="selectTask(task)"
      >
        <!-- Task Header -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <span :class="statusBadgeClass(task.status)">
              {{ statusLabel(task.status) }}
            </span>
            <span class="text-sm font-medium text-gray-200">{{ typeLabel(task.type) }}</span>
          </div>
          <div class="flex items-center gap-2 text-xs text-gray-500">
            <Clock :size="12" />
            {{ formatTime(task.createTime) }}
          </div>
        </div>

        <!-- Task Time -->
        <div class="text-xs text-gray-500 mb-3">创建于 {{ formatTime(task.createTime) }}</div>

        <!-- Steps Flow -->
        <div v-if="task.steps && task.steps.length" class="flex items-center gap-2 flex-wrap">
          <template v-for="(step, idx) in task.steps" :key="step.id">
            <ChevronRight v-if="idx > 0" :size="12" class="text-gray-600" />
            <span class="text-xs text-gray-400">{{ step.agentName }}</span>
          </template>
        </div>
      </div>

      <!-- Expand/collapse toggle -->
      <div v-if="tasks.length > 3" class="text-center py-2">
        <button
          @click="showAllTasks = !showAllTasks"
          class="text-xs text-primary-400 hover:text-primary-300 transition-colors"
        >
          {{ showAllTasks ? '收起历史任务' : `查看全部 (${tasks.length - 3} 个历史任务)` }}
        </button>
      </div>
    </div>

    <!-- ROI Chart -->
    <RoiChart />

    <!-- Task Detail Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="selectedTask" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="selectedTask = null">
          <div class="w-full max-w-3xl max-h-[80vh] overflow-y-auto glass-card p-6">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h3 class="text-lg font-bold text-white">{{ typeLabel(selectedTask.type) }}</h3>
                <p class="text-xs text-gray-500 font-mono mt-1">{{ selectedTask.taskId }}</p>
              </div>
              <button @click="selectedTask = null" class="text-gray-400 hover:text-white transition-colors">
                <X :size="20" />
              </button>
            </div>

            <!-- Results -->
            <div v-if="selectedTask.outputJson" class="space-y-4">
              <ProductGrid v-if="hasProducts(selectedTask)" :products="parseProducts(selectedTask)" />
              <div v-else class="p-4 rounded-lg bg-surface-200/30 text-sm text-gray-300 whitespace-pre-wrap overflow-auto max-h-96">
                {{ selectedTask.outputJson }}
              </div>
            </div>
            <div v-else-if="selectedTask.status === 'running'" class="py-8 flex flex-col items-center">
              <div class="w-10 h-10 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></div>
              <p class="text-gray-400 mt-4">AI 智能体正在分析中...</p>
            </div>
            <div v-else class="py-8 text-center text-gray-500">
              等待处理
            </div>

            <!-- Steps -->
            <div v-if="selectedTask.steps && selectedTask.steps.length" class="mt-6 pt-4 border-t border-white/5">
              <h4 class="text-sm font-medium text-gray-300 mb-3">处理步骤</h4>
              <div class="space-y-2">
                <div v-for="step in selectedTask.steps" :key="step.id" class="flex items-center gap-3 p-2 rounded-lg bg-surface-200/30">
                  <span :class="stepStatusBadgeClass(step.status)">{{ stepStatusIcon(step.status) }}</span>
                  <span class="text-sm text-gray-300">{{ step.agentName }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Create Task Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="showCreateModal = false">
          <div class="w-full max-w-md glass-card p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-bold text-white">新建任务</h3>
              <button @click="showCreateModal = false" class="text-gray-400 hover:text-white transition-colors">
                <X :size="20" />
              </button>
            </div>

            <div class="space-y-4">
              <div>
                <label class="block text-sm text-gray-300 mb-1.5">任务类型</label>
                <select v-model="newTaskType" class="w-full px-3 py-2.5 bg-surface-200/50 border border-white/10 rounded-xl text-sm text-white focus:border-primary-400/50 focus:outline-none transition-colors">
                  <option value="product_analysis">选品分析</option>
                  <option value="comment_auto_reply">评论管理</option>
                  <option value="publish_article">发布文章</option>
                  <option value="publish_imagetext">发布图文</option>
                </select>
              </div>

              <div v-if="newTaskType === 'product_analysis'">
              <div>
                <label class="block text-sm text-gray-300 mb-1.5">关键词</label>
                <input
                  v-model="newTaskKeywords"
                  placeholder="输入关键词，用逗号分隔"
                  class="w-full px-3 py-2.5 bg-surface-200/50 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:border-primary-400/50 focus:outline-none transition-colors"
                />
              </div>

              <div>
                <label class="block text-sm text-gray-300 mb-1.5">平台</label>
                <select v-model="newTaskPlatform" class="w-full px-3 py-2.5 bg-surface-200/50 border border-white/10 rounded-xl text-sm text-white focus:border-primary-400/50 focus:outline-none transition-colors">
                  <option value="douyin">抖音</option>
                  <option value="xiaohongshu">小红书</option>
                  <option value="taobao">淘宝</option>
                </select>
              </div>

              <div>
                <label class="block text-sm text-gray-300 mb-1.5">推荐数量</label>
                <input
                  v-model.number="newTaskLimit"
                  type="number"
                  min="1"
                  max="50"
                  class="w-full px-3 py-2.5 bg-surface-200/50 border border-white/10 rounded-xl text-sm text-white focus:border-primary-400/50 focus:outline-none transition-colors"
                />
              </div>

              <div>
                <label class="block text-sm text-gray-300 mb-1.5">预算上限 <span class="text-gray-500">(选填)</span></label>
                <input
                  v-model="newTaskBudget"
                  placeholder="留空则不考虑预算"
                  class="w-full px-3 py-2.5 bg-surface-200/50 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:border-primary-400/50 focus:outline-none transition-colors"
                />
              </div>

              <div>
                <label class="block text-sm text-gray-300 mb-1.5">品类 <span class="text-gray-500">(选填)</span></label>
                <input
                  v-model="newTaskCategory"
                  placeholder="如：美妆护肤、3C数码"
                  class="w-full px-3 py-2.5 bg-surface-200/50 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:border-primary-400/50 focus:outline-none transition-colors"
                />
              </div>
              </div>  <!-- end v-if product_analysis -->

              <button class="btn-primary w-full mt-2" @click="createTask" :disabled="creating">
                {{ creating ? '创建中...' : (newTaskType === 'comment_auto_reply' ? '开始评论管理' : '开始分析') }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { taskApi, type TaskVO } from '../api/task'
import ProductGrid from '../components/ProductGrid.vue'
import RoiChart from '../components/RoiChart.vue'
import { Plus, ClipboardList, Clock, ChevronRight, X } from 'lucide-vue-next'

const tasks = ref<TaskVO[]>([])
const loading = ref(false)
const selectedTask = ref<TaskVO | null>(null)
const showCreateModal = ref(false)
const creating = ref(false)

const newTaskKeywords = ref('抖音热销,美妆护肤')
const newTaskType = ref('product_analysis')
const newTaskPlatform = ref('douyin')
const newTaskLimit = ref(10)
const newTaskBudget = ref('')
const newTaskCategory = ref('')
const showAllTasks = ref(false)

const runningCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)
const failedCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)

function statusLabel(status: string): string {
  const map: Record<string, string> = { pending: '等待中', running: '运行中', completed: '已完成', failed: '失败' }
  return map[status] || status
}

function typeLabel(type: string): string {
  const map: Record<string, string> = { product_analysis: '选品分析', finance_review: '财务审核', comment_auto_reply: '评论管理', publish_article: '发布文章', publish_imagetext: '发布图文' }
  return map[type] || type
}

function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    pending: 'badge-pending',
    running: 'badge-running',
    completed: 'badge-completed',
    failed: 'badge-failed',
  }
  return map[status] || 'badge-pending'
}

function stepStatusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    pending: 'text-gray-500',
    running: 'text-primary-400 animate-pulse',
    completed: 'text-emerald-400',
    failed: 'text-red-400',
  }
  return map[status] || 'text-gray-500'
}

function stepStatusIcon(status: string): string {
  const map: Record<string, string> = { pending: '○', running: '◉', completed: '●', failed: '✕' }
  return map[status] || '○'
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

function selectTask(task: TaskVO) {
  selectedTask.value = task
  if (task.status === 'running') {
    pollTask(task.taskId)
  }
}

async function pollTask(taskId: string) {
  const interval = setInterval(async () => {
    try {
      const res = await taskApi.getById(taskId)
      const updated = res.data
      const idx = tasks.value.findIndex(t => t.taskId === taskId)
      if (idx >= 0) tasks.value[idx] = updated
      if (selectedTask.value?.taskId === taskId) selectedTask.value = updated
      if (updated.status !== 'running') clearInterval(interval)
    } catch {
      clearInterval(interval)
    }
  }, 3000)
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await taskApi.list()
    tasks.value = (res.data || []).sort((a, b) =>
      new Date(b.createTime || 0).getTime() - new Date(a.createTime || 0).getTime()
    )
  } catch {
    tasks.value = []
  } finally {
    loading.value = false
  }
}

async function createTask() {
  creating.value = true
  try {
    const keywords = newTaskKeywords.value.split(',').map(k => k.trim()).filter(Boolean)
    const basePayload: Record<string, unknown> = { keywords, platform: newTaskPlatform.value, limit: newTaskLimit.value }
    if (newTaskBudget.value) basePayload.budget = newTaskBudget.value
    if (newTaskCategory.value) basePayload.category = newTaskCategory.value

    const res = await taskApi.create({
      type: newTaskType.value as 'product_analysis' | 'comment_auto_reply' | 'publish_article' | 'publish_imagetext',
      inputJson: newTaskType.value === 'comment_auto_reply'
        ? { action: 'auto_reply', reply_limit: newTaskLimit.value }
        : newTaskType.value === 'publish_article'
        ? { action: 'publish_article', title: keywords[0] || '', content: keywords.join(' '), dry_run: false }
        : newTaskType.value === 'publish_imagetext'
        ? { action: 'publish_imagetext', title: keywords[0] || '', description: keywords.join(' '), image_paths: [] }
        : basePayload,
    })
    tasks.value.unshift(res.data)
    showCreateModal.value = false
    pollTask(res.data.taskId)
  } catch (err) {
    console.error('创建任务失败:', err)
  } finally {
    creating.value = false
  }
}

function hasProducts(task: TaskVO): boolean {
  if (!task.outputJson) return false
  try { const d = JSON.parse(task.outputJson); return Array.isArray(d.products) && d.products.length > 0 } catch { return false }
}

function parseProducts(task: TaskVO): any[] {
  if (!task.outputJson) return []
  try { const d = JSON.parse(task.outputJson); return d.products || [] } catch { return [] }
}

onMounted(loadTasks)
</script>
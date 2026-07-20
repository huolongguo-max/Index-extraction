<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dataApi, type LogItem } from '@/utils/api'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import { RefreshCw, Trash2, AlertCircle, CheckCircle2, Clock } from 'lucide-vue-next'

/* ================================================================
   State
   ================================================================ */

const logs = ref<LogItem[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const error = ref<string | null>(null)

/* ================================================================
   Load
   ================================================================ */

async function loadLogs() {
  loading.value = true
  error.value = null
  try {
    const res = await dataApi.logs({ page: page.value, page_size: 30 })
    logs.value = res.data.items
    total.value = res.data.total
    totalPages.value = res.data.total_pages
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)

function prevPage() { if (page.value > 1) { page.value--; loadLogs() } }
function nextPage() { if (page.value < totalPages.value) { page.value++; loadLogs() } }

/* ================================================================
   Stats (computed from current logs only)
   ================================================================ */

const okCount = ref(0)
const failCount = ref(0)

import { computed } from 'vue'
import { onUnmounted } from 'vue'

// Recalc on logs change
import { watch } from 'vue'
watch(logs, (val) => {
  okCount.value = val.filter((l) => l.status === 'ok').length
  failCount.value = val.filter((l) => l.status === 'fail').length
})
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold">运行日志</h1>
        <p class="text-xs text-muted-foreground mt-0.5">
          共 {{ total }} 条记录 · {{ okCount }} 成功 · {{ failCount }} 异常
        </p>
      </div>
      <Button variant="ghost" size="sm" @click="loadLogs" :disabled="loading">
        <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
      </Button>
    </div>

    <!-- Error banner -->
    <div
      v-if="error"
      class="px-3 py-2 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive"
    >
      {{ error }}
    </div>

    <!-- Log list -->
    <div v-if="loading && logs.length === 0" class="text-center py-16 text-muted-foreground text-sm">加载中...</div>

    <div v-else-if="logs.length === 0" class="text-center py-16 text-muted-foreground text-sm">
      暂无运行记录，启动采集后将自动生成
    </div>

    <div v-else class="space-y-1.5">
      <Card
        v-for="log in logs"
        :key="`${log.rule_id}-${log.run_at}`"
        class="p-3 hover:border-primary/20 transition-colors"
      >
        <div class="flex items-start gap-3">
          <!-- Status icon -->
          <div class="mt-0.5 shrink-0">
            <CheckCircle2 v-if="log.status === 'ok'" class="w-4 h-4 text-emerald-400" />
            <AlertCircle v-else class="w-4 h-4 text-red-400" />
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0 space-y-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm font-medium">{{ log.rule_name }}</span>
              <Badge
                :variant="log.status === 'ok' ? 'success' : 'destructive'"
                class="text-[10px]"
              >
                {{ log.status === 'ok' ? '成功' : '失败' }}
              </Badge>
              <span v-if="log.row_count > 0" class="text-[11px] text-muted-foreground">
                {{ log.row_count }} 行
              </span>
            </div>
            <div class="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Clock class="w-3 h-3" />
              {{ log.run_at?.slice(0, 19).replace('T', ' ') || '—' }}
            </div>
            <div
              v-if="log.error"
              class="text-[11px] text-red-400/80 bg-red-500/5 px-2.5 py-1.5 rounded-md mt-1.5 font-mono break-all"
            >
              {{ log.error }}
            </div>
          </div>

          <!-- Row count badge -->
          <div class="shrink-0 text-right">
            <span
              v-if="log.row_count > 0"
              class="text-xs font-mono tabular-nums text-muted-foreground"
            >
              {{ log.row_count }} 行
            </span>
          </div>
        </div>
      </Card>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-2">
      <Button variant="outline" size="sm" :disabled="page <= 1" @click="prevPage">
        上一页
      </Button>
      <span class="text-xs text-muted-foreground">{{ page }} / {{ totalPages }}</span>
      <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="nextPage">
        下一页
      </Button>
    </div>
  </div>
</template>

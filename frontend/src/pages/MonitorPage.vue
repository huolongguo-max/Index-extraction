<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { dataApi, controlApi, type SchedulerStatus, type ScrapeRule, type LatestDataItem } from '@/utils/api'
import { rulesApi } from '@/utils/api'
import { useSSE } from '@/composables/useSSE'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import {
  Play, Square, Monitor, MonitorOff, RefreshCw, Wifi, WifiOff,
  TrendingUp, Clock, Hash, AlertCircle,
} from 'lucide-vue-next'

/* ================================================================
   Data sources
   ================================================================ */

// Scheduled polling fallback (every 10s) + SSE
const status = ref<SchedulerStatus | null>(null)
const rules = ref<ScrapeRule[]>([])
const latestMap = ref<Record<string, LatestDataItem>>({})
const loading = ref(false)
const triggerLoading = ref<Record<string, boolean>>({})
const debugLogs = ref<Record<string, string[]>>({})
const showDebug = ref<Record<string, boolean>>({})

// SSE
const {
  connected: sseConnected,
  updateData: sseData,
  schedulerStatus: sseStatus,
} = useSSE({
  onUpdate(payload) {
    const rid = payload.rule_id as string
    if (rid && latestMap.value[rid]) {
      latestMap.value[rid].row_count = (payload.row_count as number) || 0
      latestMap.value[rid].rows = (payload.data as Record<string, unknown>[]) || []
      latestMap.value[rid].cached_at = new Date().toISOString()
    }
  },
  onStatus(payload) {
    status.value = payload as unknown as SchedulerStatus
  },
})

/* ================================================================
   Load all
   ================================================================ */

async function loadAll() {
  loading.value = true
  try {
    const [statusRes, rulesRes, latestRes] = await Promise.all([
      dataApi.status(),
      rulesApi.list(),
      dataApi.latest(),
    ])
    status.value = statusRes.data
    rules.value = rulesRes.data.items

    // Build latestMap
    const items =
      'items' in latestRes.data
        ? (latestRes.data as { items: LatestDataItem[] }).items
        : [latestRes.data as LatestDataItem]
    const map: Record<string, LatestDataItem> = {}
    for (const item of items) {
      map[item.rule_id] = item
    }
    latestMap.value = map
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

// Fallback polling every 30s
const pollTimer = setInterval(loadAll, 30000)
import { onUnmounted } from 'vue'
onUnmounted(() => clearInterval(pollTimer))

/* ================================================================
   Actions
   ================================================================ */

async function triggerRule(ruleId: string, ruleName: string) {
  triggerLoading.value[ruleId] = true
  try {
    const res = await controlApi.trigger(ruleId)
    // 捕获调试日志 — 成功和失败都尝试提取
    const payload = res.data as any
    if (payload?.debug_log?.length) {
      debugLogs.value[ruleId] = payload.debug_log
    } else {
      debugLogs.value[ruleId] = [`[诊断] 未获取到调试日志。API 返回: code=${res.code}, msg=${res.msg}`]
    }
    showDebug.value[ruleId] = true
    setTimeout(loadAll, 2000)
  } catch (e: any) {
    debugLogs.value[ruleId] = [`[诊断] 请求失败: ${e.message || '未知错误'}`]
    showDebug.value[ruleId] = true
  } finally {
    triggerLoading.value[ruleId] = false
  }
}

async function handleScheduler(action: 'start' | 'stop') {
  try {
    if (action === 'start') await controlApi.schedulerStart()
    else await controlApi.schedulerStop()
    setTimeout(loadAll, 500)
  } catch {}
}

async function switchBrowser(mode: 'headless' | 'gui') {
  try {
    await controlApi.switchBrowserMode(mode)
  } catch {}
}

/* ================================================================
   Computed
   ================================================================ */

const enabledRules = computed(() => rules.value.filter((r) => r.enabled))

const totalRows = computed(() =>
  Object.values(latestMap.value).reduce((sum, d) => sum + (d.row_count || 0), 0),
)

const okCount = computed(() =>
  rules.value.filter((r) => r.last_status === 'ok').length,
)
const failCount = computed(() =>
  rules.value.filter((r) => r.last_status === 'fail').length,
)

function lastRunDisplay(rule: ScrapeRule): string {
  if (!rule.last_run_at) return '—'
  return rule.last_run_at.slice(0, 16).replace('T', ' ')
}

function latestData(rule: ScrapeRule): LatestDataItem | undefined {
  return latestMap.value[rule.rule_id]
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') return v.toLocaleString()
  return String(v)
}
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-xl font-bold">实时监控</h1>
        <p class="text-xs text-muted-foreground mt-0.5 flex items-center gap-2">
          <span
            class="inline-flex items-center gap-1"
            :class="sseConnected ? 'text-emerald-400' : 'text-muted-foreground'"
          >
            <Wifi v-if="sseConnected" class="w-3 h-3" />
            <WifiOff v-else class="w-3 h-3" />
            {{ sseConnected ? 'SSE 已连接' : 'SSE 未连接（轮询中）' }}
          </span>
          <span v-if="status?.active" class="text-emerald-400">· 调度运行中 ({{ status.uptime_seconds }}s)</span>
          <span v-else class="text-muted-foreground">· 调度已停止</span>
        </p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <Button variant="ghost" size="sm" @click="loadAll" :disabled="loading">
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
        </Button>
        <Button
          v-if="!status?.active"
          size="sm"
          variant="outline"
          @click="handleScheduler('start')"
        >
          <Play class="w-3.5 h-3.5" /> 启动调度
        </Button>
        <Button
          v-else
          size="sm"
          variant="outline"
          @click="handleScheduler('stop')"
        >
          <Square class="w-3.5 h-3.5" /> 停止调度
        </Button>
        <Button size="sm" variant="ghost" @click="switchBrowser('gui')">
          <Monitor class="w-3.5 h-3.5" /> GUI
        </Button>
        <Button size="sm" variant="ghost" @click="switchBrowser('headless')">
          <MonitorOff class="w-3.5 h-3.5" /> 静默
        </Button>
      </div>
    </div>

    <!-- KPI row -->
    <div class="grid grid-cols-4 gap-3">
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">启用规则</p>
        <p class="text-2xl font-bold">{{ enabledRules.length }}</p>
      </Card>
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">成功采集</p>
        <p class="text-2xl font-bold text-emerald-400">{{ okCount }}</p>
      </Card>
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">采集失败</p>
        <p class="text-2xl font-bold" :class="failCount ? 'text-red-400' : ''">{{ failCount }}</p>
      </Card>
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">总数据行</p>
        <p class="text-2xl font-bold text-primary">{{ totalRows }}</p>
      </Card>
    </div>

    <!-- Rule + data grid -->
    <div v-if="loading && rules.length === 0" class="text-center py-16 text-muted-foreground text-sm">加载中...</div>

    <div v-else-if="rules.length === 0" class="text-center py-16 text-muted-foreground text-sm">
      暂无规则，请先在「规则管理」中创建
    </div>

    <div v-else class="space-y-3">
      <Card
        v-for="rule in rules"
        :key="rule.rule_id"
        class="p-4"
      >
        <!-- Rule header -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2 min-w-0">
            <span
              class="w-2 h-2 rounded-full shrink-0"
              :class="rule.last_status === 'ok' ? 'bg-emerald-400' : rule.last_status === 'fail' ? 'bg-red-400' : 'bg-muted-foreground/40'"
            />
            <span class="text-sm font-semibold truncate">{{ rule.rule_name }}</span>
            <Badge
              :variant="rule.last_status === 'ok' ? 'success' : rule.last_status === 'fail' ? 'destructive' : 'secondary'"
              class="text-[10px]"
            >
              {{ rule.last_status === 'ok' ? '正常' : rule.last_status === 'fail' ? '异常' : '待运行' }}
            </Badge>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-[10px] text-muted-foreground">
              {{ lastRunDisplay(rule) }}
            </span>
            <Button
              size="sm"
              variant="outline"
              class="h-7 text-xs"
              :disabled="triggerLoading[rule.rule_id]"
              @click="triggerRule(rule.rule_id, rule.rule_name)"
            >
              <RefreshCw
                class="w-3 h-3"
                :class="{ 'animate-spin': triggerLoading[rule.rule_id] }"
              />
              立即抓取
            </Button>
          </div>
        </div>

        <!-- Latest data -->
        <div v-if="latestData(rule)?.rows?.length">
          <div class="overflow-x-auto rounded-lg border border-border/50">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-border/50 bg-secondary/30">
                  <th
                    v-for="h in (latestData(rule)?.headers || rule.target_headers)"
                    :key="h"
                    class="px-3 py-2 text-left font-medium text-muted-foreground"
                  >
                    {{ h }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, ri) in (latestData(rule)?.rows || [])"
                  :key="ri"
                  class="border-b border-border/30 last:border-0"
                >
                  <td
                    v-for="h in (latestData(rule)?.headers || rule.target_headers)"
                    :key="h"
                    class="px-3 py-2 text-foreground tabular-nums"
                  >
                    {{ formatValue(row[h]) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="text-xs text-muted-foreground py-2">
          暂无采集数据
        </div>

        <!-- Error -->
        <div
          v-if="rule.last_error"
          class="mt-2 px-3 py-1.5 bg-destructive/10 rounded text-[11px] text-destructive/80 truncate"
        >
          {{ rule.last_error }}
        </div>

        <!-- Debug log -->
        <div v-if="debugLogs[rule.rule_id]?.length" class="mt-2 border-t border-border pt-2">
          <button
            class="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
            @click="showDebug[rule.rule_id] = !showDebug[rule.rule_id]"
          >
            <span>{{ showDebug[rule.rule_id] ? '▼' : '▶' }}</span>
            采集诊断 ({{ debugLogs[rule.rule_id].length }} 条)
          </button>
          <div v-if="showDebug[rule.rule_id]" class="mt-1.5 space-y-0.5 max-h-48 overflow-auto">
            <div
              v-for="(line, i) in debugLogs[rule.rule_id]"
              :key="i"
              class="text-[10px] font-mono px-2 py-0.5 rounded"
              :class="line.includes('✅') ? 'text-emerald-400 bg-emerald-500/5' : line.includes('❌') ? 'text-red-400 bg-red-500/5' : 'text-muted-foreground'"
            >
              {{ line }}
            </div>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

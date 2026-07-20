<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { windowApi, type WindowStatus } from '@/utils/api'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import { Monitor, Play, Square, RefreshCw, Clock, Hash } from 'lucide-vue-next'

/* ================================================================
   State
   ================================================================ */

const status = ref<WindowStatus>({ running: false, pid: null, uptime_seconds: 0 })
const loading = ref(false)
const actionLoading = ref<string | null>(null)

/* ================================================================
   Lifecycle — poll every 5s
   ================================================================ */

let timer: ReturnType<typeof setInterval> | null = null

async function loadStatus() {
  try {
    const res = await windowApi.status()
    status.value = res.data
  } catch { /* silent */ }
}

onMounted(() => {
  loadStatus()
  timer = setInterval(loadStatus, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

/* ================================================================
   Actions
   ================================================================ */

async function handleStart() {
  actionLoading.value = 'start'
  try {
    const res = await windowApi.start()
    status.value = res.data
  } catch { /* handled */ }
  finally { actionLoading.value = null }
}

async function handleStop() {
  actionLoading.value = 'stop'
  try {
    const res = await windowApi.stop()
    status.value = res.data
  } catch { /* handled */ }
  finally { actionLoading.value = null }
}

async function handleRestart() {
  actionLoading.value = 'restart'
  try {
    const res = await windowApi.restart()
    status.value = res.data
  } catch { /* handled */ }
  finally { actionLoading.value = null }
}

/* ================================================================
   Format
   ================================================================ */

function formatUptime(s: number): string {
  if (s <= 0) return '—'
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  if (m > 0) return `${m}m ${Math.floor(s % 60)}s`
  return `${Math.floor(s)}s`
}
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold">悬浮窗控制</h1>
        <p class="text-xs text-muted-foreground mt-0.5 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" :class="status.running ? 'bg-emerald-400' : 'bg-muted-foreground/40'" />
          {{ status.running ? '运行中' : '未启动' }}
          <template v-if="status.running && status.pid">
            · PID {{ status.pid }}
          </template>
        </p>
      </div>
      <Button variant="ghost" size="sm" @click="loadStatus" :disabled="loading">
        <RefreshCw class="w-3.5 h-3.5" />
      </Button>
    </div>

    <!-- KPI cards -->
    <div class="grid grid-cols-3 gap-3">
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">状态</p>
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full" :class="status.running ? 'bg-emerald-400' : 'bg-muted-foreground/40'" />
          <span class="text-lg font-bold">{{ status.running ? '运行中' : '已停止' }}</span>
        </div>
      </Card>
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">运行时长</p>
        <p class="text-lg font-bold tabular-nums">{{ formatUptime(status.uptime_seconds) }}</p>
      </Card>
      <Card class="p-4 space-y-1">
        <p class="text-[10px] text-muted-foreground uppercase tracking-wider">进程 PID</p>
        <p class="text-lg font-bold tabular-nums font-mono">{{ status.pid || '—' }}</p>
      </Card>
    </div>

    <!-- Controls -->
    <Card class="p-5 space-y-4">
      <h3 class="text-sm font-semibold">操作</h3>
      <div class="flex flex-wrap gap-3">
        <Button
          size="lg"
          @click="handleStart"
          :disabled="status.running || actionLoading === 'start'"
        >
          <Play class="w-4 h-4" />
          {{ actionLoading === 'start' ? '启动中...' : '启动悬浮窗' }}
        </Button>
        <Button
          variant="destructive"
          size="lg"
          @click="handleStop"
          :disabled="!status.running || actionLoading === 'stop'"
        >
          <Square class="w-4 h-4" />
          {{ actionLoading === 'stop' ? '停止中...' : '停止悬浮窗' }}
        </Button>
        <Button
          variant="outline"
          size="lg"
          @click="handleRestart"
          :disabled="!status.running || actionLoading === 'restart'"
        >
          <RefreshCw class="w-4 h-4" />
          {{ actionLoading === 'restart' ? '重启中...' : '重启悬浮窗' }}
        </Button>
      </div>
    </Card>

    <!-- Info -->
    <Card class="p-5 space-y-3">
      <h3 class="text-sm font-semibold">使用说明</h3>
      <ul class="text-xs text-muted-foreground space-y-1.5 list-disc list-inside">
        <li>悬浮窗是独立桌面程序，通过 SSE 实时接收后端采集数据</li>
        <li>点击「启动悬浮窗」后会在桌面显示置顶数据窗口</li>
        <li>关闭悬浮窗窗口不会停止程序，会自动隐藏到系统托盘</li>
        <li>如 PyQt6 未安装，按钮将无响应（需 pip install PyQt6）</li>
        <li>悬浮窗与 Web 管理后台共享同一后端，数据完全同步</li>
      </ul>
    </Card>
  </div>
</template>

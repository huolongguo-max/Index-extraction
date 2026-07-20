<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Settings2, Activity, ScrollText, Monitor, PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const navItems = [
  { to: '/rules', label: '规则管理', icon: Settings2 },
  { to: '/monitor', label: '实时监控', icon: Activity },
  { to: '/window', label: '悬浮窗', icon: Monitor },
  { to: '/logs', label: '运行日志', icon: ScrollText },
]

const activeRoute = computed(() => route.path)
</script>

<template>
  <div class="flex h-screen bg-background overflow-hidden">
    <!-- Sidebar -->
    <aside
      :class="[
        'flex flex-col border-r border-border bg-card/60 backdrop-blur-xl transition-all duration-300 ease-out',
        collapsed ? 'w-[52px]' : 'w-[200px]',
      ]"
    >
      <!-- Logo -->
      <div class="flex items-center gap-2 h-12 px-3 border-b border-border/50">
        <div class="w-6 h-6 rounded-md bg-primary flex items-center justify-center shrink-0">
          <span class="text-[10px] font-bold text-primary-foreground">IX</span>
        </div>
        <span
          v-if="!collapsed"
          class="text-xs font-semibold text-foreground truncate"
        >
          Index-extraction
        </span>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-2 px-1.5 space-y-0.5">
        <button
          v-for="item in navItems"
          :key="item.to"
          :class="[
            'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all duration-150',
            activeRoute === item.to
              ? 'bg-primary/15 text-primary'
              : 'text-muted-foreground hover:bg-accent hover:text-foreground',
          ]"
          @click="router.push(item.to)"
        >
          <component :is="item.icon" class="w-4 h-4 shrink-0" />
          <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
        </button>
      </nav>

      <!-- Collapse toggle -->
      <div class="p-1.5 border-t border-border/50">
        <button
          class="w-full flex items-center justify-center py-2 rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          @click="collapsed = !collapsed"
        >
          <PanelLeftClose v-if="!collapsed" class="w-4 h-4" />
          <PanelLeftOpen v-else class="w-4 h-4" />
        </button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto">
      <div class="max-w-6xl mx-auto p-6">
        <slot />
      </div>
    </main>
  </div>
</template>

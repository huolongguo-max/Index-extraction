<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'
  class?: string
}>()

const variants: Record<string, string> = {
  default: 'bg-primary/15 text-primary border-transparent',
  secondary: 'bg-secondary text-secondary-foreground border-transparent',
  destructive: 'bg-destructive/15 text-destructive border-transparent',
  outline: 'text-foreground border-border',
  success: 'bg-emerald-500/15 text-emerald-400 border-transparent',
  warning: 'bg-amber-500/15 text-amber-400 border-transparent',
}
</script>

<template>
  <span
    :class="
      cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
        variants[variant || 'default'],
        $attrs.class as string,
      )
    "
  >
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  class?: HTMLAttributes['class']
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'default',
  disabled: false,
})

const variants: Record<string, string> = {
  default: 'bg-primary text-primary-foreground hover:opacity-90 shadow-sm',
  destructive: 'bg-destructive text-destructive-foreground hover:opacity-90',
  outline: 'border border-input bg-transparent hover:bg-accent hover:text-accent-foreground',
  secondary: 'bg-secondary text-secondary-foreground hover:opacity-80',
  ghost: 'hover:bg-accent hover:text-accent-foreground',
  link: 'text-primary underline-offset-4 hover:underline',
}

const sizes: Record<string, string> = {
  default: 'h-9 px-4 py-2 text-sm',
  sm: 'h-8 px-3 text-xs rounded-md',
  lg: 'h-10 px-6 text-base rounded-md',
  icon: 'h-9 w-9',
}
</script>

<template>
  <button
    :class="
      cn(
        'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium',
        'transition-all duration-150 ease-out',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background',
        'disabled:pointer-events-none disabled:opacity-40',
        'active:scale-[0.97]',
        variants[variant],
        sizes[size],
        props.class,
      )
    "
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

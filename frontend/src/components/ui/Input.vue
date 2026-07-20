<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  modelValue?: string | number | null
  class?: HTMLAttributes['class']
  placeholder?: string
  type?: string
  disabled?: boolean
  autocomplete?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string | number | null] }>()

const model = computed({
  get: () => props.modelValue ?? '',
  set: (v) => emit('update:modelValue', v),
})
</script>

<template>
  <input
    v-model="model"
    :type="type || 'text'"
    :placeholder="placeholder"
    :disabled="disabled"
    :autocomplete="autocomplete"
    :class="
      cn(
        'flex h-9 w-full rounded-lg border border-input bg-transparent px-3 py-1 text-sm text-foreground',
        'placeholder:text-muted-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background',
        'disabled:cursor-not-allowed disabled:opacity-40',
        'transition-shadow duration-150',
        props.class,
      )
    "
  />
</template>

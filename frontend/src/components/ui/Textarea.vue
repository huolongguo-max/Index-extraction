<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{ modelValue?: string; class?: string; placeholder?: string; rows?: number; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: string] }>()
const m = computed({ get: () => props.modelValue ?? '', set: (v) => emit('update:modelValue', v) })
</script>
<template>
  <textarea v-model="m" :placeholder="placeholder" :rows="rows || 3" :disabled="disabled"
    :class="cn('flex min-h-[60px] w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-40', props.class)" />
</template>

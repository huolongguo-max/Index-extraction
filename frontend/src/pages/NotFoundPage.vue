<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-center text-center px-6">
    <h1 class="text-6xl font-bold text-muted-foreground/30 mb-4">404</h1>
    <p class="text-lg text-foreground mb-2">页面未找到</p>
    <p class="text-sm text-muted-foreground mb-8">您访问的页面不存在或已被移除</p>
    <button
      class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm"
      @click="router.push('/')"
    >
      返回首页
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { rulesApi, type ScrapeRule, type RuleCreatePayload } from '@/utils/api'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import { Plus, Pencil, Trash2, Search, Power, PowerOff, RefreshCw, X } from 'lucide-vue-next'

/* ================================================================
   State
   ================================================================ */

const rules = ref<ScrapeRule[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// -- Form
const showForm = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)

const form = ref<RuleCreatePayload>({
  rule_name: '',
  target_url: '',
  row_keyword: '',
  target_headers: [],
  refresh_mode: 'interval',
  interval_seconds: 60,
  enabled: true,
  auto_click_button: false,
  button_text: null,
  table_type: 'div',
  row_xpath: "//div[contains(@class, 'table-row')]",
  header_row_xpath: "//div[contains(@class, 'table-header')]",
  cell_tag: 'div',
  cell_class: null,
  max_pages: 1,
})

const headersInput = ref('')
const showAdvanced = ref(false)

// 切换表格类型时自动更新 XPath 默认值
import { watch } from 'vue'
watch(() => form.value.table_type, (val) => {
  if (val === 'table') {
    form.value.row_xpath = form.value.row_xpath.includes('table-row') ? "//table/tbody/tr" : form.value.row_xpath
    form.value.header_row_xpath = form.value.header_row_xpath.includes('table-header') ? "//table/thead/tr" : form.value.header_row_xpath
    form.value.cell_tag = form.value.cell_tag === 'div' ? 'td' : form.value.cell_tag
  } else {
    form.value.row_xpath = form.value.row_xpath === '//table/tbody/tr' ? "//div[contains(@class, 'table-row')]" : form.value.row_xpath
    form.value.header_row_xpath = form.value.header_row_xpath === '//table/thead/tr' ? "//div[contains(@class, 'table-header')]" : form.value.header_row_xpath
    form.value.cell_tag = form.value.cell_tag === 'td' ? 'div' : form.value.cell_tag
  }
})

// -- Delete confirm
const deletingId = ref<string | null>(null)

/* ================================================================
   Computed
   ================================================================ */

const editingRule = computed(() =>
  editingId.value ? rules.value.find((r) => r.rule_id === editingId.value) : null,
)

const formTitle = computed(() => (editingId.value ? '编辑规则' : '新增规则'))

const isValid = computed(() =>
  form.value.rule_name.trim() &&
  form.value.target_url.startsWith('http') &&
  form.value.row_keyword.trim() &&
  form.value.target_headers.length > 0,
)

/* ================================================================
   Load
   ================================================================ */

async function loadRules() {
  loading.value = true
  error.value = null
  try {
    const res = await rulesApi.list()
    rules.value = res.data.items
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(loadRules)

/* ================================================================
   Form actions
   ================================================================ */

function openCreate() {
  editingId.value = null
  form.value = {
    rule_name: '',
    target_url: '',
    row_keyword: '',
    target_headers: [],
    refresh_mode: 'interval',
    interval_seconds: 60,
    enabled: true,
    auto_click_button: false,
    button_text: null,
    table_type: 'div',
    row_xpath: "//div[contains(@class, 'table-row')]",
    header_row_xpath: "//div[contains(@class, 'table-header')]",
    cell_tag: 'div',
    cell_class: null,
    max_pages: 1,
  }
  headersInput.value = ''
  showForm.value = true
}

function openEdit(rule: ScrapeRule) {
  editingId.value = rule.rule_id
  form.value = {
    rule_name: rule.rule_name,
    target_url: rule.target_url,
    row_keyword: rule.row_keyword,
    target_headers: [...rule.target_headers],
    refresh_mode: rule.refresh_mode || 'interval',
    interval_seconds: rule.interval_seconds,
    enabled: rule.enabled,
    auto_click_button: rule.auto_click_button,
    button_text: rule.button_text,
    table_type: rule.table_type || 'div',
    row_xpath: rule.row_xpath || "//div[contains(@class, 'table-row')]",
    header_row_xpath: rule.header_row_xpath || "//div[contains(@class, 'table-header')]",
    cell_tag: rule.cell_tag || 'div',
    cell_class: rule.cell_class || null,
    max_pages: rule.max_pages || 1,
  }
  headersInput.value = rule.target_headers.join(', ')
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingId.value = null
}

function syncHeaders() {
  form.value.target_headers = headersInput.value
    .split(/[,，、\s]+/)
    .map((h) => h.trim())
    .filter(Boolean)
}

async function save() {
  syncHeaders()
  if (!isValid.value) return
  saving.value = true
  error.value = null
  try {
    if (editingId.value) {
      await rulesApi.update(editingId.value, form.value)
    } else {
      await rulesApi.create(form.value)
    }
    closeForm()
    await loadRules()
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

/* ================================================================
   Actions
   ================================================================ */

async function toggleRule(rule: ScrapeRule) {
  try {
    await rulesApi.toggle(rule.rule_id)
    await loadRules()
  } catch (e: any) {
    error.value = e.message
  }
}

async function deleteRule(ruleId: string) {
  try {
    await rulesApi.remove(ruleId)
    deletingId.value = null
    await loadRules()
  } catch (e: any) {
    error.value = e.message
    deletingId.value = null
  }
}

function removeHeader(index: number) {
  form.value.target_headers.splice(index, 1)
  headersInput.value = form.value.target_headers.join(', ')
}
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold">规则管理</h1>
        <p class="text-xs text-muted-foreground mt-0.5">
          共 {{ rules.length }} 条规则 · {{ rules.filter((r) => r.enabled).length }} 条启用
        </p>
      </div>
      <div class="flex gap-2">
        <Button variant="ghost" size="sm" @click="loadRules" :disabled="loading">
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
        </Button>
        <Button size="sm" @click="openCreate">
          <Plus class="w-4 h-4" />
          新增规则
        </Button>
      </div>
    </div>

    <!-- Error banner -->
    <div
      v-if="error"
      class="flex items-center gap-2 px-3 py-2 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive"
    >
      <X class="w-3.5 h-3.5 shrink-0" />
      {{ error }}
      <button class="ml-auto text-xs underline" @click="error = null">关闭</button>
    </div>

    <!-- Rule list -->
    <div v-if="loading" class="text-center py-16 text-muted-foreground text-sm">加载中...</div>

    <div v-else-if="rules.length === 0" class="text-center py-16 space-y-3">
      <p class="text-muted-foreground text-sm">暂无抓取规则</p>
      <Button variant="outline" size="sm" @click="openCreate">创建第一条规则</Button>
    </div>

    <div v-else class="space-y-2">
      <Card
        v-for="rule in rules"
        :key="rule.rule_id"
        class="p-4 hover:border-primary/30 transition-colors duration-200"
      >
        <div class="flex items-start gap-4">
          <!-- Status dot + info -->
          <div class="flex-1 min-w-0 space-y-1.5">
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full shrink-0"
                :class="rule.enabled ? 'bg-emerald-400' : 'bg-muted-foreground/40'"
              />
              <span class="text-sm font-semibold truncate">{{ rule.rule_name }}</span>
              <Badge v-if="rule.enabled" variant="success" class="text-[10px]">启用</Badge>
              <Badge v-else variant="secondary" class="text-[10px]">停用</Badge>
            </div>
            <p class="text-xs text-muted-foreground truncate">{{ rule.target_url }}</p>
            <div class="flex flex-wrap gap-1.5">
              <Badge
                v-for="h in rule.target_headers"
                :key="h"
                variant="outline"
                class="text-[10px]"
              >
                {{ h }}
              </Badge>
              <span class="text-[10px] text-muted-foreground self-center ml-1">
                <template v-if="rule.refresh_mode === 'manual'">手动刷新</template>
                <template v-else>每 {{ rule.interval_seconds }}s</template>
                <span v-if="rule.auto_click_button"> · 自动点「{{ rule.button_text }}」</span>
              </span>
            </div>
            <p v-if="rule.last_run_at" class="text-[10px] text-muted-foreground">
              最后运行: {{ rule.last_run_at?.slice(0, 16).replace('T', ' ') }}
              <span :class="rule.last_status === 'ok' ? 'text-emerald-400' : 'text-red-400'">
                · {{ rule.last_status === 'ok' ? `成功 (${rule.last_row_count}行)` : '失败' }}
              </span>
            </p>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              :title="rule.enabled ? '停用' : '启用'"
              @click="toggleRule(rule)"
            >
              <Power v-if="rule.enabled" class="w-3.5 h-3.5 text-emerald-400" />
              <PowerOff v-else class="w-3.5 h-3.5" />
            </button>
            <button
              class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title="编辑"
              @click="openEdit(rule)"
            >
              <Pencil class="w-3.5 h-3.5" />
            </button>
            <button
              class="p-1.5 rounded-md text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="删除"
              @click="deletingId = rule.rule_id"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Inline delete confirm -->
        <div
          v-if="deletingId === rule.rule_id"
          class="mt-3 flex items-center gap-2 px-3 py-2 bg-destructive/10 rounded-lg"
        >
          <span class="text-xs text-destructive">确定删除「{{ rule.rule_name }}」？此操作不可撤销。</span>
          <Button size="sm" variant="destructive" class="h-7 text-xs" @click="deleteRule(rule.rule_id)">
            确认删除
          </Button>
          <Button size="sm" variant="ghost" class="h-7 text-xs" @click="deletingId = null">
            取消
          </Button>
        </div>
      </Card>
    </div>

    <!-- ================================================================ -->
    <!-- Form Modal -->
    <!-- ================================================================ -->
    <Teleport to="body">
      <div
        v-if="showForm"
        class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/60 backdrop-blur-sm"
          @click="closeForm"
        />

        <!-- Card -->
        <Card class="relative w-full max-w-lg mx-4 max-h-[80vh] overflow-auto shadow-2xl border-border/60">
          <!-- Header -->
          <div class="sticky top-0 z-10 flex items-center justify-between px-5 py-3.5 border-b border-border bg-card/95 backdrop-blur-xl">
            <h2 class="text-sm font-semibold">{{ formTitle }}</h2>
            <button
              class="p-1 rounded-md text-muted-foreground hover:text-foreground transition-colors"
              @click="closeForm"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Body -->
          <div class="px-5 py-4 space-y-4">
            <!-- Name -->
            <div class="space-y-1.5">
              <Label>规则名称</Label>
              <Input v-model="form.rule_name" placeholder="如：营收数据抓取" />
            </div>

            <!-- URL -->
            <div class="space-y-1.5">
              <Label>目标网页地址</Label>
              <Input v-model="form.target_url" placeholder="https://..." type="url" />
            </div>

            <!-- Row keyword -->
            <div class="space-y-1.5">
              <Label>行关键词</Label>
              <Input v-model="form.row_keyword" placeholder="如：公司名称 / 产品名" />
              <p class="text-[10px] text-muted-foreground">在表格行中能唯一识别目标行的文字</p>
            </div>

            <!-- Target headers -->
            <div class="space-y-1.5">
              <Label>待采集表头列表</Label>
              <Textarea
                v-model="headersInput"
                placeholder="金额, 日期, 状态（逗号或空格分隔）"
                :rows="2"
                @blur="syncHeaders"
              />
              <div v-if="form.target_headers.length" class="flex flex-wrap gap-1 mt-1">
                <Badge
                  v-for="(h, i) in form.target_headers"
                  :key="i"
                  variant="secondary"
                  class="text-[10px] gap-1"
                >
                  {{ h }}
                  <button class="hover:text-destructive" @click="removeHeader(i)">×</button>
                </Badge>
              </div>
            </div>

            <!-- Refresh mode -->
            <div class="space-y-1.5">
              <Label>刷新模式</Label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input v-model="form.refresh_mode" type="radio" value="interval" class="accent-primary" />
                  <span class="text-sm">定时刷新</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input v-model="form.refresh_mode" type="radio" value="manual" class="accent-primary" />
                  <span class="text-sm">手动刷新</span>
                </label>
              </div>
              <p class="text-[10px] text-muted-foreground">
                手动模式下不会自动采集，仅可通过实时监控页「立即抓取」触发
              </p>
            </div>

            <!-- Interval -->
            <div v-if="form.refresh_mode === 'interval'" class="space-y-1.5">
              <Label>刷新间隔（秒）</Label>
              <Input v-model.number="form.interval_seconds" type="number" placeholder="60" />
            </div>

            <!-- Auto click -->
            <div class="space-y-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="form.auto_click_button"
                  type="checkbox"
                  class="w-4 h-4 rounded border-input bg-transparent accent-primary"
                />
                <span class="text-sm">加载页面后自动点击按钮</span>
              </label>
              <Input
                v-if="form.auto_click_button"
                v-model="form.button_text"
                placeholder="按钮文字（如：导出数据）"
              />
            </div>

            <!-- Advanced -->
            <div class="border-t border-border pt-4">
              <button type="button" class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors" @click="showAdvanced = !showAdvanced">
                <span class="text-[9px]">{{ showAdvanced ? '▼' : '▶' }}</span> 高级选项（XPath / 翻页）
              </button>
              <div v-if="showAdvanced" class="space-y-3 mt-3">
                <div class="space-y-1.5">
                  <Label class="text-xs">表格类型</Label>
                  <div class="flex gap-4">
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input v-model="form.table_type" type="radio" value="div" class="accent-primary" />
                      <span class="text-sm">DIV 表格</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input v-model="form.table_type" type="radio" value="table" class="accent-primary" />
                      <span class="text-sm">HTML &lt;table&gt;</span>
                    </label>
                  </div>
                  <p class="text-[10px] text-muted-foreground">
                    <template v-if="form.table_type === 'table'">通用匹配 &lt;table&gt; 结构；多表格页面可自行在下方 XPath 中添加 class 筛选，例如 //table[@class="data-table"]/tbody/tr</template>
                    <template v-else>使用下方自定义 XPath 定位 DIV 表格行列</template>
                  </p>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1.5">
                    <Label class="text-xs">行容器 XPath</Label>
                    <Input v-model="form.row_xpath" placeholder="//div[contains(@class,'table-row')]" />
                  </div>
                  <div class="space-y-1.5">
                    <Label class="text-xs">表头行 XPath</Label>
                    <Input v-model="form.header_row_xpath" placeholder="//div[contains(@class,'table-header')]" />
                  </div>
                  <div class="space-y-1.5">
                    <Label class="text-xs">单元格标签</Label>
                    <Input v-model="form.cell_tag" placeholder="div" />
                  </div>
                  <div class="space-y-1.5">
                    <Label class="text-xs">单元格 CSS class</Label>
                    <Input v-model="form.cell_class" placeholder="可选，留空则不限制" />
                  </div>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs">最大翻页数</Label>
                  <Input v-model.number="form.max_pages" type="number" placeholder="1" />
                  <p class="text-[10px] text-muted-foreground">1 = 仅抓取首页</p>
                </div>
              </div>
            </div>

            <!-- Enable -->
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="form.enabled"
                type="checkbox"
                class="w-4 h-4 rounded border-input bg-transparent accent-primary"
              />
              <span class="text-sm">创建后立即启用</span>
            </label>
          </div>

          <!-- Footer -->
          <div class="sticky bottom-0 flex justify-end gap-2 px-5 py-3 border-t border-border bg-card/95 backdrop-blur-xl">
            <Button variant="ghost" size="sm" @click="closeForm">取消</Button>
            <Button size="sm" :disabled="!isValid" @click="save">
              {{ saving ? '保存中...' : (editingId ? '保存修改' : '创建规则') }}
            </Button>
          </div>
        </Card>
      </div>
    </Teleport>
  </div>
</template>

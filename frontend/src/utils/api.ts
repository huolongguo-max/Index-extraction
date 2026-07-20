/**
 * API 服务层 — 对接后端全部 17 个接口
 * 所有入参出参强类型，统一返回 { code, msg, data }
 */
import axios, { type AxiosInstance } from 'axios'

/* ================================================================
   Types
   ================================================================ */

export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data: T
}

export interface ScrapeRule {
  rule_id: string
  rule_name: string
  target_url: string
  row_keyword: string
  target_headers: string[]
  table_type: string
  refresh_mode: string
  interval_seconds: number
  enabled: boolean
  auto_click_button: boolean
  button_text?: string | null
  row_xpath: string
  header_row_xpath: string
  cell_tag: string
  cell_class?: string | null
  max_pages: number
  last_run_at?: string | null
  last_status?: string | null
  last_row_count: number
  last_error?: string | null
  created_at: string
}

export interface RuleCreatePayload {
  rule_name: string
  target_url: string
  row_keyword: string
  target_headers: string[]
  table_type?: string
  refresh_mode?: string
  interval_seconds?: number
  enabled?: boolean
  auto_click_button?: boolean
  button_text?: string | null
  row_xpath?: string
  header_row_xpath?: string
  cell_tag?: string
  cell_class?: string | null
  max_pages?: number
}

export interface RuleUpdatePayload {
  rule_name?: string
  target_url?: string
  row_keyword?: string
  target_headers?: string[]
  table_type?: string
  refresh_mode?: string
  interval_seconds?: number
  enabled?: boolean
  auto_click_button?: boolean
  button_text?: string | null
  row_xpath?: string
  header_row_xpath?: string
  cell_tag?: string
  cell_class?: string | null
  max_pages?: number
}

export interface LatestDataItem {
  rule_id: string
  rule_name: string
  row_count: number
  cached_at?: string
  headers?: string[]
  rows?: Record<string, unknown>[]
}

export interface HistoryItem {
  rule_id: string
  rule_name: string
  target_url: string
  last_run_at: string | null
  last_status: string | null
  last_row_count: number
  last_error: string | null
  cached_at: string | null
}

export interface LogItem {
  rule_id: string
  rule_name: string
  run_at: string | null
  status: string | null
  row_count: number
  error: string | null
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SchedulerStatus {
  active: boolean
  active_rules: number
  running_tasks: number
  total_runs: number
  total_ok: number
  total_fail: number
  rules_detail: Array<{
    rule_id: string
    rule_name: string
    enabled: boolean
    interval: number
    last_run: string | null
    last_status: string | null
    last_rows: number
  }>
  uptime_seconds: number
  reason?: string
}

/* ================================================================
   Axios Instance
   ================================================================ */

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:18000'
const http: AxiosInstance = axios.create({ baseURL: BASE, timeout: 30000 })

http.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '网络请求失败'
    console.error(`[API] ${err.config?.method?.toUpperCase()} ${err.config?.url} → ${msg}`)
    return Promise.reject(new Error(msg))
  },
)

/* ================================================================
   Rules API
   ================================================================ */

export const rulesApi = {
  list: (enabled?: boolean) =>
    http.get<ApiResponse<{ items: ScrapeRule[]; total: number }>>('/api/rules', {
      params: enabled !== undefined ? { enabled: String(enabled) } : {},
    }).then((r) => r.data),

  get: (ruleId: string) =>
    http.get<ApiResponse<ScrapeRule>>(`/api/rules/${ruleId}`).then((r) => r.data),

  create: (payload: RuleCreatePayload) =>
    http.post<ApiResponse<ScrapeRule>>('/api/rules', payload).then((r) => r.data),

  update: (ruleId: string, payload: RuleUpdatePayload) =>
    http.put<ApiResponse<ScrapeRule>>(`/api/rules/${ruleId}`, payload).then((r) => r.data),

  remove: (ruleId: string) =>
    http.delete<ApiResponse<null>>(`/api/rules/${ruleId}`).then((r) => r.data),

  enable: (ruleId: string) =>
    http.post<ApiResponse<ScrapeRule>>(`/api/rules/${ruleId}/enable`).then((r) => r.data),

  disable: (ruleId: string) =>
    http.post<ApiResponse<ScrapeRule>>(`/api/rules/${ruleId}/disable`).then((r) => r.data),

  toggle: (ruleId: string) =>
    http.post<ApiResponse<ScrapeRule>>(`/api/rules/${ruleId}/toggle`).then((r) => r.data),
}

/* ================================================================
   Data API
   ================================================================ */

export const dataApi = {
  latest: (ruleId?: string) =>
    http.get<ApiResponse<LatestDataItem | { items: LatestDataItem[]; total: number }>>(
      '/api/data/latest',
      { params: ruleId ? { rule_id: ruleId } : {} },
    ).then((r) => r.data),

  history: (params?: { rule_id?: string; page?: number; page_size?: number }) =>
    http.get<ApiResponse<Paginated<HistoryItem>>>('/api/data/history', { params }).then((r) => r.data),

  logs: (params?: { rule_id?: string; page?: number; page_size?: number }) =>
    http.get<ApiResponse<Paginated<LogItem>>>('/api/data/logs', { params }).then((r) => r.data),

  status: () =>
    http.get<ApiResponse<SchedulerStatus>>('/api/data/status').then((r) => r.data),
}

/* ================================================================
   Control API
   ================================================================ */

export const controlApi = {
  trigger: (ruleId: string) =>
    http.post<ApiResponse<{ rule_id: string; rule_name: string; row_count: number; elapsed_seconds: number; rows: Record<string, unknown>[] }>>(
      `/api/control/trigger/${ruleId}`,
    ).then((r) => r.data),

  schedulerStart: () =>
    http.post<ApiResponse<SchedulerStatus>>('/api/control/scheduler/start').then((r) => r.data),

  schedulerStop: () =>
    http.post<ApiResponse<null>>('/api/control/scheduler/stop').then((r) => r.data),

  switchBrowserMode: (mode: 'headless' | 'gui') =>
    http.post<ApiResponse<{ mode: string }>>('/api/control/browser/mode', { mode }).then((r) => r.data),
}

/* ================================================================
   Window API
   ================================================================ */

export interface WindowStatus {
  running: boolean
  pid: number | null
  uptime_seconds: number
}

export const windowApi = {
  start: () =>
    http.post<ApiResponse<WindowStatus>>('/api/control/window/start').then((r) => r.data),

  stop: () =>
    http.post<ApiResponse<WindowStatus>>('/api/control/window/stop').then((r) => r.data),

  restart: () =>
    http.post<ApiResponse<WindowStatus>>('/api/control/window/restart').then((r) => r.data),

  status: () =>
    http.get<ApiResponse<WindowStatus>>('/api/control/window/status').then((r) => r.data),
}

/* ================================================================
   SSE endpoint URL
   ================================================================ */

export const SSE_URL = `${BASE}/api/sse/stream`

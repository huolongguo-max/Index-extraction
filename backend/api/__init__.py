"""
FastAPI 接口路由模块

子模块:
  rules      — 规则管理 CRUD + 启用/停用
  data       — 最新数据 / 历史记录 / 运行日志
  control    — 手动触发 / 调度启停 / 浏览器模式
  sse        — SSE 实时数据推送

严格 Restful 规范: GET 查 | POST 新增/操作 | PUT 修改 | DELETE 删除
"""

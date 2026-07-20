"""
Index-extraction PyQt6 桌面悬浮窗
Apple 简约风格 — 玻璃态背景 + 系统托盘 + SSE 实时数据

组件:
  floating_window  — 主悬浮窗（完整版：无边框 / 置顶 / 拖拽 / 缩放 / 托盘）
  styles           — Apple 设计令牌
  components/      — 可复用 UI 组件（GlassCard / StatusDot / AppleTable / KPIStat）
"""

from window.floating_window import FloatingWindow
from window.styles import colors, spacing, radius, typography, motion, shadow

__all__ = [
    "FloatingWindow",
    "colors", "spacing", "radius", "typography", "motion", "shadow",
]

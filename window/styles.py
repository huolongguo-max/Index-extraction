"""
Apple-style 设计令牌 (Design Tokens)
来源：ui-ux-pro-max 数据 — Glassmorphism + Bento Box + Spatial UI / VisionOS
Apple Human Interface Guidelines 参考色值 & 间距系统
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AppleColors:
    """Apple 系统色彩体系 — 基于 Spatial UI / Glassmorphism 数据"""

    # ============ 系统色 (System Colors) ============
    system_blue: str = "#007AFF"          # Apple 标志性系统蓝
    system_blue_light: str = "#409CFF"    # 浅系统蓝 (hover / active)
    system_blue_dark: str = "#0060CC"     # 深系统蓝 (press)

    system_green: str = "#34C759"
    system_orange: str = "#FF9500"
    system_red: str = "#FF3B30"
    system_pink: str = "#FF2D55"
    system_purple: str = "#AF52DE"
    system_teal: str = "#5AC8FA"

    # ============ 玻璃态表面 (Glass Surfaces - 浅色模式) ============
    # 参考: macOS 控制中心 / 通知中心浅色玻璃
    glass_bg_primary: str = "rgba(255, 255, 255, 0.72)"     # 主玻璃表面
    glass_bg_secondary: str = "rgba(255, 255, 255, 0.55)"   # 次要玻璃表面
    glass_bg_tertiary: str = "rgba(255, 255, 255, 0.35)"    # 三级玻璃表面
    glass_bg_elevated: str = "rgba(255, 255, 255, 0.88)"    # 悬浮/提升表面 (如弹窗)

    # ============ 不透明表面 (Opaque Surfaces - 浅色模式) ============
    opaque_bg_primary: str = "#FBFBFD"      # 系统主背景
    opaque_bg_secondary: str = "#F0F0F2"    # 系统次背景
    opaque_bg_tertiary: str = "#E5E5EA"     # 系统三级背景

    # ============ 分隔 & 边框 ============
    separator: str = "rgba(0, 0, 0, 0.10)"           # 标准分隔线
    separator_opaque: str = "#D1D1D6"                 # 不透明分隔线
    border_glass: str = "rgba(0, 0, 0, 0.12)"        # 玻璃边框
    border_prominent: str = "rgba(0, 0, 0, 0.20)"    # 突出边框

    # ============ 文字色 (Text Colors - 浅色模式) ============
    text_primary: str = "rgba(0, 0, 0, 0.88)"         # 主文字 (标题)
    text_secondary: str = "rgba(0, 0, 0, 0.60)"       # 次要文字 (正文)
    text_tertiary: str = "rgba(0, 0, 0, 0.35)"        # 三级文字 (占位 / disabled)
    text_quaternary: str = "rgba(0, 0, 0, 0.18)"      # 四级文字 (极弱)

    # ============ 填充色 (Fill Colors - 浅色模式) ============
    fill_primary: str = "rgba(0, 0, 0, 0.08)"         # 主填充 (按钮背景)
    fill_secondary: str = "rgba(0, 0, 0, 0.05)"       # 次填充
    fill_tertiary: str = "rgba(0, 0, 0, 0.03)"        # 三级填充


@dataclass
class AppleSpacing:
    """Apple 8pt 间距系统"""
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 20
    xxl: int = 24
    xxxl: int = 32


@dataclass
class AppleRadius:
    """Apple 圆角系统"""
    sm: int = 6       # 小组件 (button, input)
    md: int = 10      # 中等组件
    lg: int = 14      # 卡片 / 面板
    xl: int = 18      # 大面板
    xxl: int = 24     # 弹窗 / 主容器
    full: int = 999   # 胶囊 / 圆形


@dataclass
class AppleTypography:
    """Apple SF Pro 风格排版 (Inter 作为桌面替代)"""
    font_family: str = "Inter, SF Pro Display, -apple-system, Helvetica Neue, sans-serif"

    # 字号层级
    caption2: int = 11       # 极小程序标注
    caption1: int = 12       # 辅助说明
    footnote: int = 13       # 脚注
    subheadline: int = 15    # 副标题
    callout: int = 16        # 强调正文
    body: int = 17           # 正文
    headline: int = 17       # 标题 (Semibold)
    title3: int = 20         # 三级标题
    title2: int = 22         # 二级标题
    title1: int = 28         # 一级标题
    large_title: int = 34    # 大标题

    # 字重
    weight_regular: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600
    weight_bold: int = 700


@dataclass
class AppleMotion:
    """Apple 动效系统 (参考 HIG + ui-ux-pro-max gsap data)"""
    duration_fast: int = 150       # 微交互 (hover 反馈)
    duration_normal: int = 250     # 标准过渡
    duration_slow: int = 350       # 页面级过渡
    duration_spring: int = 500     # 弹性动画

    easing_default: str = "power1.out"
    easing_spring: str = "cubic-bezier(0.34, 1.56, 0.64, 1)"  # Apple 弹性

    # 动效位移量 (Apple 微交互规范: ≤2px)
    hover_y_offset: int = -1
    press_scale: float = 0.97


@dataclass
class AppleShadow:
    """Apple 阴影系统 (玻璃态多层阴影)"""
    # 卡片阴影
    card_sm: str = "0 1px 3px rgba(0, 0, 0, 0.24)"
    card_md: str = "0 4px 12px rgba(0, 0, 0, 0.32)"
    card_lg: str = "0 8px 32px rgba(0, 0, 0, 0.40)"

    # 玻璃面板阴影
    glass_sm: str = "0 2px 8px rgba(0, 0, 0, 0.20)"
    glass_md: str = "0 8px 24px rgba(0, 0, 0, 0.28)"
    glass_lg: str = "0 12px 48px rgba(0, 0, 0, 0.36)"

    # 提升式阴影 (浮窗特有)
    elevated: str = (
        "0 0 0 0.5px rgba(255, 255, 255, 0.15), "  # 高光描边
        "0 2px 6px rgba(0, 0, 0, 0.16), "           # 近阴影
        "0 8px 30px rgba(0, 0, 0, 0.32)"             # 环境阴影
    )


# ============ 全局设计令牌实例 ============
colors = AppleColors()
spacing = AppleSpacing()
radius = AppleRadius()
typography = AppleTypography()
motion = AppleMotion()
shadow = AppleShadow()


# ============ PyQt6 样式表生成器 ============

def generate_global_stylesheet() -> str:
    """
    生成 PyQt6 全局 QSS 样式表
    将 Apple 设计令牌映射为 Qt 样式表语法
    参考: ui-ux-pro-max Bento Box + Glassmorphism data
    """
    c = colors
    return f"""
    /* ============================================
       Index-extraction — Apple Glassmorphism 全局样式
       参考: Spatial UI / visionOS + macOS HIG
       ============================================ */

    /* ----- 全局基础 ----- */
    QWidget {{
        background: transparent;
        color: {c.text_primary};
        font-family: 'SF Pro Display', 'Inter', '-apple-system', 'Helvetica Neue', sans-serif;
        font-size: 13px;
    }}

    /* ----- 主窗口 (玻璃态背景) ----- */
    QMainWindow {{
        background: {c.glass_bg_primary};
        border: 0.5px solid {c.border_glass};
    }}

    /* ----- 标签 ----- */
    QLabel {{
        color: {c.text_primary};
        background: transparent;
        border: none;
    }}

    QLabel[level="secondary"] {{
        color: {c.text_secondary};
    }}

    QLabel[level="tertiary"] {{
        color: {c.text_tertiary};
    }}

    /* ----- 按钮 (Apple 风格) ----- */
    QPushButton {{
        background: {c.fill_primary};
        color: {c.system_blue};
        border: none;
        border-radius: {radius.md}px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background: {c.fill_secondary};
    }}

    QPushButton:pressed {{
        background: {c.fill_primary};
        color: {c.system_blue_dark};
    }}

    QPushButton[primary="true"] {{
        background: {c.system_blue};
        color: #FFFFFF;
        font-weight: 600;
    }}

    QPushButton[primary="true"]:hover {{
        background: {c.system_blue_light};
    }}

    QPushButton[primary="true"]:pressed {{
        background: {c.system_blue_dark};
    }}

    QPushButton[danger="true"] {{
        background: rgba(255, 59, 48, 0.15);
        color: {c.system_red};
    }}

    QPushButton[danger="true"]:hover {{
        background: rgba(255, 59, 48, 0.25);
    }}

    /* ----- 输入框 (玻璃态) ----- */
    QLineEdit, QTextEdit {{
        background: {c.fill_secondary};
        color: {c.text_primary};
        border: 0.5px solid {c.separator};
        border-radius: {radius.md}px;
        padding: 6px 10px;
        selection-background-color: {c.system_blue};
        selection-color: #FFFFFF;
    }}

    QLineEdit:focus, QTextEdit:focus {{
        border: 1.5px solid {c.system_blue};
        background: {c.fill_primary};
    }}

    QLineEdit::placeholder {{
        color: {c.text_tertiary};
    }}

    /* ----- 滚动条 (Apple 风格 - 超薄) ----- */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.15);
        border-radius: 3px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 0.28);
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: rgba(255, 255, 255, 0.15);
        border-radius: 3px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: rgba(255, 255, 255, 0.28);
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ----- 进度条 ----- */
    QProgressBar {{
        background: {c.fill_secondary};
        border-radius: 3px;
        height: 4px;
        border: none;
    }}

    QProgressBar::chunk {{
        background: {c.system_blue};
        border-radius: 3px;
    }}

    /* ----- 工具提示 ----- */
    QToolTip {{
        background: {c.glass_bg_elevated};
        color: {c.text_primary};
        border: 0.5px solid {c.border_glass};
        border-radius: {radius.sm}px;
        padding: 4px 8px;
        font-size: 11px;
    }}
    """

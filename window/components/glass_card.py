"""
Apple 风格玻璃态卡片组件 (Glassmorphism Card)
参考: visionOS 玻璃表面 + macOS 控制中心面板
ui-ux-pro-max data: Glassmorphism (Style #3) + Bento Box (#39)
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QBrush, QColor, QPainterPath, QLinearGradient

from window.styles import colors, radius, spacing, shadow


class GlassCard(QFrame):
    """
    苹果风格玻璃态卡片

    视觉特征:
    - 半透明背景 (rgba(28, 28, 30, 0.55-0.77))
    - 圆角 14-18px
    - 微细白色描边 (rgba white 0.15)
    - 多层次投影模拟深度
    - hover 时轻微上浮 (Apple 微交互: ≤2px)

    使用方式:
        card = GlassCard(title="数据概览")
        card.add_widget(some_child_widget)
    """

    def __init__(
        self,
        title: str = "",
        parent: QWidget | None = None,
        level: str = "secondary",  # primary | secondary | tertiary
        radius_size: int = radius.lg,
    ):
        super().__init__(parent)
        self._title = title
        self._card_level = level
        self._radius_size = radius_size
        self._is_hovered = False
        self._elevation = 0.0  # 0.0 ~ 1.0 提升量，用于动画

        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        """初始化卡片 UI 结构"""
        self.setObjectName("GlassCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # 主布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            spacing.lg, spacing.lg, spacing.lg, spacing.lg
        )
        self._layout.setSpacing(spacing.md)

        # 标题
        if self._title:
            self._title_label = QLabel(self._title)
            self._title_label.setObjectName("cardTitle")
            self._title_label.setStyleSheet(f"""
                QLabel#cardTitle {{
                    font-size: 13px;
                    font-weight: 600;
                    color: {colors.text_secondary};
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    padding-bottom: {spacing.sm}px;
                    border-bottom: 0.5px solid {colors.separator};
                }}
            """)
            self._layout.addWidget(self._title_label)

        # 内容区域
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(spacing.sm)
        self._layout.addWidget(self._content)

    def _apply_style(self):
        """根据 level 应用对应玻璃态样式"""
        opacity_map = {
            "primary": colors.glass_bg_primary,
            "secondary": colors.glass_bg_secondary,
            "tertiary": colors.glass_bg_tertiary,
        }
        bg_color = opacity_map.get(self._card_level, colors.glass_bg_secondary)

        self.setStyleSheet(f"""
            QFrame#GlassCard {{
                background: {bg_color};
                border: 0.5px solid {colors.border_glass};
                border-radius: {self._radius_size}px;
            }}
        """)

    def add_widget(self, widget: QWidget):
        """向卡片内容区域添加组件"""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        """向卡片内容区域添加布局"""
        self._content_layout.addLayout(layout)

    def set_title(self, title: str):
        self._title_label.setText(title)

    # ============ Hover 浮升效果 ============

    def enterEvent(self, event):
        """鼠标进入：卡片浮升"""
        self._is_hovered = True
        self._animate_elevation(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：卡片恢复"""
        self._is_hovered = False
        self._animate_elevation(0.0)
        super().leaveEvent(event)

    def _animate_elevation(self, target: float):
        """弹性动画驱动 elevation 属性变化"""
        anim = QPropertyAnimation(self, b"elevation")
        anim.setDuration(250)  # Apple 标准过渡
        anim.setStartValue(self._elevation)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

    def get_elevation(self) -> float:
        return self._elevation

    def set_elevation(self, val: float):
        self._elevation = val
        self.update()  # 触发重绘

    elevation = pyqtProperty(float, get_elevation, set_elevation)

    def paintEvent(self, event):
        """自定义绘制：添加多层投影 (Apple 阴影系统)"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 根据 elevation 混合阴影强度
        if self._elevation > 0.01:
            path = QPainterPath()
            path.addRoundedRect(self.rect(), self._radius_size, self._radius_size)

            # 环境阴影 (大范围低不透明度)
            env_color = QColor(0, 0, 0, int(40 + 20 * self._elevation))
            env_offset = 8 + 4 * self._elevation
            painter.setBrush(QBrush(env_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path.translated(0, env_offset))

        painter.end()


class BentoGrid(QFrame):
    """
    Apple 风格 Bento Box 网格布局
    参考: Apple 官网功能展示 + ui-ux-pro-max Bento Box Grid (#39)

    不规则网格，模块化卡片，大小变化
    """

    def __init__(self, columns: int = 4, parent: QWidget | None = None):
        super().__init__(parent)
        self._columns = columns
        self._cards: list[GlassCard] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing.lg)

        self._grid = QWidget()
        self._grid_layout = QVBoxLayout(self._grid)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(spacing.lg)
        self._layout.addWidget(self._grid)

    def add_card(self, card: GlassCard, col_span: int = 1, row_span: int = 1):
        """
        添加卡片到 Bento Grid
        col_span: 占用列数 (1~columns)
        row_span: 占用行数 (1~N)
        """
        self._cards.append({
            "card": card,
            "col_span": col_span,
            "row_span": row_span,
        })
        self._rebuild_grid()

    def _rebuild_grid(self):
        """重建网格布局"""
        # 清除旧布局
        for i in reversed(range(self._grid_layout.count())):
            item = self._grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        # 逐行构建
        row_widgets = []
        current_row = QWidget()
        row_layout = QHBoxLayout(current_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(spacing.lg)
        col_used = 0

        for entry in self._cards:
            card = entry["card"]
            span = entry["col_span"]

            if col_used + span > self._columns:
                self._grid_layout.addWidget(current_row)
                current_row = QWidget()
                row_layout = QHBoxLayout(current_row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(spacing.lg)
                col_used = 0

            # 设置卡片伸缩比例
            row_layout.addWidget(card, stretch=span)
            col_used += span

        if col_used > 0:
            row_layout.addStretch(self._columns - col_used)
            self._grid_layout.addWidget(current_row)

"""
Apple 风格状态指示器
参考: macOS 状态栏 / iOS 状态点 + Apple 产品设计语言
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QBrush, QColor, QPainterPath, QFont

from window.styles import colors, radius, spacing


class StatusDot(QWidget):
    """
    Apple 风格状态圆点
    用于指示连接状态、抓取进度、数据更新

    颜色语义:
    - green: 正常 / 在线 / 成功
    - orange: 警告 / 处理中
    - red: 错误 / 离线 / 失败
    - blue: 信息 / 更新中
    - grey: 未激活 / 闲置

    动画:
    - pulse: 脉冲动画 (活跃状态)
    - solid: 静态 (稳定状态)
    """

    def __init__(
        self,
        status: str = "grey",  # green | orange | red | blue | grey
        size: int = 8,
        animated: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._status = status
        self._dot_size = size
        self._animated = animated
        self._opacity = 1.0
        self.setFixedSize(size + 8, size + 8)

        if animated:
            self._pulse_timer = QTimer(self)
            self._pulse_timer.timeout.connect(self._toggle_pulse)
            self._pulse_timer.start(1500)  # Apple 呼吸节奏
            self._pulse_phase = True

    def _status_color(self) -> QColor:
        """状态 → 颜色映射 (Apple 系统色)"""
        color_map = {
            "green": QColor(colors.system_green),
            "orange": QColor(colors.system_orange),
            "red": QColor(colors.system_red),
            "blue": QColor(colors.system_blue),
            "grey": QColor(142, 142, 147),      # Apple systemGray
        }
        return color_map.get(self._status, QColor(142, 142, 147))

    def _toggle_pulse(self):
        """呼吸动画脉冲切换"""
        if not self._animated:
            return
        self._pulse_phase = not self._pulse_phase
        self._animate_opacity(0.4 if self._pulse_phase else 1.0)

    def _animate_opacity(self, target: float):
        anim = QPropertyAnimation(self, b"dotOpacity")
        anim.setDuration(700)  # Apple 呼吸节奏
        anim.setStartValue(self._opacity)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.start()

    def get_dot_opacity(self) -> float:
        return self._opacity

    def set_dot_opacity(self, val: float):
        self._opacity = val
        self.update()

    dotOpacity = pyqtProperty(float, get_dot_opacity, set_dot_opacity)

    def set_status(self, status: str, animated: bool = False):
        self._status = status
        self._animated = animated
        if animated and not hasattr(self, '_pulse_timer'):
            self._pulse_timer = QTimer(self)
            self._pulse_timer.timeout.connect(self._toggle_pulse)
            self._pulse_timer.start(1500)
            self._pulse_phase = True
        elif not animated and hasattr(self, '_pulse_timer'):
            self._pulse_timer.stop()
            self._opacity = 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self._status_color()
        color.setAlphaF(self._opacity)

        # 外圈光晕 (玻璃态风格)
        glow_color = QColor(color)
        glow_color.setAlphaF(self._opacity * 0.2)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        center = self.rect().center()
        painter.drawEllipse(center, self._dot_size // 2 + 3, self._dot_size // 2 + 3)

        # 内层实心圆点
        painter.setBrush(QBrush(color))
        painter.drawEllipse(center, self._dot_size // 2, self._dot_size // 2)

        painter.end()


class ConnectionBadge(QWidget):
    """
    连接状态徽章 — 圆点 + 文字，苹果风格
    用于悬浮窗顶部显示后端连接状态
    """

    def __init__(self, label: str = "未连接", status: str = "grey", parent=None):
        super().__init__(parent)
        self._label = label
        self._status = status

        layout = QHBoxLayout(self)
        layout.setContentsMargins(spacing.sm, 2, spacing.md, 2)
        layout.setSpacing(spacing.sm)

        self._dot = StatusDot(status=status, size=6, animated=(status == "blue"))
        layout.addWidget(self._dot)

        self._label_widget = QLabel(label)
        self._label_widget.setStyleSheet(f"""
            QLabel {{
                color: {colors.text_secondary};
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }}
        """)
        layout.addWidget(self._label_widget)

        self.setStyleSheet(f"""
            ConnectionBadge {{
                background: {colors.fill_secondary};
                border-radius: {radius.full}px;
            }}
        """)

    def set_status(self, label: str, status: str):
        self._label = label
        self._status = status
        self._dot.set_status(status, animated=(status == "blue"))
        self._label_widget.setText(label)


class KPIStat(QWidget):
    """
    Apple 风格 KPI 数据卡片 — 大数字 + 标签 + 趋势箭头
    参考: Apple Health app 数据展示
    """

    def __init__(
        self,
        value: str = "--",
        label: str = "指标",
        trend: str = "",      # ↑ ↓ → or +5%
        trend_positive: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._value = value
        self._label = label
        self._trend = trend
        self._trend_positive = trend_positive

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 数值
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 28px;
                font-weight: 700;
                color: {colors.text_primary};
                background: transparent;
            }}
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(value_label)

        # 标签 + 趋势
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(spacing.sm)

        name_label = QLabel(label)
        name_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                font-weight: 500;
                color: {colors.text_tertiary};
                background: transparent;
            }}
        """)
        bottom_row.addWidget(name_label)

        if trend:
            trend_color = colors.system_green if trend_positive else colors.system_red
            trend_arrow = "↑" if trend_positive else "↓"
            trend_label = QLabel(f"{trend_arrow} {trend}")
            trend_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 12px;
                    font-weight: 600;
                    color: {trend_color};
                    background: transparent;
                }}
            """)
            bottom_row.addWidget(trend_label)

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

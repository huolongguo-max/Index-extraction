"""
Apple 风格数据表格组件
参考: macOS Numbers / TableView — 玻璃态行、微妙分隔、悬浮高亮
"""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QWidget, QVBoxLayout, QLabel,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor

from window.styles import colors, radius, spacing


class AppleTable(QTableWidget):
    """
    Apple 风格数据表

    视觉特征:
    - 透明背景，玻璃态行
    - 行 hover 高亮 (微弱填充变色)
    - 无网格线，用行间距替代
    - 圆角表头
    - 等宽数字列
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_style()
        self._empty_label: QLabel | None = None

    def _init_style(self):
        """应用 Apple 表格样式"""
        self.setObjectName("AppleTable")

        # 基本设置
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().setVisible(False)
        self.setWordWrap(False)

        # 样式表
        self.setStyleSheet(f"""
            QTableWidget#AppleTable {{
                background: transparent;
                border: none;
                gridline-color: transparent;
                color: {colors.text_primary};
                font-size: 12px;
            }}

            QTableWidget#AppleTable::item {{
                padding: 6px 10px;
                border-bottom: 0.5px solid {colors.separator};
                background: transparent;
            }}

            QTableWidget#AppleTable::item:selected {{
                background: {colors.fill_primary};
                color: {colors.text_primary};
            }}

            QTableWidget#AppleTable::item:hover {{
                background: {colors.fill_tertiary};
            }}

            QHeaderView::section {{
                background: {colors.fill_secondary};
                color: {colors.text_secondary};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                padding: 8px 10px;
                border: none;
                border-bottom: 0.5px solid {colors.separator};
                border-radius: {radius.sm}px;
            }}
        """)

        # 表头交互
        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setStretchLastSection(True)

    def populate_data(self, columns: list[str], rows: list[dict]):
        """
        填入数据

        Args:
            columns: 列名列表 ['姓名', '金额', '日期']
            rows: 行数据列表 [{'姓名': '张三', '金额': 100, ...}, ...]
        """
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        if not rows:
            self.setRowCount(0)
            self._show_empty_state()
            return

        self._hide_empty_state()
        self.setRowCount(len(rows))

        for row_idx, row_data in enumerate(rows):
            for col_idx, col_name in enumerate(columns):
                value = row_data.get(col_name, "")
                display_text = self._format_cell(value)

                item = QTableWidgetItem(display_text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # 右对齐数字列
                if isinstance(value, (int, float)):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )

                self.setItem(row_idx, col_idx, item)

        # 自适应列宽
        self.resizeColumnsToContents()

    def _format_cell(self, value) -> str:
        """格式化单元格显示"""
        if value is None:
            return "--"
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _show_empty_state(self):
        """显示空数据状态"""
        if not self._empty_label:
            self._empty_label = QLabel("暂无数据", self)
            self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors.text_tertiary};
                    font-size: 14px;
                    font-weight: 500;
                    background: transparent;
                    padding: 32px;
                }}
            """)
        self._empty_label.setVisible(True)

    def _hide_empty_state(self):
        """隐藏空数据状态"""
        if self._empty_label:
            self._empty_label.setVisible(False)

    def resizeEvent(self, event):
        """保持空状态标签居中"""
        super().resizeEvent(event)
        if self._empty_label:
            self._empty_label.setGeometry(self.rect())

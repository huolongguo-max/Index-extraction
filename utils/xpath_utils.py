"""
XPath 行列交叉定位工具 — 固定模板化生成器

核心原则（RPA 专属强制规范）：
  1. 禁止浏览器自动生成的绝对路径 XPath
  2. 统一使用手写「行关键词 + 列表头」交叉定位
  3. 所有文字匹配使用 normalize-space() 适配隐形空格
  4. 仅适配 DIV 结构网页表格，适配 Vue 动态渲染 DOM
  5. 全程不手动数序号、不使用绝对路径

用法（纯工具，零业务逻辑）：
    from utils.xpath_utils import XPathBuilder  （类方法调用）
    或
    from utils.xpath_utils import xp            （预实例便捷调用）

    # 行关键词 + 列表头 → 单元格 XPath
    xp.cell("张三", "金额")   → 完整表达式

    # 自定义容器
    xp.cell("张三", "金额",
            row_xpath="//div[contains(@class,'data-row')]",
            header_row="//div[contains(@class,'thead')]",
            cell_class="field")
"""

import re
from typing import Optional


class XPathBuilder:
    """
    行列交叉 XPath 固定模板生成器

    设计思路：
      不依赖浏览器自动生成、不手动数序号。
      通过「行内关键词」定位目标行，通过「表头文字」定位目标列，
      输出无绝对路径的可执行 XPath 表达式。
    """

    # ----------------------------------------------------------------
    # 原子方法
    # ----------------------------------------------------------------

    @staticmethod
    def normalize(text: str) -> str:
        """
        构造 normalize-space() 条件，适配隐形空格 & 引号转义

        >>> XPathBuilder.normalize("金额")
        "normalize-space(text())='金额'"
        >>> XPathBuilder.normalize("it's ok")
        "normalize-space(text())='it'  → 自动处理单引号
        """
        # 优先用双引号包裹，避免文本中的单引号冲突
        if "'" in text:
            escaped = text.replace('"', '&quot;')
            return f'normalize-space(text())="{escaped}"'
        else:
            escaped = text.replace("'", "\\'")
            return f"normalize-space(text())='{escaped}'"

    @staticmethod
    def contains_class(class_name: str, tag: str = "div") -> str:
        """生成 contains(@class, '...') 条件（适配 Vue CSS Modules 哈希类名）"""
        return f"contains(@class, '{class_name}')"

    # ----------------------------------------------------------------
    # 行定位
    # ----------------------------------------------------------------

    @staticmethod
    def row_by_keyword(
        keyword: str,
        row_xpath: str = "//div[contains(@class, 'table-row')]",
    ) -> str:
        """
        通过行内关键词定位目标行

        匹配逻辑：在 row 容器内，寻找任意后代节点文本 == keyword

        Args:
            keyword:   行内关键词（例如：单元格中的文字、名字、ID）
            row_xpath: 行容器 XPath 基础表达式
        """
        norm = XPathBuilder.normalize(keyword)
        return f"({row_xpath})[.//*[{norm}]]"

    @staticmethod
    def row_by_index(
        index: int,
        row_xpath: str = "//div[contains(@class, 'table-row')]",
    ) -> str:
        """通过行号定位目标行（1-based）"""
        return f"({row_xpath})[{index}]"

    # ----------------------------------------------------------------
    # 列定位
    # ----------------------------------------------------------------

    @staticmethod
    def column_index_by_header(
        header_text: str,
        header_row_xpath: str = "//div[contains(@class, 'table-header')]",
        header_cell_tag: str = "div",
    ) -> str:
        """
        根据表头文字计算列序号 XPath 片段

        原理：count(目标表头之前的所有兄弟表头) + 1

        Returns:
            可嵌入的 XPath 数字片段，如 "count(//div[contains(@class,'header')]
            //div[normalize-space(text())='金额']/preceding-sibling::div) + 1"
        """
        norm_header = XPathBuilder.normalize(header_text)
        header_el = f"{header_row_xpath}//{header_cell_tag}[{norm_header}]"
        return f"count({header_el}/preceding-sibling::{header_cell_tag}) + 1"

    # ----------------------------------------------------------------
    # 单元格定位（核心：行列交叉）
    # ----------------------------------------------------------------

    @staticmethod
    def cell(
        row_keyword: str,
        header_text: str,
        *,
        row_xpath: str = "//div[contains(@class, 'table-row')]",
        header_row_xpath: str = "//div[contains(@class, 'table-header')]",
        cell_tag: str = "div",
        cell_class: Optional[str] = None,
        header_cell_tag: str = "div",
    ) -> str:
        """
        【核心方法】行关键词 + 列表头 → 单元格完整 XPath

        固定模板（内部）:
          (  (行容器)[.//*[normalize-space(text())='<row_keyword>']]
             //<cell>[count-index]  )

        意思：先找含关键词的行，再在该行内取第 N 个子元素（N = 表头序号）

        Args:
            row_keyword:      行关键词文字（如 "张三"、"订单001"）
            header_text:      列表头文字（如 "金额"、"日期"、"状态"）
            row_xpath:        行容器基础 XPath
            header_row_xpath: 表头行容器 XPath
            cell_tag:         单元格标签名，默认 "div"
            cell_class:       单元格 CSS class（可选，用于 contains(@class, ...)）
            header_cell_tag:  表头单元格标签名，默认 "div"

        Returns:
            可直接用于 Selenium find_element(By.XPATH, ...) 的完整表达式

        Example:
            >>> XPathBuilder.cell("张三", "金额")
            '(//div[contains(@class, 'table-row')])
             [.//*[normalize-space(text())='张三']]
             //div[count(//div[contains(@class, 'table-header')]
             //div[normalize-space(text())='金额']/preceding-sibling::div) + 1]'
        """
        # 1) 行 XPath（按关键词定位）
        row_xp = XPathBuilder.row_by_keyword(row_keyword, row_xpath)

        # 2) 列索引 XPath（按表头文字计算序号）
        col_idx_xp = XPathBuilder.column_index_by_header(
            header_text, header_row_xpath, header_cell_tag
        )

        # 3) 单元格匹配条件：按序号定位 & 可选 class
        cell_cond = cell_tag
        if cell_class:
            cell_cond += f"[{XPathBuilder.contains_class(cell_class)}]"

        # 4) 组装最终表达式
        return f"({row_xp}//{cell_cond})[{col_idx_xp}]"

    # ----------------------------------------------------------------
    # 快捷方法：整列 / 整行 / 区域
    # ----------------------------------------------------------------

    @staticmethod
    def column_cells(
        header_text: str,
        *,
        row_xpath: str = "//div[contains(@class, 'table-row')]",
        header_row_xpath: str = "//div[contains(@class, 'table-header')]",
        cell_tag: str = "div",
        cell_class: Optional[str] = None,
        header_cell_tag: str = "div",
    ) -> str:
        """
        定位整列所有单元格（所有行中，指定表头对应的列）

        Returns 可迭代取的 XPath，搭配 driver.find_elements() 取所有值
        """
        cell_cond = cell_tag
        if cell_class:
            cell_cond += f"[{XPathBuilder.contains_class(cell_class)}]"

        col_idx = XPathBuilder.column_index_by_header(
            header_text, header_row_xpath, header_cell_tag
        )
        return f"({row_xpath}//{cell_cond})[{col_idx}]"

    @staticmethod
    def all_cells_in_row(
        row_keyword: str,
        *,
        row_xpath: str = "//div[contains(@class, 'table-row')]",
        cell_tag: str = "div",
        cell_class: Optional[str] = None,
    ) -> str:
        """
        定位某行所有单元格（返回该行所有 cell 的 XPath）

        用于提取整行数据
        """
        row_xp = XPathBuilder.row_by_keyword(row_keyword, row_xpath)
        cell_cond = cell_tag
        if cell_class:
            cell_cond += f"[{XPathBuilder.contains_class(cell_class)}]"
        return f"{row_xp}//{cell_cond}"

    @staticmethod
    def table_region(
        row_start: int,
        row_end: int,
        header_text: str,
        *,
        row_xpath: str = "//div[contains(@class, 'table-row')]",
        header_row_xpath: str = "//div[contains(@class, 'table-header')]",
        cell_tag: str = "div",
        header_cell_tag: str = "div",
    ) -> str:
        """
        定位表格区域（多行 × 指定列）

        Args:
            row_start: 起始行号（1-based）
            row_end:   结束行号（1-based）
            header_text: 列表头文字
        """
        col_idx = XPathBuilder.column_index_by_header(
            header_text, header_row_xpath, header_cell_tag
        )
        return (
            f"({row_xpath})"
            f"[position() >= {row_start} and position() <= {row_end}]"
            f"//{cell_tag}[{col_idx}]"
        )

    # ----------------------------------------------------------------
    # 分页 / 翻页按钮
    # ----------------------------------------------------------------

    @staticmethod
    def pagination(text: str = "下一页") -> str:
        """翻页按钮 XPath"""
        norm = XPathBuilder.normalize(text)
        return f"//button[{norm}] | //a[{norm}] | //span[{norm}]"

    @staticmethod
    def pagination_next() -> str:
        """下一页按钮（多语言 fallback）"""
        texts = ["下一页", "下一頁", "Next", ">", "›", "»"]
        parts = [XPathBuilder.normalize(t) for t in texts]
        joined = " or ".join(parts)
        return f"//button[{joined}] | //a[{joined}] | //span[{joined}]"

    # ----------------------------------------------------------------
    # 表头列表
    # ----------------------------------------------------------------

    @staticmethod
    def header_labels(
        header_row_xpath: str = "//div[contains(@class, 'table-header')]",
        cell_tag: str = "div",
    ) -> str:
        """获取所有表头文字 XPath（配合 find_elements 取 list）"""
        return f"{header_row_xpath}//{cell_tag}"

    @staticmethod
    def row_count(
        row_xpath: str = "//div[contains(@class, 'table-row')]",
    ) -> str:
        """计算表格行数"""
        return f"count({row_xpath})"


# ================================================================
# XPath 表达式验证（纯语法检查，不依赖浏览器）
# ================================================================

class XPathValidator:
    """XPath 语法校验器 — 纯工具层，零浏览器依赖"""

    # 自动生成绝对路径特征模式（如 /div[1]/div[3]/div[2]/...）
    _AUTO_GENERATED_PATTERN = re.compile(
        r'(?:div|span|section|article|tr|td)\[\d+\]'
        r'/(?:div|span|section|article|tr|td)\[\d+\]'
        r'/(?:div|span|section|article|tr|td)\[\d+\]',
    )

    @staticmethod
    def validate(xpath: str) -> tuple[bool, Optional[str]]:
        """
        校验 XPath 表达式

        Returns:
            (is_valid, error_message)
        """
        if not xpath or not isinstance(xpath, str):
            return False, "XPath 为空或非字符串类型"

        # 拦截浏览器自动生成风格（连续 3+ 索引层级）
        if XPathValidator._AUTO_GENERATED_PATTERN.search(xpath):
            return False, (
                "拒绝浏览器自动生成的绝对路径 XPath（含连续数字索引）。"
                "请使用 XPathBuilder.cell(row_keyword, header_text) 生成。"
            )

        # 检查 normalize-space 使用（推荐但非强制）
        if "text()=" in xpath and "normalize-space" not in xpath:
            # 仅建议，不阻断
            pass

        return True, None

    @staticmethod
    def is_auto_generated(xpath: str) -> bool:
        """检测是否为浏览器自动生成的绝对路径风格"""
        return bool(XPathValidator._AUTO_GENERATED_PATTERN.search(xpath))


# ================================================================
# 便捷实例（推荐 import 使用）
# ================================================================

xp = XPathBuilder()
xpath_validator = XPathValidator()

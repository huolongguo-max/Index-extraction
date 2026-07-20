# RPA 抓取规则编写指南

## 核心原则

1. **禁止**使用浏览器自动生成的绝对路径 XPath（如 `/html/body/div[1]/div[3]/div[2]/...`）
2. **强制**使用手写行列文字交叉 XPath
3. 所有文字匹配统一使用 `normalize-space()` 适配隐形空格
4. 仅适配 DIV 结构网页表格

## XPath 规则模板

### 基础模板

```json
{
  "name": "规则唯一名称",
  "description": "规则用途描述",
  "url_pattern": "目标网页URL模式（支持通配符 *）",
  "table_container": "表格容器 XPath",
  "row_xpath": "行容器 XPath",
  "columns": [
    {
      "name": "列名",
      "header_xpath": "表头定位 XPath",
      "cell_xpath_template": "单元格 XPath 模板（{row_index} 和 {col_index} 为占位符）",
      "data_type": "string | number | date"
    }
  ],
  "pagination": {
    "next_button_xpath": "下一页按钮 XPath",
    "max_pages": 10
  }
}
```

### 常见场景 XPath 示例

#### 1. 通过 CSS class 定位表格容器
```
//div[contains(@class, 'table-wrapper')]
//div[contains(@class, 'data-grid')]
//section[contains(@class, 'table-container')]
```

#### 2. 通过文字定位表头列
```
//div[contains(@class, 'table-header')]//div[normalize-space(text())='姓名']
//div[contains(@class, 'table-header')]//span[normalize-space(text())='金额']
```

#### 3. 行列交叉定位单元格
```
// 第 {row} 行第 {col} 列
(//div[contains(@class, 'table-row')])[{row}]//div[contains(@class, 'table-cell')])[{col}]
```

#### 4. 翻页按钮
```
//button[normalize-space(text())='下一页']
//li[contains(@class, 'pagination-next')]/button
//a[normalize-space(text())='>']
```

## 适配 Vue 动态渲染注意事项

1. 等待元素加载完成后再抓取（`WebDriverWait` + `presence_of_element_located`）
2. 使用 `contains(@class, ...)` 而非 `@class=...`，适配 CSS Modules 编译后的哈希类名
3. 对于 v-if 条件渲染的元素，使用 `find_elements` + 判空而非直接 `find_element`

## 调试方法

1. 打开 Chrome DevTools → Elements → Ctrl+F 搜索 XPath 表达式
2. 使用 `$x('//xpath...')` 在 Console 中测试
3. 检查 `normalize-space()` 是否正确去除隐形空格
4. 确认 `contains(@class, 'xxx')` 能匹配到目标元素

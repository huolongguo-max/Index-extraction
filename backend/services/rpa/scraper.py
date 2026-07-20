"""
RPA 核心采集引擎 — 标准采集流水线（健壮版）

标准流程（全自动）：
  1. 加载目标页面
  2. 按需自动点击指定按钮
  3. 等待 Vue 动态页面渲染完成
  4. 调用 XPath 工具批量生成行列交叉表达式
  5. 提取所有指标数值（含降级重试）
  6. 清洗数据（空值/异常值统一处理）
  7. 更新本地缓存
  8. 记录运行日志

容错增强:
  - 元素匹配失败 → 自动降级重试（去 class / 换 tag / 模糊 text）
  - 页面超时 → 自动重载一次 + 浏览器重启
  - 浏览器崩溃 → 自动重启 driver，下次采集恢复正常
  - 网络异常 → 记录异常，下一轮自动重试
  - 程序不崩溃，规则之间互不影响
"""

import time
from datetime import datetime
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    InvalidSessionIdException,
    StaleElementReferenceException,
)

from backend.models.rpa_models import ScrapeRule, ScrapeResult
from backend.services.rpa.rule_manager import rule_manager
from utils.browser_utils import browser_manager
from utils.xpath_utils import xp
from utils.common_utils import clean_number, sanitize_row
from utils.storage_utils import data_store
from utils.log_utils import get_logger, RPALogger

logger = get_logger()


# ================================================================
# 采集引擎
# ================================================================

class RPAScraper:
    """
    RPA 采集引擎（健壮版）

    每条规则独立运行，执行标准采集流水线。
    内置元素降级重试、页面超时重载、浏览器崩溃恢复。
    所有异常内部消化，不影响其他规则或主程序。
    """

    # 页面加载最大重试次数
    _PAGE_RETRY_MAX = 2

    # 元素提取降级策略序列
    # 每个策略是 (描述, cell_tag, cell_class) 组合
    _EXTRACT_FALLBACKS = [
        # (描述,            cell_tag,  cell_class)
        ("默认策略",         None,      None),      # 使用规则原始配置
        ("去 class 降级",    None,      ""),         # 去掉 cell_class 限制
        ("span 标签降级",    "span",    None),       # 尝试 span 标签
        ("通用 * 标签降级",  "*",       ""),         # 最宽松匹配
    ]

    # ================================================================
    # 主入口
    # ================================================================

    def run(self, rule: ScrapeRule) -> ScrapeResult:
        """执行一条规则的完整采集流程。始终返回 ScrapeResult，不抛异常。"""
        started_at = datetime.now()
        result = ScrapeResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            target_url=rule.target_url,
            status="fail",
            started_at=started_at.isoformat(),
        )
        dbg: list[str] = []  # 调试日志

        try:
            logger.info(f"[SCRAPE:START] rule={rule.rule_name} url={rule.target_url}")

            # ---- Step 1: 加载页面（含超时重载） ----
            self._navigate_with_retry(rule.target_url)
            dbg.append(f"[页面] 加载完成: {rule.target_url}")
            try:
                title = browser_manager.get_driver().title
                dbg.append(f"[页面] 标题: {title}")
            except Exception:
                pass

            # ---- Step 2: 按需自动点击按钮 ----
            if rule.auto_click_button and rule.button_text:
                self._click_button(rule.button_text)

            # ---- Step 3: 等待 Vue 动态渲染 ----
            browser_manager.wait_for_vue_render()
            dbg.append("[页面] Vue 渲染等待完成")

            # ---- 参数诊断 ----
            params = self._effective_params(rule)
            dbg.append(f"[参数] table_type={rule.table_type}")
            dbg.append(f"[参数] row_xpath={params['row_xpath']}")
            dbg.append(f"[参数] header_row_xpath={params['header_row_xpath']}")
            dbg.append(f"[参数] cell_tag={params['cell_tag']}")
            dbg.append(f"[参数] header_cell_tag={params['header_cell_tag']}")
            dbg.append(f"[参数] cell_class={params['cell_class'] or '(无)'}")
            dbg.append(f"[参数] row_keyword={rule.row_keyword}")
            dbg.append(f"[参数] target_headers={rule.target_headers}")

            # 诊断：页面实际匹配到的行/表头数量
            driver = browser_manager.get_driver()
            try:
                row_count = len(driver.find_elements(By.XPATH, params["row_xpath"]))
                dbg.append(f"[诊断] 页面上匹配到的数据行数: {row_count}")
            except Exception as e:
                dbg.append(f"[诊断] 行匹配异常: {e}")
            try:
                hdr_count = len(driver.find_elements(By.XPATH, params["header_row_xpath"]))
                dbg.append(f"[诊断] 匹配到的表头行数: {hdr_count}")
            except Exception as e:
                dbg.append(f"[诊断] 表头匹配异常: {e}")
            try:
                hdr_texts = driver.find_elements(By.XPATH, f"{params['header_row_xpath']}//{params['header_cell_tag']}")
                texts = [el.text.strip() for el in hdr_texts[:20]]
                dbg.append(f"[诊断] 表头文字列表: {texts}")
            except Exception as e:
                dbg.append(f"[诊断] 表头提取异常: {e}")

            # ---- Step 4+5: 批量生成 XPath → 提取数据（含降级重试） ----
            extracted_rows = self._extract_with_fallback(rule, dbg)

            # ---- Step 6: 数据清洗 ----
            cleaned_rows = self._clean_data(extracted_rows)
            sanitized_rows = [sanitize_row(row) for row in cleaned_rows]

            # ---- Step 7: 更新缓存 ----
            self._update_cache(rule, sanitized_rows)

            # ---- 成功 ----
            elapsed = (datetime.now() - started_at).total_seconds()
            result.status = "ok"
            result.row_count = len(sanitized_rows)
            result.headers = rule.target_headers
            result.rows = sanitized_rows
            result.debug_log = dbg
            result.elapsed_seconds = elapsed
            result.finished_at = datetime.now().isoformat()

            RPALogger.fetch_success(
                url=rule.target_url,
                row_count=len(sanitized_rows),
                elapsed=elapsed,
                rule_name=rule.rule_name,
            )

        except PageLoadError as exc:
            result.error = str(exc)
            result.debug_log = dbg
            RPALogger.fetch_failure(rule.target_url, str(exc), rule.rule_name)
            logger.warning(f"[SCRAPE:PAGE_FAIL] rule={rule.rule_name} — {exc}")

        except BrowserCrashError as exc:
            result.error = str(exc)
            result.debug_log = dbg
            RPALogger.fetch_failure(rule.target_url, str(exc), rule.rule_name)
            logger.error(f"[SCRAPE:BROWSER_CRASH] rule={rule.rule_name} — {exc}")
            self._restart_browser()

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.debug_log = dbg
            RPALogger.fetch_failure(rule.target_url, result.error, rule.rule_name)
            logger.error(f"[SCRAPE:FAIL] rule={rule.rule_name} — {result.error}")

        finally:
            result.finished_at = datetime.now().isoformat()
            rule_manager.record_run(
                rule_id=rule.rule_id,
                status=result.status,
                row_count=result.row_count,
                error=result.error,
            )

        return result

    # ================================================================
    # Step 1: 加载页面（含超时重载 + 浏览器崩溃恢复）
    # ================================================================

    def _navigate_with_retry(self, url: str):
        """加载页面：首次失败 → 重载；浏览器崩溃 → 自动重启"""
        last_error = None

        for attempt in range(1, self._PAGE_RETRY_MAX + 1):
            try:
                browser_manager.navigate(url)
                logger.debug(f"[NAVIGATE] 加载成功: {url} (attempt {attempt})")
                return
            except (TimeoutException, WebDriverException) as exc:
                last_error = exc
                logger.warning(
                    f"[NAVIGATE] 加载失败 (attempt {attempt}/{self._PAGE_RETRY_MAX}): "
                    f"{url} — {type(exc).__name__}"
                )
                if attempt < self._PAGE_RETRY_MAX:
                    # 第 1 次失败：停止当前加载 + 等待后重试
                    try:
                        browser_manager.get_driver().execute_script("window.stop();")
                    except Exception:
                        pass
                    time.sleep(2)
                else:
                    # 最后一次失败 → 尝试重启浏览器再加载一次
                    logger.warning(f"[NAVIGATE] 尝试重启浏览器后再次加载...")
                    try:
                        browser_manager.restart()
                        browser_manager.navigate(url)
                        logger.info(f"[NAVIGATE] 浏览器重启后加载成功: {url}")
                        return
                    except Exception as retry_exc:
                        raise PageLoadError(
                            f"页面加载失败（已重试 {self._PAGE_RETRY_MAX} 次 + 重启浏览器）: "
                            f"{url} — {retry_exc}"
                        ) from retry_exc

        raise PageLoadError(
            f"页面加载失败: {url} — {type(last_error).__name__}: {last_error}"
        ) from last_error

    def _restart_browser(self):
        """尝试重启浏览器驱动"""
        try:
            browser_manager.restart()
            logger.info("[BROWSER] 浏览器已自动重启")
        except Exception as exc:
            logger.error(f"[BROWSER] 浏览器重启失败: {exc}")

    # ================================================================
    # Step 2: 自动点击按钮
    # ================================================================

    def _click_button(self, button_text: str):
        """自动点击页面上指定文字的按钮。找不到按钮时不中断流程，仅记录日志。"""
        driver = browser_manager.get_driver()
        # 多标签 + 宽松匹配
        xpath_parts = []
        for tag in ("button", "a", "span", "div"):
            xpath_parts.append(f"//{tag}[{xp.normalize(button_text)}]")
        # 额外：模糊文本匹配（contains）
        xpath_parts.append(
            f"//*[contains(text(),'{button_text}')]"
        )
        xpath = " | ".join(xpath_parts)

        try:
            elements = driver.find_elements(By.XPATH, xpath)
            clicked = False
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    el.click()
                    logger.info(f"[CLICK] 已点击按钮: '{button_text}'")
                    clicked = True
                    time.sleep(0.8)
                    break
            if not clicked:
                logger.debug(f"[CLICK] 未找到可交互的按钮: '{button_text}'")
        except Exception as exc:
            logger.debug(f"[CLICK] 点击异常（跳过）: '{button_text}' — {exc}")

    # ================================================================
    # Step 4+5: 批量提取（含降级重试）
    # ================================================================

    def _effective_params(self, rule: ScrapeRule) -> dict:
        """根据 table_type 返回 XPath 参数默认值，用户自定义值优先"""
        div_defaults = {
            "row_xpath": "//div[contains(@class, 'table-row')]",
            "header_row_xpath": "//div[contains(@class, 'table-header')]",
            "cell_tag": "div",
            "cell_class": None,
            "header_cell_tag": "div",
        }
        table_defaults = {
            "row_xpath": "//table/tbody/tr",
            "header_row_xpath": "//table/thead/tr",
            "cell_tag": "td",
            "cell_class": None,
            "header_cell_tag": "th",
        }
        defaults = table_defaults if rule.table_type == "table" else div_defaults

        # 用户填了就用用户的，没填就用当前模式的默认值
        return {
            "row_xpath": rule.row_xpath if rule.row_xpath != div_defaults["row_xpath"] and rule.row_xpath != table_defaults["row_xpath"] else defaults["row_xpath"],
            "header_row_xpath": rule.header_row_xpath if rule.header_row_xpath != div_defaults["header_row_xpath"] and rule.header_row_xpath != table_defaults["header_row_xpath"] else defaults["header_row_xpath"],
            "cell_tag": rule.cell_tag if rule.cell_tag not in ("div", "td") else defaults["cell_tag"],
            "cell_class": rule.cell_class if rule.cell_class else None,
            "header_cell_tag": defaults["header_cell_tag"],
        }

    def _extract_with_fallback(self, rule: ScrapeRule, dbg: list[str] | None = None) -> list[dict]:
        """提取数据 — 主策略失败时自动降级重试。"""
        if dbg is None:
            dbg = []
        row_data: dict = {}
        driver = browser_manager.get_driver()
        params = self._effective_params(rule)

        for header in rule.target_headers:
            extracted = False
            dbg.append(f"[提取] 开始提取 header='{header}'")

            for desc, fallback_tag, fallback_class in self._EXTRACT_FALLBACKS:
                cell_tag = fallback_tag or params["cell_tag"]
                if fallback_class is not None:
                    cell_class = fallback_class if fallback_class else None
                else:
                    cell_class = params["cell_class"]

                try:
                    cell_xpath = xp.cell(
                        row_keyword=rule.row_keyword,
                        header_text=header,
                        row_xpath=params["row_xpath"],
                        header_row_xpath=params["header_row_xpath"],
                        cell_tag=cell_tag,
                        cell_class=cell_class,
                        header_cell_tag=params["header_cell_tag"],
                    )
                    dbg.append(f"[提取] XPath({desc}): {cell_xpath[:120]}...")

                    element = driver.find_element(By.XPATH, cell_xpath)
                    raw_text = element.text.strip() if element else ""

                    if raw_text:
                        row_data[header] = raw_text
                        extracted = True
                        dbg.append(f"[提取] ✅ header='{header}' → '{raw_text}' (策略: {desc})")
                        if desc != "默认策略":
                            logger.debug(f"[EXTRACT:FALLBACK] header='{header}' 使用降级策略: {desc}")
                        break
                    else:
                        dbg.append(f"[提取] ⚠️ header='{header}' 元素存在但文本为空 (策略: {desc})")

                except NoSuchElementException:
                    dbg.append(f"[提取] ❌ header='{header}' 元素未找到 (策略: {desc})")
                    continue
                except StaleElementReferenceException:
                    dbg.append(f"[提取] ❌ header='{header}' 元素已过期 (策略: {desc})")
                    continue
                except Exception as exc:
                    dbg.append(f"[提取] ❌ header='{header}' 异常: {type(exc).__name__}: {exc} (策略: {desc})")
                    continue

            if not extracted:
                dbg.append(f"[提取] ❌❌ header='{header}' 全部 {len(self._EXTRACT_FALLBACKS)} 种策略均失败")
                logger.warning(
                    f"[XPATH:NOMATCH] rule={rule.rule_name} "
                    f"row='{rule.row_keyword}' header='{header}' "
                    f"（已尝试全部 {len(self._EXTRACT_FALLBACKS)} 种降级策略）"
                )
                RPALogger.xpath_not_found(
                    xp.cell(rule.row_keyword, header),
                    url=rule.target_url,
                )
                row_data[header] = ""

        return [row_data] if row_data else []

    # ================================================================
    # Step 6: 数据清洗
    # ================================================================

    def _clean_data(self, rows: list[dict]) -> list[dict]:
        """清洗提取数据：数字自动转换，非数字保留原文。"""
        cleaned = []
        for row in rows:
            cleaned_row = {}
            for key, raw in row.items():
                num = clean_number(raw, default=None)
                if num is not None and isinstance(num, (int, float)):
                    cleaned_row[key] = num
                else:
                    cleaned_row[key] = raw if raw else ""
            cleaned.append(cleaned_row)
        return cleaned

    # ================================================================
    # Step 7: 更新缓存
    # ================================================================

    def _update_cache(self, rule: ScrapeRule, rows: list[dict]):
        """将本次采集结果写入本地缓存"""
        cache_key = f"rule_{rule.rule_id}_latest"
        payload = {
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_url": rule.target_url,
            "headers": rule.target_headers,
            "row_count": len(rows),
            "rows": rows,
            "cached_at": datetime.now().isoformat(),
        }
        try:
            data_store.write(cache_key, payload)
            logger.debug(f"[CACHE] 已更新缓存 key={cache_key} rows={len(rows)}")
        except Exception as exc:
            logger.error(f"[CACHE] 缓存更新失败: {exc}")


# ================================================================
# 自定义异常
# ================================================================

class PageLoadError(Exception):
    """页面加载失败（可恢复）"""


class BrowserCrashError(Exception):
    """浏览器崩溃（需重启）"""


# ================================================================
# 全局单例
# ================================================================

scraper = RPAScraper()

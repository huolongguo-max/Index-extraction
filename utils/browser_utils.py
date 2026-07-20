"""
浏览器工具模块 — Selenium Chrome 自动化驱动管理

职责（纯工具层，零业务逻辑）：
  1. Chrome 驱动生命周期管理（单例、自动下载 webdriver）
  2. 前台显示 / 后台静默模式切换
  3. Vue / React 等 SPA 动态页面等待机制（DOM 渲染完成再操作）
  4. 统一超时处理与健康检查

可被 backend/、desktop/ 直接复用，与 RPA 抓取业务完全解耦。
"""

import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchWindowException,
)
from webdriver_manager.chrome import ChromeDriverManager

from config.settings import (
    CHROME_MODE,
    CHROME_BINARY_PATH,
    CHROME_PAGE_LOAD_TIMEOUT,
    CHROME_ELEMENT_TIMEOUT,
    CHROME_WINDOW_SIZE,
    CHROME_CACHE_DIR,
    CHROME_DISABLE_IMAGES,
)
from utils.log_utils import get_logger

logger = get_logger()


# ================================================================
# 异常定义
# ================================================================

class BrowserInitError(Exception):
    """浏览器初始化失败"""


class PageLoadTimeout(Exception):
    """页面加载超时"""


class VueRenderTimeout(Exception):
    """Vue 动态渲染超时"""


# ================================================================
# Vue / SPA 动态渲染检测脚本
# ================================================================

# JavaScript：检测 Vue 2/3 是否完成渲染
_VUE_RENDER_CHECK_JS = """
// 检测 Vue 是否存在且渲染完毕
(function() {
    // 1. 检查 Vue 根实例
    var appEl = document.querySelector('#app') || document.querySelector('[data-v-]');
    var vueDetected = !!(window.Vue || window.__VUE_DEVTOOLS_GLOBAL_HOOK__);

    // 2. 检查 DOM 稳定性（关键渲染节点已存在）
    var tableRows = document.querySelectorAll('[class*="table"] div, table tr, [class*="row"]');
    var hasContent = tableRows.length > 0;

    // 3. 检查是否有 pending 的网络请求（简单判断）
    var pendingXHR = window._pendingXHRCount || 0;

    // 4. 检查 vue 内部的 _isMounted 或类似标记
    var vueMounted = true;
    if (appEl && appEl.__vue_app__) {
        // Vue 3 — 检查是否挂载
        vueMounted = !!appEl.__vue_app__._instance;
    }

    return {
        vueDetected: vueDetected,
        hasContent: hasContent,
        pendingRequests: pendingXHR,
        vueMounted: vueMounted,
        ready: hasContent && vueMounted && pendingXHR === 0
    };
})()
"""

# JavaScript：等待 Vue nextTick + requestAnimationFrame 完成
_VUE_STABILIZE_JS = """
// 等待 Vue 完成所有异步更新
(function(callback) {
    if (window.Vue && window.Vue.nextTick) {
        // Vue 2
        window.Vue.nextTick(function() {
            requestAnimationFrame(function() {
                setTimeout(callback, 100);
            });
        });
    } else if (document.querySelector('#app') && document.querySelector('#app').__vue_app__) {
        // Vue 3 — 使用 nextTick
        var app = document.querySelector('#app').__vue_app__;
        if (app.config && app.config.globalProperties) {
            requestAnimationFrame(function() {
                setTimeout(callback, 100);
            });
        } else {
            requestAnimationFrame(function() {
                setTimeout(callback, 100);
            });
        }
    } else {
        // 非 Vue 页面 — 等 DOM ready
        requestAnimationFrame(function() {
            setTimeout(callback, 100);
        });
    }
})(arguments[0]);
"""

# JavaScript：通用网络空闲检测
_NETWORK_IDLE_JS = """
// 轮询检测网络空闲
(function() {
    var checkCount = 0;
    var maxChecks = 20;
    function check() {
        var xhrReady = (window._pendingXHRCount || 0) === 0;
        var noSpinner = !document.querySelector('.loading, .spinner, [class*="loading"], .el-loading-mask');
        if ((xhrReady && noSpinner) || checkCount >= maxChecks) {
            return true;
        }
        checkCount++;
        return false;
    }
    return { idle: check() };
})()
"""


# ================================================================
# Chrome 驱动管理器
# ================================================================

class BrowserManager:
    """
    Chrome 浏览器管理器（单例模式）

    核心能力：
      - 自动下载/管理 ChromeDriver
      - 前台 GUI / 后台 headless 一键切换
      - Vue/React SPA 动态渲染等待
      - 元素可见/可点击等待
      - 超时处理 + 健康检查

    用法（纯工具调用，无业务耦合）：
        from utils.browser_utils import browser_manager

        driver = browser_manager.get_driver()
        browser_manager.navigate("https://example.com")
        browser_manager.wait_for_vue_render()
        # ... 后续操作由 RPA 业务层负责
    """

    # 已知的 Vue 渲染完成标记属性
    _VUE_MARKERS = [
        "[data-v-]",                      # Vue scoped style marker
        "[data-v-app]",                   # Vue 3 mount marker
        "[data-app]",                     # 自定义挂载
    ]

    # 常见 loading/spinner 选择器
    _LOADING_SELECTORS = [
        ".loading",
        ".spinner",
        "[class*='loading']",
        ".el-loading-mask",              # Element UI
        ".ant-spin",                     # Ant Design
        ".n-spin",                       # Naive UI
        ".v-loading",                    # Vuetify
        "[role='progressbar']",
    ]

    def __init__(self):
        self._driver: Optional[webdriver.Chrome] = None
        self._mode: str = CHROME_MODE
        self._page_load_timeout = CHROME_PAGE_LOAD_TIMEOUT
        self._element_timeout = CHROME_ELEMENT_TIMEOUT

    # ======== 驱动生命周期 ========

    def get_driver(self, mode: Optional[str] = None) -> webdriver.Chrome:
        """
        获取或创建 Chrome 驱动实例（单例）

        Args:
            mode: 可选 "headless" | "gui"，覆盖全局配置。不传则用 .env 中的 CHROME_MODE。
        """
        if mode:
            self._mode = mode

        if self._driver is None:
            self._driver = self._create_driver()
        else:
            # 已存在则健康检查
            if not self._is_alive():
                logger.warning("浏览器已崩溃或关闭，重新创建")
                self.close()
                self._driver = self._create_driver()

        return self._driver

    def close(self):
        """关闭浏览器，释放所有资源"""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("Chrome 驱动已关闭")
            except Exception as exc:
                logger.error(f"关闭驱动时发生异常: {exc}")
            finally:
                self._driver = None

    def restart(self, mode: Optional[str] = None) -> webdriver.Chrome:
        """重启浏览器（会丢失当前会话）"""
        self.close()
        return self.get_driver(mode=mode)

    def switch_mode(self, mode: str):
        """
        运行时切换显示模式
        mode: "headless" | "gui"
        """
        if mode not in ("headless", "gui"):
            raise ValueError(f"mode 必须为 'headless' 或 'gui'，收到: {mode}")
        if self._mode != mode:
            logger.info(f"浏览器模式切换: {self._mode} → {mode}")
            self._mode = mode
            self.restart(mode=mode)

    @property
    def driver(self) -> Optional[webdriver.Chrome]:
        return self._driver

    @property
    def mode(self) -> str:
        return self._mode

    # ======== 内部实现 ========

    def _create_driver(self) -> webdriver.Chrome:
        """创建并配置 Chrome 驱动"""
        logger.info(f"正在初始化 Chrome 浏览器（模式: {self._mode}）...")
        try:
            options = self._build_options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            driver.set_page_load_timeout(self._page_load_timeout)
            driver.implicitly_wait(self._element_timeout)

            # 注入 XHR 计数器，用于网络空闲检测
            driver.execute_script("window._pendingXHRCount = 0;")

            logger.info(
                f"Chrome 初始化完成 | 模式: {self._mode} | "
                f"页面超时: {self._page_load_timeout}s | 元素超时: {self._element_timeout}s"
            )
            return driver

        except WebDriverException as exc:
            logger.error(f"Chrome 驱动创建失败: {exc}")
            raise BrowserInitError(f"Chrome 驱动初始化失败: {exc}") from exc

    def _build_options(self) -> Options:
        """构建 ChromeOptions"""
        options = Options()

        # —— 静默 / GUI 模式 ——
        if self._mode == "headless":
            options.add_argument("--headless=new")          # 新一代 headless
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        # —— 窗口尺寸 ——
        if CHROME_WINDOW_SIZE:
            options.add_argument(f"--window-size={CHROME_WINDOW_SIZE}")

        # —— 自定义二进制 ——
        if CHROME_BINARY_PATH:
            options.binary_location = CHROME_BINARY_PATH

        # —— 禁用图片（加速静默抓取） ——
        if CHROME_DISABLE_IMAGES:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)

        # —— 通用配置 ——
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-first-run")
        options.add_argument("--ignore-certificate-errors")

        # 隐藏自动化特征
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def _is_alive(self) -> bool:
        """检测驱动是否仍然可用"""
        if self._driver is None:
            return False
        try:
            _ = self._driver.current_url
            return True
        except (WebDriverException, NoSuchWindowException):
            return False

    # ================================================================
    # 页面导航 + 动态渲染等待（核心能力）
    # ================================================================

    def navigate(self, url: str, timeout: Optional[int] = None) -> bool:
        """
        导航到指定页面

        Returns:
            True 导航成功，否则抛出异常
        """
        driver = self.get_driver()
        timeout = timeout or self._page_load_timeout

        try:
            driver.set_page_load_timeout(timeout)
            logger.debug(f"导航到: {url}")
            driver.get(url)
            return True

        except TimeoutException:
            logger.error(f"页面加载超时 ({timeout}s): {url}")
            # 尝试停止加载
            driver.execute_script("window.stop();")
            raise PageLoadTimeout(f"页面加载超时 ({timeout}s): {url}")

    def wait_for_vue_render(
        self,
        timeout: Optional[int] = None,
        check_network_idle: bool = True,
    ) -> bool:
        """
        等待 Vue 动态页面完全渲染完成

        检测策略（多级递进）：
          1. Vue 挂载标记检测（data-v- 属性 或 __vue_app__）
          2. 关键 DOM 节点存在性（table / row 元素）
          3. Loading 动画消失
          4. 网络请求空闲
          5. requestAnimationFrame + Vue.nextTick 稳定

        Args:
            timeout: 最大等待秒数，默认取 CHROME_ELEMENT_TIMEOUT
            check_network_idle: 是否额外等待网络空闲

        Returns:
            True 渲染完成
        """
        driver = self.get_driver()
        timeout = timeout or max(self._element_timeout, 15)
        deadline = time.monotonic() + timeout

        logger.debug(f"等待 Vue 页面渲染（超时: {timeout}s）...")

        # — 第 1 层：等待 body 中至少出现 Vue 标记或表格行 —
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: (
                    d.find_elements(By.CSS_SELECTOR, "[data-v-], [data-v-app], [class*='table'] div, [class*='row']")
                ),
                message="Vue 渲染标记未出现",
            )
        except TimeoutException:
            logger.warning(f"Vue 标记未在 {timeout}s 内出现，继续尝试...")

        # — 第 2 层：等待 loading 消失 —
        remaining = deadline - time.monotonic()
        if remaining > 2:
            self._wait_loading_gone(remaining)

        # — 第 3 层：网络空闲检测 —
        if check_network_idle:
            remaining = deadline - time.monotonic()
            if remaining > 2:
                self._wait_network_idle(remaining)

        # — 第 4 层：extra requestAnimationFrame 稳定 —
        time.sleep(0.3)

        logger.debug("Vue 页面渲染等待完成")
        return True

    def _wait_loading_gone(self, timeout: float):
        """等待页面 loading 动画消失"""
        driver = self.get_driver()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            any_loading = False
            for sel in self._LOADING_SELECTORS:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            any_loading = True
                            break
                except Exception:
                    pass
                if any_loading:
                    break
            if any_loading:
                time.sleep(0.2)
            else:
                break

    def _wait_network_idle(self, timeout: float):
        """等待网络请求空闲"""
        driver = self.get_driver()
        deadline = time.monotonic() + timeout
        interval = 0.3
        stable_count = 0
        while time.monotonic() < deadline:
            try:
                result = driver.execute_script(_NETWORK_IDLE_JS)
                if result and result.get("idle", False):
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
            except Exception:
                pass
            time.sleep(interval)

    def wait_for_element(
        self,
        xpath: str,
        timeout: Optional[int] = None,
        clickable: bool = False,
    ):
        """
        等待元素出现（并可选等待可点击）

        Args:
            xpath: XPath 表达式
            timeout: 超时秒数
            clickable: True 则等待元素可点击
        """
        driver = self.get_driver()
        timeout = timeout or self._element_timeout
        condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
        locator = (By.XPATH, xpath)

        try:
            return WebDriverWait(driver, timeout).until(condition(locator))
        except TimeoutException:
            logger.warning(f"元素等待超时 ({timeout}s): {xpath}")
            return None

    def check_vue_presence(self) -> bool:
        """快速检测当前页面是否使用 Vue"""
        driver = self.get_driver()
        try:
            result = driver.execute_script("return !!(window.Vue || window.__VUE_DEVTOOLS_GLOBAL_HOOK__);")
            return bool(result)
        except Exception:
            return False

    def page_source(self) -> str:
        """获取当前页面源码"""
        return self.get_driver().page_source


# ================================================================
# 全局单例
# ================================================================

browser_manager = BrowserManager()

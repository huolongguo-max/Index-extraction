# 🪟 Apple 风格玻璃态悬浮窗

基于 **ui-ux-pro-max** 设计数据 + **Apple Human Interface Guidelines** 打造的 PyQt6 桌面悬浮窗。

## 设计来源

| 维度 | 来源 | 数据 |
|------|------|------|
| **风格** | ui-ux-pro-max `styles.csv` | Glassmorphism (#3) + Bento Box Grid (#39) + Spatial UI (VisionOS) |
| **色彩** | ui-ux-pro-max `colors.csv` + Apple HIG | Apple 系统色 + 半透明玻璃表面 token |
| **排版** | ui-ux-pro-max `typography.csv` | Inter (SF Pro 风格替代) — Spatial Clear / Minimal Swiss |
| **动效** | ui-ux-pro-max `motion.csv` | Subtle micro-interactions: 150-250ms, power1.out, ≤2px 位移 |
| **UX** | ui-ux-pro-max `ux-guidelines.csv` | 可见焦点环, 触摸友好, 键盘导航 |
| **布局** | Apple Bento Box | 模块化卡片网格, 不对称尺寸, 负空间 |

## 设计令牌 (Design Tokens)

```
AppleColors         → 系统色 + 玻璃态表面 + 文字色 + 填充色
AppleSpacing        → 8pt 间距系统 (4-32px)
AppleRadius         → 圆角系统 (6-24px)
AppleTypography     → SF Pro 风格排版 (11-34px, 5 级字重)
AppleMotion         → 动效系统 (150-500ms, Apple 弹性曲线)
AppleShadow         → 多层投影系统 (卡片 / 玻璃 / 提升)
```

## 窗口视觉特征

- 🔮 **半透明玻璃背景** — `rgba(28, 28, 30, 0.77)` + 白色描边
- 📐 **圆角 24px** — Apple visionOS 风格
- 🌑 **深色模式** — 系统级暗色 + 低亮度适配
- 🔴🟡🟢 **macOS 交通灯按钮** — 窗口左上角
- 📊 **Bento Box KPI 卡片** — 大数字 + 趋势指示
- 📋 **Apple TableView 风格** — 无网格线, 玻璃态行, 微弱悬浮高亮
- 🫧 **多层投影** — 环境阴影 + 直接阴影 + 高光描边模拟 3D 深度
- ✨ **微交互** — 鼠标悬浮窗透明度变化, 卡片浮升 (≤2px)

## 组件清单

| 组件 | 文件 | 说明 |
|------|------|------|
| `AppleFloatingWindow` | `apple_window.py` | 主玻璃态悬浮窗 |
| `AppleTitleBar` | `apple_window.py` | macOS 风格标题栏 + 拖拽 |
| `GlassCard` | `components/glass_card.py` | 半透明玻璃卡片 |
| `BentoGrid` | `components/glass_card.py` | Bento Box 网格布局 |
| `StatusDot` | `components/status_indicator.py` | 状态圆点 (呼吸动画) |
| `ConnectionBadge` | `components/status_indicator.py` | 连接状态胶囊徽章 |
| `KPIStat` | `components/status_indicator.py` | Apple Health 风格 KPI 卡片 |
| `AppleTable` | `components/data_table.py` | 玻璃态数据表 |

## 启动方式

```bash
cd Index-extraction
python -m window.main
```

## 参考

- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines)
- [ui-ux-pro-max SKILL.md](../skills/ui-ux-pro-max/SKILL.md)

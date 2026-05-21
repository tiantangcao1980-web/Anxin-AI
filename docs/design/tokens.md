# 安心智能助手 · Design Token Contract（单一来源）

> 日期：2026-05-22
> 来源：[DESIGN.md §10](../../DESIGN.md) + [产品蓝图 §2](../plans/2026-05-22-product-blueprint.md)
> 用途：跨端 token 唯一契约。当 token 漂移时，以本文件为准。

## 颜色

| 语义 | Web (HSL) | Mobile (HEX) | Desktop | MP (HEX) | UniApp (HEX) |
|---|---|---|---|---|---|
| `primary` | `25 95% 53%` | `#F97316` | 同 Web | `#F97316` | `#F97316` |
| `primary-600` | `21 90% 48%` | `#EA580C` | 同 Web | `#EA580C` | `#EA580C` |
| `im-primary` | `217 100% 55%` | `#1664FF` | 同 Web | `#1664FF` | `#1664FF` |
| `success` | `142 76% 36%` | `#16A34A` | 同 Web | `#16A34A` | `#16A34A` |
| `warning` | `38 92% 50%` | `#F59E0B` | 同 Web | `#F59E0B` | `#F59E0B` |
| `destructive` | `0 72% 51%` | `#DC2626` | 同 Web | `#DC2626` | `#DC2626` |
| `info` | `217 91% 60%` | `#3B82F6` | 同 Web | `#3B82F6` | `#3B82F6` |
| `background` | `0 0% 100%` | `#FFFFFF` | 同 Web | `#FFFFFF` | `#FFFFFF` |
| `surface-2` | `30 14% 98%` | `#FAF8F6` | 同 Web | `#FAF8F6` | `#FAF8F6` |
| `border` | `30 13% 91%` | `#E8E5E0` | 同 Web | `#E8E5E0` | `#E8E5E0` |
| `foreground` | `20 14% 10%` | `#1C1A17` | 同 Web | `#1C1A17` | `#1C1A17` |
| `muted-foreground` | `20 9% 46%` | `#7A736D` | 同 Web | `#7A736D` | `#7A736D` |
| `ai` | `262 83% 58%` | `#7C5CFF` | 同 Web | `#7C5CFF` | `#7C5CFF` |

## 圆角阶梯（飞书风 — 克制）

| 用途 | px | rpx | 备注 |
|---|---|---|---|
| 微标签 | 4 | 8 | 状态圆点附近 |
| 紧凑表格 | 6 | 12 | |
| 标准按钮 / 输入框 | 8 | 16 | 飞书标准 |
| 卡片 / 面板 | 12 | 24 | 不要 24px 大圆角 |
| 抽屉 / 弹层 | 16 | 32 | |
| 头像 / 胶囊 | 9999 | 9999 | full radius |

## 间距阶梯

```
4px → 8px → 12px → 16px → 20px → 24px → 32px → 40px → 48px
```

- 控件内：8 / 12
- 卡片内：16 / 20
- 模块间：24
- 页面块间：32

## 触控目标

- 桌面：最小 32x32（点击盒）
- 移动 / 小程序：最小 44x44（44pt iOS / 88rpx）

## 字号

| 角色 | px |
|---|---|
| Display | 40 |
| Page Title | 32 |
| Section Title | 24 |
| Panel Title | 20 |
| Lead Body | 16 |
| Body | 14 |
| Small | 13 |
| Caption | 12 |
| Micro | 11 |

## 阴影

- `shadow-card`: `0 8px 24px rgba(15,23,42,0.06)`
- `shadow-float`: `0 18px 48px rgba(15,23,42,0.12)`
- `shadow-focus`: `0 0 0 3px hsl(25 95% 53% / 0.35)`

## 各端 token 文件位置

| 端 | 文件 |
|---|---|
| Web | [`frontend/src/index.css`](../../frontend/src/index.css) + [`frontend/tailwind.config.js`](../../frontend/tailwind.config.js) |
| Desktop | 复用 Web（Tauri 加载 frontend/） |
| Mobile | [`mobile/src/theme/colors.ts`](../../mobile/src/theme/colors.ts) + [`mobile/src/constants/colors.ts`](../../mobile/src/constants/colors.ts) |
| MP | [`mini-program/src/styles/design-tokens.scss`](../../mini-program/src/styles/design-tokens.scss) + [`design-tokens.ts`](../../mini-program/src/styles/design-tokens.ts) + [`utils/theme/colors.ts`](../../mini-program/src/utils/theme/colors.ts) |
| UniApp | [`apps/uni-mobile/src/styles/tokens.ts`](../../apps/uni-mobile/src/styles/tokens.ts) + [`tokens.scss`](../../apps/uni-mobile/src/styles/tokens.scss) |

## 校验

跨端 token 漂移 CI 校验（计划在 M6 之前加入）：

```bash
# 检查残留的旧 brand 色
rg "#D4A574|#E8C9A8|#B8895A|#B8864E" --type ts --type tsx --type scss --type vue . | wc -l   # 期望 0
# 检查与 contract 偏离的硬编码
rg "text-\[#|bg-\[#" frontend/src --type tsx | wc -l   # 期望 0
```

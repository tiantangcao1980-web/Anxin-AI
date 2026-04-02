# 应用图标

## 生成步骤

1. 准备一个 **1024x1024** 的 PNG 源图（品牌 Logo，透明背景）
2. 将其放置为 `icon.png`
3. 使用 Tauri CLI 自动生成所有尺寸：

```bash
# 安装 Tauri CLI（如果尚未安装）
cargo install tauri-cli --version "^2"

# 从 1024x1024 源图生成所有平台图标
cd desktop
cargo tauri icon icons/icon.png
```

## 生成的文件清单

### 桌面端
- `32x32.png` - Windows 任务栏
- `128x128.png` - macOS / Linux
- `128x128@2x.png` - macOS Retina
- `icon.icns` - macOS 应用图标
- `icon.ico` - Windows 应用图标

### 移动端（通过 `cargo tauri icon` 自动生成到各平台目录）
- Android: `gen/android/app/src/main/res/mipmap-*` (多密度)
- iOS: `gen/apple/Assets.xcassets/AppIcon.appiconset/` (多尺寸)

## 设计规范

- 主色调：琥珀橙 `#F97316`（与 Web 端一致）
- 建议包含盾牌 + 天平元素（法律 + 安全）
- 背景色：白色或透明
- 安全区域：图标内容保持在 80% 区域内（移动端自适应图标裁切）

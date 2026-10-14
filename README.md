# JKaiMono

[English](README.en.md) | 中文

基于霞鹜文楷屏幕阅读版等宽 (LXGW WenKai Mono Screen) 与 Nerd Font 符号图标合并的 2:1 中英文等宽编程字体。

![2:1 等宽对齐演示](resources/2-1.png)

## 特性

- **西文字体**：Inconsolata（1024 单元格宽度）
- **中文字体**：霞鹜文楷屏幕阅读版等宽 (LXGW WenKai Mono Screen v1.522，46,523 字字符集，2048 单元格宽度)
- **图标扩展**：Symbols Nerd Font Mono (v3.5.1，10,594 个 2048 宽开发者图标)
- **严格等宽**：严格 1:2 中西文等宽（西文 1024 / 中文与图标 2048），专为终端与代码网格对齐优化
- **非破坏性合并**：基准字体已有的字符绝对保留，仅补充缺失的 Nerd Font 图标

## 快速构建

### 依赖安装

```bash
pip install fonttools pyyaml
```

### 构建字体

```bash
python build.py
```

生成字体保存在 `output/fonts/JKaiMono.ttf`。

## 安装与配置

### 1. 安装字体 (macOS)

```bash
cp output/fonts/JKaiMono.ttf ~/Library/Fonts/
```

### 2. 编辑器与终端设置 (VS Code / Kaku / Ghostty / WezTerm / iTerm2)

- **VS Code / VSCodium / Cursor**:
  ```json
  {
    "editor.fontFamily": "'JKaiMono', monospace",
    "editor.fontSize": 14,
    "editor.lineHeight": 1.55,
    "terminal.integrated.fontFamily": "'JKaiMono', monospace"
  }
  ```
- **终端 (Kaku / Ghostty / WezTerm / iTerm2 等)**:
  将字体族（Font Family）设置为 `JKaiMono`。

## 配置说明

修改 `config.yaml` 调整构建参数：

```yaml
font:
  family_name: "JKaiMono"
  version: "2.0"

fonts_dir: "fonts"
nerd_font: "SymbolsNerdFontMono-Regular.ttf"

styles:
  Regular:
    base_font: "LXGWWenKaiMonoScreen.ttf"
    display_name: "Regular"
    output_filename: "JKaiMono.ttf"

build:
  styles: "Regular"
  output_dir: "output/fonts"
  parallel: 1

width:
  monospace: true
  en_width: 1024
  cn_width: 2048
  visual_scale: 1.0
```

## 源字体

放置于 `fonts/` 目录：
- `LXGWWenKaiMonoScreen.ttf` (LXGW WenKai Mono Screen v1.522)
- `SymbolsNerdFontMono-Regular.ttf` (Nerd Fonts v3.5.1 Symbols Only Mono)

## 许可证

- 霞鹜文楷: SIL Open Font License 1.1
- Nerd Fonts: MIT License

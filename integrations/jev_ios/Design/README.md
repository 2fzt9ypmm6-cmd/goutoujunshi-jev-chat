# 狗头军师 iOS 图标

奶油米白底、橘棕柴犬与深棕轮廓构成统一标识。轻挑眉和短笑表达军师的机灵感，脸部轮廓融入聊天气泡。

- 原始图：`app-icon-master.png`
- 当前选用：`icon-05-shiba-cream.png`
- 生成方式：Codex 内置 imagegen
- 完整提示词：`app-icon-prompt.txt`
- 备选方案：`icon-02-minimal.png`、`icon-03-scholarly.png`、`icon-04-soft-3d.png`
- 备选提示词：`app-icon-variant-prompts.txt`
- 四款对比及 48 px 预览：`icon-options.html`
- 资源目录：`../App/Assets.xcassets/AppIcon.appiconset`
- 首页与键盘共用吉祥物资源：`../Shared/BrandAssets.xcassets/ShibaMascot.imageset`
- App 与键盘共用颜色：`../Shared/BrandTheme.swift`

整个 iOS 界面沿用同一套语义颜色：奶油背景、米白卡片、浅杏高亮、深棕主按钮与正文、橘色选中状态。深色模式对应暖棕背景与浅暖色文字。K 线用橘色和灰棕区分涨跌，并配合方向标记。

在 iOS 项目目录重新导出资源：

```sh
swift tools/make_icon.swift App/Assets.xcassets/AppIcon.appiconset
cp App/Assets.xcassets/AppIcon.appiconset/icon-60x60-3x.png Shared/BrandAssets.xcassets/ShibaMascot.imageset/shiba.png
```

导出 9 个尺寸，统一为不含透明通道的 sRGB PNG。保留完整方形底图，圆角由 iOS 应用。

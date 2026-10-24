# C 端视觉调整与背景素材

## 页面方向

参考 https://roozen.top/ 搜索缓存可见的文章分区、推荐与侧栏结构，结合本站已有的雪山、云海与企鹅女孩背景，调整首页、文章归档、文章阅读页、资源页及公共导航。参考站当时直接访问超时，未按其当前页面逐像素复刻。

## 背景

- 原 966×1629 的竖图已删除。
- 新横图 `zdblog-vue-c/public/img/hero-landscape-hd.png`：1672×941，约 16:9，桌面和手机统一使用，固定铺满视口。
- 夜景图 `zdblog-vue-c/public/img/hero-landscape-night.png`：1672×941，以当前横图为编辑输入，保留场景与人物位置，改成深蓝色夜空、月光云层、雪山和草地。使用内置 imagegen 工具生成。
- 背景读取共享 `useTheme()` 状态，亮色模式使用白天图，暗色模式使用夜景图，刷新时沿用保存的主题。雪花与固定背景保持一致。
- 新横图使用内置 imagegen 工具，以原竖图为编辑输入扩展场景；实际产物为 1672×941，并非提示词请求的 4K 分辨率，也不是原视频的逐帧修复。
- `SiteBackdrop.vue` 提供固定背景层，滚动和路由切换不移动背景。雪花使用 Canvas 绘制，限制为 30 帧；手机减少粒子数量，页面不可见时停止动画，系统减少动态效果时展示静态雪花。
- 首页和文章归档均为单列横向文章卡片；封面始终在左侧，仅显示分类、日期，标题、摘要、标签与互动信息放在右侧。`reverseCut` 交替改变中间分界的斜向，手机也保留左右结构。
- 删除推荐文章上方的介绍卡片。资源页卡片样式恢复至远端 main 的 `9a437c7` 版本。

## 图片编辑提示词

```text
Edit target: supplied original blog background illustration. Produce a very high resolution 3840x2160 landscape desktop wallpaper by extending the scenery horizontally and enhancing crisp painted details. Preserve the exact recognizable scene, palette, sunny lighting, anime illustration style, single black penguin-costume girl, her face and pose, snowy mountain, towering white cumulus clouds, green meadow and golden flowers. Compose the girl in the lower right third, snowy mountain behind her; expansive blue sky and cloud space across left/center for white blog heading. Keep the character reasonably small in the landscape. Clean detailed edges without oversharpening halos. No typography, text, watermark, logo, new characters or buildings. It should feel like the same original painting in a wide crop with restored detail.
```

## 夜景编辑提示词

```text
Use case: lighting-weather. Edit target: the supplied daytime blog wallpaper. Create a matching after-dark night version of this EXACT same illustration. Preserve identical wide composition and crop, mountain silhouette and position, cloud shapes, valleys, foreground grass and flowers, and the single penguin-costume girl's identity, face, pose, size and lower-right position. Change only the time of day and lighting: deep midnight navy and muted indigo sky, soft silver-blue moonlight along cloud edges and snowy mountain, subdued teal-blue meadow, softly visible golden flowers and a gently moonlit character. A few subtle stars may peek through existing clear sky; calm natural night atmosphere. The scene must clearly feel like night, with rich dark tones but readable painted detail, not a daytime image with a black overlay. Preserve the original anime painted style and crisp detail. Keep lighting subtle and cohesive; no new characters, buildings, lamps, large moon, text, logos, watermarks or changes to objects. Output a landscape image matching the reference aspect ratio as closely as possible.
```

# 截图素材维护

`docs/assets/screenshots/` 用于存放仓库 README、发布页和演示材料里引用的界面截图。面向公开读者的 README 只放成品图片，不放拍摄说明；拍摄约定统一维护在这份文档里。

## 📁 目录约定

- `docs/assets/screenshots/`：正式截图资源
- `docs/assets/README.md`：命名规范、补图清单、拍摄要求

## 🏷️ 命名规范

- 桌面端静态图：`workspace-overview-light.png`
- 桌面端深色图：`workspace-overview-dark.png`
- 中文版可加后缀：`workspace-overview-light-zh.png`
- 英文版可加后缀：`workspace-overview-light-en.png`
- 动图建议统一用 `webp`：`streaming-trace-light.webp`

## 📸 推荐截图清单

- `workspace-overview-light.png`
  主工作台全貌，包含侧边栏、欢迎区、输入框。
- `chat-answer-light.png`
  一轮完整知识问答结果，保留引用感较强的回答内容。
- `streaming-trace-light.png`
  流式回复和执行轨迹同屏，适合展示链路可视化。
- `system-status-light.png`
  账户与系统面板展开，展示模型配置、依赖健康度和访问地址。
- `aiops-diagnosis-light.png`
  AIOps 诊断结果页，保留步骤摘要和最终结论。
- `upload-index-light.png`
  上传知识文档后的成功提示和索引轨迹。
- `mobile-workspace-light.png`
  移动端布局，优先展示侧边栏收起后的主工作区。

## 📐 分辨率建议

- 桌面端：`1440 x 900` 或 `1600 x 1000`
- 移动端：`390 x 844`
- 动图时长：建议控制在 `4-8 秒`

## ✅ 拍摄检查项

- 隐去真实密钥、内网地址、个人邮箱和本机用户名
- 统一使用演示账号 `viewer / operator / admin`
- 保留一组稳定的知识问答和 AIOps 示例，避免每次截图内容波动过大
- 中英文版本尽量使用相同布局与相近数据量
- README 引用图片前，先确认路径写成 `./docs/assets/screenshots/<file>`

## 🔄 更新流程

1. 截图导出到 `docs/assets/screenshots/`
2. 检查文件名是否符合规范
3. 在 README 中替换为相对路径
4. 提交前在 GitHub 预览 Markdown，确认图片可正常显示

# 报告：ComfyUI 使用说明 + AI 短剧第一集提质方案

> 生成时间：2026-10-19
> 目的：① 说清 ComfyUI 怎么用（你本机已装好）；② 调研"有没有更好的工具/方案，让第一集做得更好、更有用、资产可复用"——这一块涉及编导、镜头、色彩、人物、环境、概念图等专业知识。
> 阅读对象：吴涛（自己看，可转外部顾问）

---

## 〇、先回答你三个问题

**1. "这个 MCP 装好了吗？"**
没有。我上一轮装的是 **ComfyUI 本体**（一个跑在 `E:\ComfyUI` 的本地节点编辑器应用），**不是 MCP 服务**。两者不是一回事：
- MCP 是一套"让 AI agent 能调用外部工具"的协议；ComfyUI 是生图应用本身。
- 我装的是应用，没装把 ComfyUI 暴露成 MCP 工具的桥。

**2. "agent 能直接用吗？"**
- ✅ **你**能用：双击 `E:\ComfyUI\run.bat` → 开 `http://127.0.0.1:8188` 就能用。
- ❌ **agent（我）现在还不能直接把它当工具调**——因为它没暴露成 MCP/Connector。
- 但"agent 驱动它"其实**不需要走 MCP 那么重**：ComfyUI 自带 REST API（`POST /prompt` 提交 workflow JSON 就能出图）。我写个脚本把工作流 JSON 推过去即可。真要"在对话里一键调"，再装个 ComfyUI MCP server 写进 `~/.workbuddy/mcp.json` 也行——但那是后话。
- **建议**：等第一集验收、确定要走"本地一致性精修"时再接，现在不插新工具，避免打乱执行窗口的节奏。

**3. 网络**
你开了 VPN。之前 HF 直连 502，现在应该通了 → 以后 ComfyUI 拉模型不必绕 `hf-mirror.com` 镜像（PyPI / GitHub 本来就直连可用）。

**记忆**：你说交执行窗口整理，我不碰 MEMORY.md。

---

## 一、ComfyUI 是什么 / 怎么用（使用说明）

### 1.1 定位
节点式（node-based）工作流引擎，把 Stable Diffusion / SDXL / Flux 的生图全链路（文本编码→采样→VAE 解码）做成**可视化的图**，每个环节是一个可配置节点。比 Automatic1111 那种"设置面板"更可控、更省显存（只加载用到的部分），社区自定义节点极多。

### 1.2 核心概念（你后面一定会碰到）
| 概念 | 作用 | 放哪个目录 |
|---|---|---|
| **Checkpoint** | 主模型（SD1.5 / SDXL / Flux），决定底子画风 | `models/checkpoints/` |
| **LoRA** | 小适配器（10–300MB），教模型一个新角色/风格，触发词激活 | `models/loras/` |
| **VAE** | 潜空间↔图像的解码器，一般主模型自带 | `models/vae/` |
| **ControlNet** | 用边缘/深度/姿态/参考图"注入"结构约束 | `models/controlnet/` |
| **IP-Adapter / PuLID** | 免训练从参考图提取"身份"，锁脸/锁人 | `models/ipadapter/`、`models/clip_vision/` |
| **KSampler** | 采样核心（步数/CFG/采样器/种子） | —（节点） |
| **Upscale** | 放大（RealESRGAN / SUPIR 等） | `models/upscale_models/` |

你本机现状：`checkpoints/` 已有 SDXL base；`loras/ controlnet/ vae/ upscale_models/` 等目录都建好了，后续把对应模型丢进去即可。

### 1.3 最简文生图工作流（节点连线）
```
[Load Checkpoint] → model ─┐
                           ├─→ [KSampler] → [VAE Decode] → [Save Image]
[CLIP Text Encode +] ──────┘   ↑
[CLIP Text Encode -] ──────────┘（负向）
[Empty Latent Image] → latent ─┘
```
操作步骤：右键画布加节点 → 拖线连（颜色要对：紫=model，粉=conditioning，黄=latent，橙=VAE）→ 选模型、写提示词 → `Queue Prompt`。

### 1.4 启动与界面
双击 `E:\ComfyUI\run.bat`，浏览器开 `http://127.0.0.1:8188`。默认带一个 SDXL 文生图工作流。

### 1.5 关键扩展（后面接管线必装）
- **ComfyUI-Manager**：一键装自定义节点（`custom_nodes` 里 `git clone ltdrdata/ComfyUI-Manager` 后重启）。
- 必经节点包：**Impact Pack**（含 FaceDetailer 面部精修）、**IPAdapter Plus**（身份一致性）、**ControlNet Preprocessors**（边缘/深度/姿态预处理）、**VideoHelperSuite**（视频支持）。
- 装法：Manager 里搜名字 → Install → 重启。

### 1.6 API 模式（回应"agent 能否直接用"）
ComfyUI 起服务后，`POST http://127.0.0.1:8188/prompt`，body 是 workflow 的 JSON（节点图），即可后台出图、结果落到 `output/`。这就是 agent 脚本驱动的路径，无需 MCP。

### 1.7 你本机算力边界
RTX 4060 **8GB**：跑 SDXL + 1 个 LoRA + ControlNet 单镜没问题；跑 **Flux 或本地视频（AnimateDiff/WAN/LTX）会吃紧**（需量化或降分辨率）。你已有 Agnes 视频通道，本地视频不是优先项。

---

## 二、让"第一集更好、更有用、资产可复用"的方案（核心）

这一节把搜到的专业方法论，和你项目里已经踩出来的血泪经验对上——结论是：**你的工艺原则方向是对的，行业最新方案只是在替你背书，并补了"本地一致性"这一块短板。**

### 2.1 行业共识：先定调、先出图、再出视频
多个 2025–2026 来源（Domer 实战指南、上戏 AIGC 培训、夜雨聆风实训、OpenStory 开源流水线）高度一致：

- **"AI 生成越快，越要先定调"**：定类型、风格、人物、美术、情绪，一步锁视觉基准，后续所有画面有据可依。
- **"先出图，再出视频"**（OpenStory 五步流水线精髓）：把一致性确认成本从"一段视频"降到"一张图"。图像比视频便宜、快、可控——在静态图阶段就把角色长相/场景布局/色调逐张确认，满意了再图生视频。
- 这**直接印证**了你 MEMORY 里两条原则：①"先建资产库，再组装镜头"；②"不确定性前置到图像阶段（图像 4000 张/天富余，视频 500 秒/天稀缺）"。你的直觉和 2026 年开源流水线的工程哲学一致。

### 2.2 角色一致性：ComfyUI 补 Agnes 的短板
你实测过：Agnes 的 `reference` 模式"能做到像同一类，做不到同一只"。ComfyUI 有三档递增方案：

| 档位 | 方案 | 强度 | 成本 | 适用 |
|---|---|---|---|---|
| 1 | **IP-Adapter FaceID / PuLID** | 中 | 免训练，权重 0.7–0.8（单图"LoRA"） | 阿月这种真人脸，快速锁身份 |
| 2 | **FaceDetailer** | 中 | 生成后二次精修面部、回锚特征 | 全身/远景小脸漂移的克星 |
| 3 | **训练角色 LoRA**（kohya_ss） | 强 | 用现有资产 15–30 张训，触发词激活 | 跨镜头、跨集最强一致 |

**关键提醒（搜索反复强调）**：LoRA 训练前必须有一张 **hero image**——干净、清晰、正面定妆。LoRA 会把参考图的模糊/怪表情也学进去。你已有 `real3_face_a`（主推定妆 3/4 脸）、阿月三视图 v1.1，正好作训练集与 hero。
**授权注意**：部分 FaceID 模型标注 research-only / 非商用，红果发布需注意合规——优先用可商用的 IP-Adapter Plus Face / 自训 LoRA。

### 2.3 环境 / 概念图：ControlNet + 锚点
你 MEMORY 里"环境必须有锚点图""轴线/180 度"——ControlNet 是工程落点：
- **Depth / Union ControlNet**：把主场景锚点图的空间结构喂给每一镜，避免"百叶窗左镜在左、右镜在右"的场景漂移。
- **概念图工作流前置**：先用 SDXL + 角色 LoRA 出"四大关键图"——主场景图（江岸村口雨夜）、人物图（阿月/金龙）、关键画面（斗笠漂水/金光透江）、关键道具（斗笠）——审过再进分镜。这把"概念图"从口头变成资产。

### 2.4 资产可复用体系升级（接你现有 REGISTRY）
你已有 `AST-<类型>-<序号>-<视图>_v<主>.<次>` 体系，很好。建议分两层：
- **图像锚点层**：hero 图 / 三视图 / 环境锚点 → 供 IP-Adapter / ControlNet 引用（放 `assets/` 或 ComfyUI `models/`）。
- **模型资产层**：训出来的 **阿月 LoRA、金龙 LoRA** → 放 `models/loras/`，**跨集复用**（第二集《龙虎斗》的阿月直接复用，白虎/穷奇同理）。
- **三库对应**（OpenStory 思路）：角色库（AST-CHAR）→ 场景库（AST-ENV）→ 视觉风格库（AST-STYLE）。每个镜头**引用资产而非重新想象**，这就是"资产可复用"的工程落点。

### 2.5 工具矩阵：什么时候用哪个
| 工具 | 角色 | 什么时候用 |
|---|---|---|
| **Agnes 图像/视频** | 主力（会员配额） | 草图、分镜静帧、视频（keyframe/reference） |
| **ComfyUI + SDXL/LoRA** | 本地补充 | 一致性精修、概念图、放大、面部修复 |
| **Runway Gen-4 / Kling / Seedance** | 商用视频 | 你记录的失败用 Agnes 解决不了、且值得花钱时 |
| **OpenStory（开源编排层）** | 参考架构 | 想做"剧本直出成片"的自建流水线时研究 |

**决策纪律（Domer 强调，与你一致）**：别为"新"加工具，只为"记录的失败"加工具。你记录的失败——角色漂移、场景漂移、色彩跳戏、叙事接不上——ComfyUI 的 LoRA + ControlNet + 风格库正好对症。盲目上订阅反而打乱节奏、烧钱。

### 2.6 落地建议（不急，等第一集验收后）
1. **第一集**：先让执行窗口用 Agnes 跑完、验收。不插入新工具。
2. **验收后 / 第二集前**：用现有资产训 **阿月 LoRA + 金龙 LoRA**；建 ControlNet 环境锚点；概念图前置。
3. 把 `AST-STYLE-001` 的亮度/色温/饱和度规范，做成 ComfyUI 可加载的 **LUT 或统一 prompt 模板**，全片视觉 DNA 固化。

---

## 三、涉及的专业知识清单（你关心的编导/镜头/色彩/人物/环境/概念图）

### 3.1 编导 / 叙事（你 MEMORY 已有，汇总成可查表）
- 连续性剪辑：建立镜头 → 视线匹配（她看→她看到的）→ 反应。
- 180° 法则 / 动作轴线：机位始终同侧，左右关系不乱。
- 库里肖夫效应：情绪在两镜之间，不在单镜内（先给脸再给龙=生成恐惧；先给龙再给脸=解释）。
- J-cut：下一镜声音提前 0.5s 进。硬切 vs 溶解：动作段硬切，时空跳跃才溶解。
- 首尾帧衔接：上一镜末帧作下一镜首帧（同空间连续动作）；大动作（奔跑/打斗）易形变，改用重拍+剪辑掩盖。

### 3.2 镜头语言
- 景别：远 / 全 / 中 / 近 / 特写。
- 角度：平 / 俯 / 仰 / 过肩。
- 焦段感：广角贴近、标准、长焦压缩背景。
- 景深：浅景深突出人物，深景深交代环境。
- 运镜：推 / 拉 / 摇 / 移 / 跟 / 升 / 降（crane up through surface 最出"它多大/她多小"）。

### 3.3 色彩
- 全片定**一条**规则（如现实线冷灰、回忆线暖黄；昼低饱和、夜可高 20%）。规则越简单越一致。
- 分镜表加**"光位"列**：每场戏固定主光方向 + 色温倾向，写进提示词（"主光来自画面左后，暖色轮廓光，背景压暗"）。
- 后期：**保对比不保均值**（你实测血泪）：S 曲线压深黑提高光，再二次 gamma 校正；判断标准用 p5/p95/动态范围，不是均值。可走 LUT/ACES。

### 3.4 人物
- 三视图/四视图标准化（正面/侧面/45°），锁定作视觉资产。
- 角色设定表写到"别人能照着画"：年龄、脸型、发型发色、瞳色、肤色、身高体态、常服、标志性配饰、默认表情。
- 参考图 **2–4 张**高质量即可；越多越杂反而漂移。

### 3.5 环境
- 主场景图锚点 + 道具叙事功能（斗笠=爹/死亡/钩子）。
- 空间结构锁定：ControlNet Depth 把锚点空间喂给每镜，防布局漂移。

### 3.6 概念图
- 四大关键图：主场景、人物、关键画面、关键道具。
- 从大到小迭代：先定方向 → 锁版本 → 精细化 → 补特写；用画板统一风格。

---

## 四、给你的决策点（本线下一步）

要不要我接着做这几件（都不急，等第一集出来再说）：
1. **装 ComfyUI-Manager + 关键节点包**（Impact Pack / IPAdapter Plus / ControlNet Preprocessors），把本地一致性能力就位；
2. **写一份 SDXL 基础文生图 / 图生图 workflow JSON** 放进 `E:\ComfyUI`，你打开就能用、也能当 agent 驱动的模板；
3. 第一集验收后，出 **《阿月/金龙 LoRA 训练方案》**（用现有资产筛选 hero + 训练参数 + 合规说明）。

**本线当前聚焦**：等执行窗口第一集产出，用本报告第二节的一致性方法论 + 第三节的专业知识，作为评审标尺——看它"像不像一部作品"，而不是只看"单镜漂不漂亮"。

---

## 参考来源（可自己深读）
- ComfyUI 入门/节点/工作流：myaitutorial.com、willitrunai.com、apatero.com（Ultimate Guide 2025）
- ComfyUI 角色一致性（IP-Adapter/PuLID/FaceDetailer/LoRA）：apatero.com influencer 教程、iimagined.ai consistent-character、flick.art 中文指南
- AI 短剧制作全流程/一致性/镜头语言：domer.io（电影感短片实战指南、短视频工作流全指南）、hiyascott.github.io（AI短剧制作）、上戏 AIGC 培训复盘（xxgk.sta.edu.cn）
- 开源短剧流水线 OpenStory（剧本直出成片、资产库、先出图再出视频）：微信公众号文章 / GitHub `openstory-so/openstory`
- 商用视频工具对比（Runway/Kling/Seedance/Vidu）：hubpy.io、invideo.io、reelmind.ai
- 实训心得（角色三视图、长镜头拆短镜、前3秒钩子）：e.yeyulingfeng.com

# Agnes API 接入实测手册

> 实测日期：2026-10-18　环境：Windows 本机 + curl
> 账号：专业版会员（国内站）
> 结论：**文本 / 图像 / 视频 三条通道全部打通。**

---

## 一、凭证与端点

| 项 | 值 |
|---|---|
| Base URL | `https://api.agnes-ai.cn/v1` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| Key 后台 | `https://platform.agnes-ai.cn/settings/apiKeys` |

**⚠️ 国内站 / 国际站账号与 key 不通用。**
- 国际站：`https://apihub.agnes-ai.com/v1`（后台 `platform.agnes-ai.com`）
- 国内站：`https://api.agnes-ai.cn/v1`（后台 `platform.agnes-ai.cn`）
- `apihub.agnes-ai.cn` 这个域名**不可用**（一律 401）

实测：同一个 key 在 `.cn` 返回 200，在 `.com` 返回 401，反之亦然。**端点必须与 key 的归属站一致。**

### 鉴权失败信号对照（排障用）

| 返回 | 含义 |
|---|---|
| `无效的令牌` / `Invalid token` | key 无效、已吊销、或跨站使用 |
| `未提供令牌` / `Token not provided` | 请求头没带上 |

**陷阱**：`/models` 端点的鉴权校验与业务端点**不是同一套**。曾遇到旧 key 在 `/models` 返回 200（有 10 个模型），但所有业务端点全 401 —— 这是陈旧缓存层造成的假阳性。**判断 key 是否可用，必须打业务端点，不能只看 `/models`。**

---

## 二、可用模型（`GET /v1/models` 实测返回）

```
agnes-3.0-flash          # 文本主力，Agent/长任务导向
agnes-3.0-pro            # 文本增强
agnes-2.5-flash          # 文本，纯问答/代码更快
agnes-2.5-pro-alpha
agnes-2.5-pro-beta
agnes-image-2.5-flash    # 图像主力
agnes-image-2.1-flash
agnes-image-2.0-flash
agnes-video-2.5-flash    # 视频主力（快）
agnes-video-2.5          # 视频（付费档）
```

---

## 三、文本：`POST /v1/chat/completions`

OpenAI 兼容，直接可用。

```json
{
  "model": "agnes-3.0-flash",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 80
}
```

**实测**：一句问答 87 prompt + 17 completion tokens，耗时 6.7 秒。

另有 `/v1/responses`（OpenAI Responses）与 `/v1/messages`（Anthropic 协议）两个端点。

---

## 四、图像：`POST /v1/images/generations`

```json
{
  "model": "agnes-image-2.5-flash",
  "prompt": "电影感中景镜头，...",
  "size": "1K",
  "ratio": "16:9",
  "extra_body": {"response_format": "url"}
}
```

| 参数 | 取值 |
|---|---|
| `size` | `1K` / `2K` / `3K` / `4K` |
| `ratio` | `1:1` `3:4` `4:3` `16:9` `9:16` `2:3` `3:2` `21:9` |

**三个必须记住的坑**：

1. **`response_format` 必须放 `extra_body` 内** —— 放顶层静默失效，返回里 `url` 为空。官方重点标注。
2. **请求的尺寸不等于实际输出尺寸**。实测 `1K` + `16:9` → **1312×704 的 736**（1312×736，比例 1.783）。要标准 1080p 素材必须下游裁剪。
3. **文生图与图生图共用同一端点**（没有 `/images/edits`）。图生图把输入图放 `extra_body.image`，支持公网 HTTPS URL 或 `data:image/png;base64,...`，可传数组做多图合成。

**返回**：`data[0].url` 指向 `cos-platform-outputs.agnes-ai.cn` 下的 PNG，另有 `task_id`。
**实测**：1312×736，1.09 MB，耗时 8.9 秒。

---

## 五、视频：`POST /v1/videos`（异步两步）

### 5.1 三种 mode —— 这是短剧的核心设计点

| mode | 用途 | 必填媒体 | 禁止字段 |
|---|---|---|---|
| `text` | 纯文生视频 | 无 | 所有媒体字段 |
| **`keyframe`** | **首帧/尾帧控制** | `first_frame` 或 `last_frame`（至少一个） | `images` `audios` `videos` |
| `reference` | 图片/音频参考 | `images`(≤5) 或 `audios`(≤3) | `first_frame` `last_frame` `videos` |

**对 AI 短剧：`keyframe` 是主力模式。** 先用图像模型把每一镜的构图、角色形象、光线锁定（图像配额 4000 张/天，随便试），再用 keyframe 把它"推"成动态 —— 这是弱模型条件下控制角色一致性的唯一可靠手段。纯 `text` 模式下同一个角色十条片子十个长相。

### 5.2 请求参数

```json
{
  "model": "agnes-video-2.5-flash",
  "mode": "keyframe",
  "prompt": "画面中的人物缓缓抬起头，眼神移向镜头，雨丝缓慢飘落，镜头极缓慢推进",
  "first_frame": "https://.../frame.png",
  "seconds": "4",
  "size": "720P",
  "aspect_ratio": "16:9",
  "n": 1
}
```

| 参数 | 说明 |
|---|---|
| `seconds` | **字符串**，`"4"`–`"12"`，默认 `"5"` |
| `size` | **只能 `"720P"`**，其他值直接 400 |
| `aspect_ratio` | `21:9` `16:9` `4:3` `1:1` `3:4` `9:16` |
| `n` | 只能 `1`，不支持一次多出 |
| `seed` | 可选，整数 |

Flash 专属限制：`images` ≤ 5 张、`audios` ≤ 3 段、不支持参考视频（传 `videos` 直接 400）。
**这些校验在排队和计费之前执行，非法请求不扣配额。**

### 5.3 轮询

```
GET https://api.agnes-ai.cn/agnesapi?video_id=<ID>&model_name=agnes-video-2.5-flash
```

- 创建响应的 `id` / `task_id` / `video_id` **三者同值**，取哪个都行
- `keyframe` / `reference` 模式**必须带 `model_name`**，只有 `text` 模式可以省略
- 建议 1–3 秒轮询一次
- 状态流转：`pending` → `in_progress` → `completed` / `failed`

**⚠️ 文档与实现不一致**：文档说从 `metadata.url` 取视频地址，实测**顶层 `url` 字段**才是真的。
```
{"status":"completed","progress":100,
 "url":"https://cos-platform-outputs.agnes-ai.cn/videos/agnes-video-2.5/task_xxx.mp4",
 "usage":{"input_seconds":0,"input_image_count":1,"input_audio_seconds":0}}
```

**⚠️ 轮询有抖动**：约每 5 次会有 1 次返回体缺 `status` 字段（解析为 None）。**轮询逻辑必须容忍空响应，不能当成 failed。**

### 5.4 实测数据（4 秒 keyframe）

| 指标 | 实测值 |
|---|---|
| 生成耗时 | **86 秒**（4 秒视频） |
| 输出分辨率 | **1280×704**（非文档说的 1280×720） |
| 实际时长 | 4.48 秒（请求 4 秒） |
| 文件大小 | 740 KB |
| 视频编码 | H.264 (`avc1`)，107 帧 |
| **音频** | **AAC (`mp4a`)，141 样本，69.6 KB，32 kHz ≈ 124 kbps —— 真实音轨，非空轨** |

**这个音频发现很重要**：Agnes Video 2.5 是**音视频同步生成**的，输出自带环境音/音效层。短剧流水线不用再单独配音效，可以直接进剪辑。但同时也意味着**要验证它对"人物对白"的处理能力** —— 是否会生成人声、是否与画面口型对得上，这一项尚未测。

---

## 六、配额约束与工程含义（专业版）

| 资源 | 额度 | 短剧视角的含义 |
|---|---|---|
| 文本 `agnes-3.0-flash` | 7,500 次/5h，75,000 次/周 | 极充裕，剧本/分镜/改稿随便跑 |
| 图像 `agnes-image-2.5-flash` | 4,000 张/天 | 充裕，**专门用来"试错"视觉方案**，别心疼 |
| **视频 `agnes-video-2.5-flash`** | **500 秒/天** | **唯一硬瓶颈：8.3 分钟素材量** |

### 算一笔账

- 一集 60 秒微短剧 = 6 段 10 秒，或 15 段 4 秒
- 500 秒 ÷ 60 秒 = **理论 8 集/天**；按 50% 废片率算，**实际 4 集/天**
- 关键推论：**视频配额是"成片秒数"级稀缺资源，但图像配额是"试验"级富余资源。**

→ 因此流水线的设计原则应当是：
**把不确定性全部前置到图像阶段消化掉**（构图、角色、光线、景别、情绪全靠图像反复试），
**视频阶段只做"已经确定的画面"的确定性放大**，而不是在视频阶段试错。

### 耗时约束（容易被忽略）

4 秒视频耗时 86 秒，约 **21 倍实时**。一集 60 秒成片串行生成 ≈ 22 分钟。
→ 短剧要规模化，**必须并发提交任务**（而非串行等待）。并发度受 RPM 限制，RPM 具体数值需再测。

---

## 七、已知坑汇总（血泪版）

1. `response_format` 放顶层 → 静默失效
2. 只看 `/models` 200 就以为 key 有效 → 实际业务端点可能全 401
3. 国内站 key 打到国际站端点 → 401，反之亦然
4. `apihub.agnes-ai.cn` 这个域名 → 一律 401，不存在
5. `size` 传 `1280x720` / `1080p` 之类 → 400，只认 `720P`
6. `seconds` 传数字 `4` 而非字符串 `"4"` → 400
7. `mode` 传 `text2video` / `t2v` → 400，只认 `text` / `keyframe` / `reference`
8. 从 `metadata.url` 取视频地址 → 取不到，实际在顶层 `url`
9. 轮询把空响应当失败 → 误判，必须容忍
10. 请求 `16:9` 得到 1280×704 → 拼片前要统一裁剪或补边

---

## 八、待验证清单

- [ ] 视频对**人物对白**的处理：能否生成人声？口型是否对得上？
- [ ] 单任务最长 `12` 秒的生成耗时与配额扣减规则（按输出秒还是按请求秒）
- [ ] 具体 RPM 上限（并发提交的压力测试）
- [ ] 图生图（`extra_body.image`）在角色一致性上的实际效果
- [ ] `reference` 模式（≤5 张参考图）与 `keyframe` 模式在角色一致性上的效果对比
- [ ] 尾帧控制（`last_frame`）做转场/运镜过渡的可行性

---

## 九、本次实测产物

| 文件 | 说明 |
|---|---|
| `probe/models.json` | 模型清单原始返回 |
| `probe/img_resp.json` | 图像生成原始返回 |
| `probe/test_frame.png` | 实测生成的分镜帧 1312×736 |
| `probe/vid_create.txt` | 视频任务创建返回 |
| `probe/vid_result.json` | 视频任务终态返回 |
| `probe/test_clip.mp4` | 实测视频 1280×704 / 4.48s / 带 AAC 音轨 |

GPT Image 2.6 动图制作教程：提示词、工具与排错
用 ChatGPT、Image 2.6 API 或精灵图制作 GIF，查看 Ofox 真实生成结果，复制提示词，选择 GitHub 工具，并检查循环、压缩和导出。

gpt-image
image-generation
api-guide
Ofox
13 分钟阅读
西洋镜的环形画带上重复出现一只橙色小鸟的动作
用 GPT Image 2.6 制作 GIF，先选路径：让 ChatGPT 交付可下载动图，通过 Images API 请求原生 GIF，或先生成精灵图，再把各帧合成动画。 三条路径的控制方式不同。六格图片本身不是 GIF；代码工具合成了 GIF，也不能证明底层模型直接输出了动画。

本教程覆盖三条路径、可复用提示词、相关 GitHub 项目、文件检查和压缩导出。先用一个主体、一个可逆的小动作和固定镜头开始。首个交付目标是确实会动、能正确循环的文件，而不只是对话中显示“成功”。

证据与可用性，核查于 2026 年 11 月 5 日：我们通过 Ofox 的 Image 2.6 Flare API 生成了一份原生 GIF，核对了九帧、时长与文件大小；另外用一张公开许可的第三方精灵图测试了浏览器转换与本地导出。下文均提供结果下载。Image 2.6 也已可在 Ofox Chat 使用。本文的生成测量来自 API，并非 Chat 界面实测；另外六组提示词尚未经过模型验证。代码和原始提示词保留英文，方便与下载包及实测请求对应。

选择 ChatGPT、API 或精灵图路径
OpenAI 的 Images 2.6 发布文章介绍了产品中的 GIF 创作，并展示角色、表情反应和工作助手动画。模型文档列出了 API 模型。仅凭公告不能确定你当前账号界面中有哪些具体控件。

路径	适合的起点	可控制内容	必须核对
ChatGPT	不写 API 代码，制作简单表情或吉祥物动画	任务、动作与修改要求	是否交付可下载动图；当前会话可用的操作
原生 Images API	需要可重复请求并记录参数	模型、受支持的 GIF 设置、请求日志	API 权限、实际帧时长、返回用量
精灵图 → GIF	能生成静态分镜网格，但需要确定的合成过程	网格、帧顺序、间隔、调色板与输出尺寸	等大单元格、主体对齐、动作连贯
使用照片或参考图时要格外注意：某个界面允许上传图片，不代表所有端点或封装工具都会传递图片。下文审查的一个仓库中，--image 用于 Codex 路径，而 API 路径只构造文字提示。不能因为命令执行成功，就认定吉祥物或商品照片已传给模型。

如果任务需要较长的商品故事、多个镜头或声音，请使用商品短视频分镜流程。短 GIF 是另一种交付物。

在 ChatGPT 中制作第一份 GIF
在具备图片创作能力的账号中打开对话。若有自己拥有使用权的角色或商品图，先上传，并说明哪些特征必须保持；否则从文字描述的简单角色开始。不必猜测按钮名称，也不要假设每个应用版本都有相同的 GIF 编辑器。

可先复制这段原创提示词：

Create a downloadable animated GIF of a small orange bird standing on a
branch against a plain cream background. The bird lifts both wings,
briefly holds the pose, then lowers them to the starting position.
Keep the camera, branch, body proportions and colors fixed. Use one
continuous reversible action. No text, extra objects or camera cuts.
Deliver the animated GIF file, not a still image or a grid of frames.
复制
你也可以在 Ofox Chat 中尝试这段小鸟提示词。明确要求使用 Image 2.6，交付可下载的动态 GIF。链接只打开 Chat，需要自己把提示词复制到对话中。

收到结果后，打开文件，观看多个循环。如果只得到静态图，可以追问一次：“是否附有动画文件？请提供 GIF 下载；如果当前会话无法生成，请直接说明。”这是澄清输出，不是保证能解锁未开放功能的方法。

若文件会动但效果不对，每次指出一个看得见的问题，例如“场景不变，把翅膀动作放慢”，或“第三个姿态中鸟的形状变了，请保持原来的轮廓”。每次修改后都重新看完整循环；修好某一帧也可能让相邻帧不匹配。

若收到精灵图，按下文转换。若会话不支持动画文件，换用可用的 API 或其他工具，不要反复要求同一个不受支持的操作。不要根据助手自述推断底层模型；保存原文件及可见的生成上下文，文件名中带“2.6”并不是模型证据。

从照片开始时
让动作足够小，原图才能继续提供有效参考。眨眼、轻轻点头或商品小幅倾斜，比露出未见过表面的完整转身更容易验收。明确固定项：脸形、衣服、标签、光线与背景；要求目标文件，再逐帧检查这些细节。

这是建议的提示方式，不表示我们已在 ChatGPT 中实测照片转 GIF。不要把下面的 API 限制直接套用到 ChatGPT 界面，也不要认为 ChatGPT 订阅包含 API 额度。

用动作与固定项组织提示词
官方提示词指南提供了角色回到起始姿态、镜头保持不动的循环示例。关键是同时描述“什么变化”和“什么保持不变”；只写画风不等于定义动画。

可复用结构包含六部分：输出格式、主体、动作路径、固定项、画风与验收要求。

OUTPUT: a downloadable animated GIF, or a single sprite sheet for assembly
SUBJECT: one clearly described character/object and its visual identity
MOTION: starting pose → small action → return toward the starting pose
INVARIANTS: camera, background, scale, colors and details that must not change
STYLE: one coherent material/rendering style and lighting setup
ACCEPTANCE: visible motion, no unwanted cuts, no extra text, a clean loop
复制
不要在同一请求中同时指定两种输出。原生 GIF 路径要求动画；精灵图路径明确网格。如果同时写“三列两行精灵图”和“GIF”，模型生成静态网格也可能符合指令。

六组可改写的原创提示词
以下模板由 Ofox 编写，不是复制的社区提示词，也不是已经验证的 Image 2.6 结果。替换主体和品牌细节，保持动作简单，并检查各自的失败风险。

1. 挥手吉祥物：检查轮廓与配饰。

Create a looping animated GIF of an original rounded orange fox mascot,
wearing a small blue scarf, on a plain off-white background. Start with
both paws down. Raise one paw, make one small wave, then lower it back.
Keep the ears, muzzle, scarf, scale and camera unchanged in every frame.
Use flat illustrated shapes and consistent soft lighting. No text or
new props. Return smoothly toward the starting pose. Deliver a GIF file.
复制
2. 商品展示：检查标签，而不只是动作。

Using the attached product image where this interface supports references,
create a looping GIF with a small left-to-right tilt and return to rest.
Keep the product shape, approved label text, colors, lighting and background
unchanged. Fixed camera, no full rotation, no new packaging or reflections
that obscure the label. Deliver the animated file. If the reference cannot
be used in this route, say so instead of inventing a replacement product.
复制
3. 表情角色：缩小后仍应看得懂情绪。

Create a looping GIF of an original round robot receiving good news.
It starts neutral, opens its eyes slightly wider, lifts both short arms
in a small celebration, then returns to neutral. Fixed front camera,
plain pale-blue background, same face and body proportions throughout.
Use simple high-contrast shapes. No captions, numbers or extra characters.
Deliver a GIF whose expression remains readable as a small reaction image.
复制
4. 输入状态指示：只移动局部，不让整个界面变化。

Create a short looping GIF of three small orange dots on a cream background.
One dot rises slightly, then the next, then the third, with each returning
to the same baseline before the cycle repeats. Keep dot size, spacing,
color and camera fixed. No glow, text, shadow changes or additional dots.
Use clean flat shapes and a calm rhythm. Deliver the GIF file.
复制
5. 轻微运动的插画：把运动限定在一个元素。

Create a looping GIF of an illustrated mug on a wooden desk. Only one thin
curl of steam moves upward and reforms gently; the mug, handle, desk,
window light and camera stay still. Warm muted colors, simple ink lines,
no lettering, hands or added objects. Avoid a visible reset at the loop
boundary. Deliver an animated GIF, not a video or a sprite sheet.
复制
6. 六帧精灵图：明确后续合成所需输入。

Create one still sprite sheet of an original small orange bird raising
and lowering its wings. Exactly six equal cells in three columns and two
rows, read left-to-right then top-to-bottom. Start at rest, raise the
wings, reach the high pose, lower them, and approach rest again. Same bird,
branch, scale, framing and plain cream background in all cells. Leave
safe space around the wings. No borders, gutters, captions or cell labels.
Use flat illustration. This output is a sprite sheet for later GIF assembly.
复制
第四组也提醒我们：严格几何形状的加载指示器，用确定性的动画代码可能比反复生成更易维护。在插画本身能贡献价值时使用模型。营销文字应尽量放在动态画面之外，否则逐帧检查可读性；图片文字处理流程讨论的是另一部分任务。

通过 API 生成原生 GIF
需要具备权限和计费的 API 账号、Python 3 与 curl。下面的 OpenAI 直连示例依据官方文档；我们的真实生成使用后面的 Ofox 兼容路径。Images API 指南说明了生成端点的 GIF 输出。

下载并解压 GIF 工作流包，在终端安全设置 OPENAI_API_KEY。不要把密钥粘到提示词或请求 JSON 中。包内 gif-request.json 使用以下小鸟提示词与设置：

{
  "model": "gpt-image-2.6-flare",
  "prompt": "Create a looping animation of a small orange bird on a stationary branch against a plain cream background. The bird raises its wings, pauses, then lowers them to its starting pose. Keep the camera fixed, the branch still, and the bird shape and colors consistent. No text. Make the transition back to the start smooth.",
  "quality": "low",
  "complexity": "low",
  "size": "auto",
  "n": 1,
  "output_format": "gif",
  "frame_count": 9,
  "frame_duration_ms": 200
}
复制
curl --fail-with-body --max-time 240 \
  https://api.openai.com/v1/images/generations \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @gif-request.json \
  --output gif-response.json

# Run only after a successful API response:
python3 decode_image.py gif-response.json bird.gif
复制
解码脚本验证 base64 和 GIF 文件签名，拒绝覆盖已有文件，并在响应包含用量时打印用量。curl 失败后应先查看错误响应。超时不代表服务器没有完成工作；付费重试前核对账号或请求活动。

设置	文档规定的行为
frame_count	2–64，默认 9
frame_duration_ms	20–2000 毫秒，按 10 毫秒舍入，默认 200
size	auto 或受支持、可被 16 整除的尺寸，同时受总像素预算约束
GIF 不支持的选项	流式输出、部分图像、输出压缩和 prompt_rewriter
图片编辑端点	不输出 GIF
九帧、每帧 200 毫秒，要求的是 1.8 秒播放周期，不是 1.8 秒生成时间。尺寸、帧数和输出数量必须满足像素预算，只有“可被 16 整除”还不够。请求被拒绝时降低负载；延长帧间隔只改变播放速度，不减少请求的图片像素。

选择 Flare 或 Sunburst 应依据具体任务，而不是保证某一个总能生成更好的循环。把请求和用量随结果保存。Image 2.6 价格指南解释了为什么静态图估算不能当通用 GIF 价格。下文只有单次请求用量，并非统一报价或已对账发票。

Ofox API 的真实生成结果
刷新后的公开目录和账号模型列表均出现 openai/gpt-image-2.6-flare 与 openai/gpt-image-2.6-sunburst。我们只测试了 一次 Flare：小鸟提示词和设置与上面相同，模型改为 openai/gpt-image-2.6-flare。GIF 支持的证据不是“目录里有模型”，而是请求真正返回了 GIF。

安全设置自己的 OFOX_API_KEY，使用包内 ofox-request.json。检查脚本需要 Pillow；尚未安装时先建立虚拟环境并安装：

curl --fail-with-body --max-time 240 \
  https://api.ofox.io/v1/images/generations \
  -H "Authorization: Bearer $OFOX_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @ofox-request.json \
  --output ofox-response.json

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install Pillow
python3 decode_image.py ofox-response.json ofox-bird.gif
python3 inspect_gif.py ofox-bird.gif
复制
通过 Ofox 使用 GPT Image 2.6 Flare 生成的九帧橙色小鸟动图

下载原生 GIF及不含凭据的请求文件。这是生成插画，不是产品界面截图。

观察项	本次请求
返回文件	GIF，512 × 512 像素，677,030 字节
动画	九帧，每帧 200 毫秒，一个周期 1,800 毫秒
循环元数据	0，表示无限重复
客户端测得请求时间	14.426 秒，包含网络时间
返回用量	92 个输入文本 token，1,172 个输出图像 token
小鸟抬起并放下翅膀，首尾姿态接近。但即使要求树枝固定，枝条和叶片仍有轻微变化。结果可用于简短插画，却不能算背景完全锁定。品牌标识或精确商品动画应逐帧对比，拒绝不需要的形状变化。一次 Flare 成功不代表 Sunburst 的表现、典型延迟或所有账号的权限。响应中的用量也不等于独立核对过的扣费。

更喜欢通过对话创作？带上小鸟提示词，在 Ofox Chat 中要求生成 Image 2.6 GIF，说明主体、动作与固定细节，再下载检查循环。上面的例子说明，即便文件帧数正确，视觉验收仍不可少。


试试更轻松的工作方式

在 Chat 中开始
把精灵图转成 GIF：经过验证的示例
精灵图是一张包含有序动画单元格的静态图片。必须切出正确单元格、按顺序播放并编码时长。当工具只能输出 PNG、没有原生 GIF 控制时，这是可行的替代路径。

本例使用 jkf87/gif-maker-skill 指定版本中的公开 cat_sheet.png。作者把它标为 Codex 精灵图路径示例。原画属于仓库作者；Ofox 完成转换、下载与文件检查。我们没有独立确认原画背后的模型。分发结果附有 MIT 许可说明。

浏览器转换：无需本地代码
打开 Sprite Sheet to GIF Converter并加载图片。本次实际操作如下：

Number of rows 填 2，Number of columns 填 3。
Frame delay (ms) 填 180。
原图没有间隙且单元格等大，偏移量保持 0。
点击 Generate GIF，检查切出的帧，再点 Download GIF。
单独检查下载文件。预览会动，不代表导出保留了正确时长。
转换器实际设置：两行三列，每帧间隔 180 毫秒

真实浏览器截图，保留英文界面，裁剪到参数与精灵图预览区域；这不是 Image 2.6 产品界面。

Ofox 使用 jkf87 公开许可的猫咪精灵图合成的 GIF

第三方原画、Ofox 验证合成。下载结果与许可说明。它不是 Ofox 模型生成样本。

导出文件为 512 × 512 像素、六帧、每帧 180 毫秒、周期 1,080 毫秒、920,053 字节。循环扩展值为 0，按解码器约定表示无限循环。数字验证的是结构和时长，不保证角色完全一致或首尾无缝。测试时网站有广告，请区分导出控件和广告。

如果网格切到脸或翅膀，先检查行列是否颠倒、边框、间隙和不等大单元格。不要把生成错位的主体硬当成对齐的帧。工具中的 3×2 应明确是三列、两行。

本地转换：用 Pillow 重现合成
工作流包还提供 sheet_to_gif.py。它接收无间隙、可等分的静态精灵图，按阅读顺序处理单元格并使用统一调色板，输出白底不透明 GIF，不保留透明背景，也不调用模型或网络。

python3 -m venv .venv
source .venv/bin/activate
python -m pip install Pillow

python3 sheet_to_gif.py sheet.png local-loop.gif \
  --cols 3 --rows 2 --ms 180 --width 512
python3 inspect_gif.py local-loop.gif
复制
Windows 使用 .venv\Scripts\Activate.ps1 激活环境。从固定版本仓库获取原示例，或使用自己的图片，命名为 sheet.png。输出文件名应未被占用。脚本拒绝无法等分的网格和不合适的时长，不会修好错位主体，也不会补出缺失动作。

对同一原图，本地转换器得到六帧 512 × 512、周期 1.08 秒、656,867 字节的 GIF。这只是该输入和编码方法的结果，不是普遍画质或压缩优势。编码器可能合并连续相同帧，所以帧数和总时长都要核对。

交付前先检查结果
原生输出和合成文件都可用以下命令检查：

python3 inspect_gif.py bird.gif
复制
脚本报告尺寸、帧数、每帧间隔、总时长与循环信息，并提供首尾帧 RGB 差异作为诊断。这个差值不是质量评分。首尾相似仍可能中间卡顿；首尾不同也可能合理，因为下一步就是新周期第一帧。

层面	验收标准	容易误判的做法
文件	能按 GIF 打开，包含动画，尺寸与时长符合预期	把 PNG 改名为 .gif
动作	主体可辨认，镜头与固定细节稳定，循环衔接可接受	只看一张静态预览就宣布成功
使用位置	在实际页面、消息或应用中按目标尺寸播放	假设所有上传平台都保留动画
商品逐帧看标签，吉祥物看眼睛、手、配饰和轮廓；循环要连看多遍，包括重新开始的位置。原始请求、原始结果与修改后的导出分别保存，才能定位问题出在哪一步。

没有循环扩展信息，不等于能循环。一帧 GIF 是有效图片文件，却不符合动画任务。OpenAI 发布的灯笼动画可作视觉参考，但它是官方示例，不是 Ofox 的生成结果。

缩小 GIF 或导出 MP4
先确定实际展示尺寸。小表情却上传巨大原图，会浪费体积。保留原件，每次只改一个导出变量：尺寸、帧率或调色板。压缩可能损失边缘、渐变或时间精度。

FFmpeg 调色板滤镜支持先生成调色板再导出。安装 FFmpeg 后，以下命令把宽度缩到 384 像素，并重采样为 10 fps：

ffmpeg -n -i input.gif \
  -filter_complex "[0:v]fps=10,scale=384:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3" \
  -loop 0 smaller.gif
复制
重采样不会创造更流畅的中间动作，只会改变帧时长，也可能重复帧。对浏览器转换的猫咪示例，结果为 384 × 384、11 个编码帧、1.10 秒周期、573,847 字节。周期由 1.08 秒变为 1.10 秒，所以不能称为保时长压缩。

目标平台支持视频时，可尝试 MP4：

ffmpeg -n -i input.gif -movflags +faststart -pix_fmt yuv420p \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" output.mp4
复制
本例得到 56,121 字节、1.08 秒的 MP4。MP4 不保存 GIF 的循环指令，重复播放需由播放器或目标平台设置。该命令也不保留 alpha 透明通道。转换后看实际视频，不要只选最小文件。

Gifsicle适合专门检查和优化 GIF。安装后可从 gifsicle -O3 input.gif -o optimized.gif 开始，并与原件比较。我们审查了手册，但本次没有运行 Gifsicle；它与上面的 FFmpeg 测试不同，没有本文自己的测量结果。

值得参考的 GitHub 项目及实际用途
下面的 Star 数采集于 2026 年 11 月 5 日北京时间约 11:19。它表示整个仓库受到的关注，不代表 Image 2.6 使用量、可靠性，也不是全网完整排名。成熟的后期工具可能比发布日出现的模型专用项目有更多 Star。

项目	采集时 Star	用途	边界
FFmpeg	66,513	调整尺寸、时长、调色板与视频导出	通用媒体工具，不是 Image 2.6 生成器
freestylefly/awesome-gpt-image-2	35,470	学习图片要求、画风与约束写法	Image 2/2.5 综合合集，不证明所有提示都适合 2.6 GIF
Pillow	13,969	读取帧、检查时长、合成精灵图	本地处理库，不含图片模型
YouMind-OpenLab/awesome-gpt-image-2	10,242	多语言图片提示词合集	静态示例仍需动作与循环要求，逐项核对归属
agent-sprite-forge	5,052	更复杂的角色、精灵图和游戏资源流程	审查的 0.4 流程包括图生视频，并非单纯的原生 2.6 GIF 客户端
Gifsicle	4,343	GIF 专门检查与优化	独立于模型生成
spritesheet-to-gif	36	可视化切网格与浏览器导出	本文已测试，不能修好错误原画
jkf87/gif-maker-skill	1	新的 2.6 API 与 Codex/精灵图流程	已审查源码，未安装或由 Ofox 端到端运行
awesome-gpt-images-2.6	0	新的非官方 2.6 特性与官方示例索引	新资料合集，不是已建立的热度领先项目
最贴合任务的仓库不一定 Star 最多。固定版本的 gif-maker-skill 默认 --via auto 会根据是否存在 OPENAI_API_KEY 选择路径，这可能改变流程和是否发生 API 费用。--image 连接的是 Codex 路径，不在原生 API 载荷中。读当前代码并显式选路径，不要把“命令成功”当成“参考图已使用”。

我们核对了项目说明和相关源码，实际测试了浏览器转换器与自己的本地工具；没有安装所有 Agent 技能，也没有验证维护者的生成速度声明。仓库许可和单张示例素材权利应分别核查；提示词图库说明不等于所有品牌与角色都可以任意再分发。
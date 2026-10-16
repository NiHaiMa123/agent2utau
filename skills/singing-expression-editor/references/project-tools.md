# 当前工具接入

从工作区解析项目根，先读AGENTS.md与docs/workflow.md，制作按[逐句工作循环](phrase-by-phrase-workflow.md)执行。仅保留原曲观测、Agent显式计划、函数数学、原生编译和验证；歌曲实现记录不是通用入口。

| 接口 | 作用和边界 |
|---|---|
| CLI `knowledge-context` / `knowledge.collect_context` | 设计前按问题显式检索表1/表2并绑定逐ID决策；编译门禁不证明相关经验检全或应用正确，见[知识接入](knowledge-before-design.md) |
| CLI `observe-source` / `workflow.observe_source` | 新目录解码、分离、ASR、GAME、双F0；只产观测，不生成音乐/歌词身份或音高线 |
| CLI `freeze-musical-intent` | 数值计划创建前绑定乐句源观察、演唱过程/备选、独立判据与发声校准状态；只记录工具观察到的顺序，不证明音乐判断正确 |
| Skill `scripts/design_functions.py` | Agent独立中心、有限回收、变深变速周期及局部期待；不读取原曲/作者数组，不自选动作 |
| CLI `compile-functions` / `workflow.compile_functions` | 要求当前输入工程完整覆盖和scope=whole_song；逐句用保留绝对时钟/必要上下文的工作副本，回写完整工程后验区域等价。编码PITD并查实际读回/音素几何，保留note.pitch；尚无phrase范围或逐句进度自动门禁 |
| CLI `review-inventory` / `review-execution` / `review-delivery` | 独立原生身份/实际动作/图像覆盖、事前意图对照及分层状态；见[执行契约](production-execution-review.md)。compile-functions contract v2接同一API；v1/无契约只交技术候选 |
| `expression/context_actions.py` / `curve_components.py` / `enveloped_landmarks.py` | 显式schema3音素锚点和分层有限/周期动作；与helper包络定义不同，不静默换参数 |
| Skill `scripts/compile_control_overlay.py` | 按当前音素锚点叠加Agent所选TENC/BREC/VOIC/DYN并恢复基底，不自动设计发声 |
| Skill `scripts/sparse_contour.py` | Agent自有节点的note.pitch转换；研究线重建只用于研究，不接入独立生成 |
| `expression/rhythm.py` | 当前音乐/音素时钟冲突观测；不自动改谱或源unknown |
| bridge / CLI原生导出与render-project | 实际pitch、phones、variance/acoustic输入与渲染；需当前版本、模型、缓存和speaker绑定 |
| `audio/mix.py` | 显式固定增益PCM24混音，拒绝削波；无自动平衡/压缩/归一化 |
| `expression/variance_expectation.py`的gaussian_frame_noise | 可复现诊断噪声；不选择有利种子，不证明自然度。聚合接口是实验研究，不是默认生产 |

生产不得调用已移出活动目录的旧cover/repair、候选搜索、源线统一缩幅、参考profile/复刻路线。当前CLI不会根据歌名选择数值方案。需要其它函数或原生适配时，Agent明确实现、绑定和验证，不能恢复旧包装脚本作为捷径。

白烁工程从工作区research索引读取，仅限用户授权研究。原曲事实、作者书面曲线、当前原生读回和历史声音分开；没有音频感知工具时如实记录未听。

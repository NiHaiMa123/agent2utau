# 雨爱：新Skill原曲输入重制v02

2026-10-15。状态 `yuai_newskill_v02_delivered_pending_listening`。用户授权“再按新的skill改雨爱，要求不看白烁或历史制作数据”。整曲工程、人声及伴奏试听已交付；执行复检完成，音乐质量与听觉接受仍未知。

## 输入与设计边界

本次运行：`runs/production/yuai-skill-source-only-20261015`。只从明确允许的原曲侧路径复制源录音、原曲分离人声/伴奏、GAME、ASR、源FCPE/RMVPE及HFA等14个文件；清单与SHA在`source-allowlist.json`。虽然文件存放在先前run的输入/观测目录，其角色是原曲观测；没有读取该run的生产谱面、目标线、控制、成声或生成脚本。

未打开白烁工程、作者音频或历史歌曲的制作数据作为输入。当前会话已有历史讨论背景，不能宣称Agent从未接触过本曲、绝对原创性或真正未见曲迁移通过。版本与维护哈希不作为音乐参考。

按当前ASR/原曲观测重新校对歌词，使用本机HFA对16段源音频重新推理；英文Rainie/love用明确英文音素。字词对齐、双F0、GAME始终是观测；短字端点及滑音/音符身份由本轮判断，保留不确定性。新的完整字时钟在`source/fresh-lexical-clock.json`，新音符判断在`score/melody-decisions-v1.json`。

制作知识接入使用本轮限定的定义目录`design/knowledge-scope.json`，检索定义及参数、逐ID记录外推/未知；不加载历史响应包或历史剂量作为设计依据。schema2函数计划编译时校验对应context与SHA；旧context不刷新。

## 实际制作与修订

- 新工程446个音符，49个原生乐句，371个实际元音单元。新选两阶段Normal100声库，不使用旧混合配比。
- Agent显式逐字选择有限回收、不等双转折、渐变振音或有理由的保持，选择及到达时间在`design/agent-choices-v1.json`。16段另有明确音乐目的、DYN/TENC/BREC包络及note.pitch连接，VOIC保持默认乘数；不从原曲F0数组取样为目标曲线。
- 首版保留。实际图审发现src095“爱”等跨音符长字只安排落音后的字腹，前一个长音仍成平台。第1轮音乐策略修订新增29个前段检查/选择，12个长前段增加独立动作，短准备段明确保持。`design/carried-stage-choices-v2.json`绑定这次修订；没有把所有字统一加波。共400条决策：189 center、137 finite_return、35 oscillation、39 hold；这是本轮分配，非普遍配方。
- 最终371元音、771个必要阶段，原生实际线对函数目标最大读回差0.499940c；身份、执行和选择复检无失败、无未解决标记。`review-final-v2/review.json`的`production_execution_complete=true`只表示该执行契约完成。
- 使用固定600px/s、50px/半音、相邻上下文和长字重叠页的126张实际局部图，逐字保留观察。首版实际打开34页；最终26页以PNG和底层数据精确相同证明复用，另100张最终图实际打开。371/371完整支撑审阅、numeric-only=0、pending=0。生成图册不算已看，重复歌词不自动继承结论。完整访问证据在`visual-review/actual-access-complete.json`和`final-records.json`。

原生5tick采样与任意实数时间锚点并不重合。初版地标检查因此误报；本轮记录对应输入网格的观测时刻及同一函数在该时刻的值，窗口/幅度要求/容差不放宽，保留首个失败及修复记录。离散网格以外的渲染相位不能因此视为已验。

## 新成声与核查

最终49乐句原生渲染成功，原生报告errors/warnings为空。新导出的49组acoustic/variance实际输入与当前原生缓存键/预测核对；两阶段Normal嵌入均精确，SHFC为0，acoustic/vocoder F0一致；variance音高转换误差≤0.001Hz。TENC/BREC/VOIC预测加人工增量和实际输入关系通过，三通道裁剪0帧。实际两阶段steps均20、depth约0.6。

本机旧桥接二进制缺少当前probe命令，因此另编译唯一命名的只读probe host并增量放置到安装目录；原a2u-bridge与Core保持。`native-input-host.json`及`audio-check-v2/native-input-and-waveform.json`绑定实际DLL、模型与嵌入等11项资源，最终重哈希一致。原生provenance的apphost SHA本身不等于整个程序集版本认证；这里单列实际DLL绑定。模型真实调用次数不从缓存时间推断。

最终原生PCM16单声道人声237.274秒，峰值0.470459。逐元音保留30ms窗口包络，RMS范围约−35.42至−15.75dBFS；辅音、尾音、音素/声学边界差异保留，未按RMS反向自动拉平。工程DYN已进入新原生渲染，但本次没有从声码器原始样本独立重建完整DYN/拼接/设备增益链，因此不能宣称这条链已获单独因果验证。

输出人声新提取的双F0与最终原生线在未优化延迟的元音窗口内比较：

| 检测器 | voiced覆盖 | 绝对中位差 | 绝对差p95 | >100c帧 |
|---|---:|---:|---:|---:|
| FCPE | 99.8567% | 1.3667c | 10.1107c | 18 |
| RMVPE | 99.9140% | 1.3309c | 9.4618c | 22 |

这些是检测器/原生时钟代理，所有异常帧保留在`output-f0-observations.json`；不代表发音、强弱、磨砂实感、自然度或情绪通过，也不以检测器输出回写曲线。

## 交付与后续验收

- 工程：`projects/latest/yuai_newskill_source_only_v02.ustx`；与本轮canonical `compiled-v2/project.ustx`字节相同，SHA `4e8270d9ee0695a6c77a6a5c8bdb52932d7194a10198cc321b69aeafab48863a`。执行复检仍绑定canonical路径，不冒充对另一工程路径独立复检。
- 纯人声：`delivery/雨爱_新Skill_v02_纯人声.wav`。
- 伴奏试听：`delivery/雨爱_新Skill_v02_伴奏试听.wav`。
- 两份试听均260.48秒、44100Hz、PCM24；纯人声从新native输出统一+3dB并仅补尾部静音，混音沿用允许的原曲伴奏−8dB。峰值分别0.664541/0.824509，无逐字后期增益、归一化、限幅或混响。PCM24容器不提升原生PCM16有效精度。
- 最终`delivery/manifest.json`与`delivery-review.json`绑定工程、执行复检和实际音频。渲染时先生成的“review incomplete”候选receipt保留，完整看图后另生成最终receipt，未回写历史状态。

196项本机测试通过。38份Skill文件与任务开始及安装副本一致、110个链接存在，本轮未改Skill。仓库路径/扩展名门禁通过；为遵守本轮禁读作者/历史数据，未运行会打开作者USTX/ZIP及旧payload头部的完整`check_repository.py`，不声称作者包完整性已复验。当前输入/资源/工程及Skill范围检查在`delivery/final-gate.json`，历史工作树未重置、未提交、未推送，CI没有改动或远程运行。

本轮只完成一次音乐策略修订；HFA格式/语言命名、采样地标、审阅脚本、测试夹具等技术失败及日志均保留。实际听音工具未执行；用户尚未对本v02反馈。下一步接本版整曲人声的时间点和听感反馈，必要时在当前来源边界内修订；旧v01被否决的结论不改写，新歌曲迁移仍unverified，表2不新增听觉成功或通用调参规律。

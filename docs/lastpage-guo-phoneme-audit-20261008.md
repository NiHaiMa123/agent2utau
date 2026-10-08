# 最后一页：“果”音素映射与时钟的只读核查

果-200c SHFC因无可感知改善且引入响度下降被否决。用户授权“下一步”后，本轮核查当前g→uo的映射、实际模型token/语言、原曲对齐观测及五处同字时钟。**没有发现足以支持立即改字界或拆韵母的明确错误。** 未新合成、改参数或补音量，已接受“抱”的完整方案保留。

## 映射与实际输入

基线是已接受“抱”的完整C精确副本（上一轮A），1:27未含被否决的果SHFC。绑定当前自身source_observations及native_word_geometry原哈希、原始MP3 SHA和封存原生A导出；不读取作者项目或旧撤出路线。

安装声库dsdur/dsdict-zh.yaml中`guo`和`zh/guo`均为`zh/g, zh/uo`，未错读为其它韵母。当前duration/pitch/variance词表ID为g119/uo149，acoustic词表为g138/uo177，各自独立词表应使用自己的ID；不能把跨模型ID不同误判为串字。

原生acoustic tokens中的g/uo确为138/177，variance linguistic tokens为119/149，两处语言ID均4=zh，没有回落到默认语言或未知token。原生g/uo时长为13/30帧，vocoder frame_ms约11.609978。原生音素序列完整，没有丢失g、重复起声或uo被截成空主体。两阶段实际合成speaker在此前探针已核查Normal75/Classic25；phone suffix的Bright不能替代实际embedding证据。

这里的uo是一个整体模型token。当前导出输入没有独立的u→o字内转折时间参数；存在单独u/o词表项不意味着把uo拆开就符合模型学习到的“果”。字典g的粗分类为fricative；当前实际模型输入是token、时长和上下文，不可据该分类字面就宣布g声学上被当作错误的擦音。

上游 [Chinese phonemizer](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/Phonemizers/DiffSingerChinesePhonemizer.cs)选择中文词典及语言前缀，[Base phonemizer](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/DiffSingerBasePhonemizer.cs)查询符号、按vowel/glide分配，并对预测时长按音符锚点伸缩。它支持上述机制解释；master不是本机Core的字节等同证明，本机字典/词表/原生输入是此次映射事实依据。也不能把模型内韵母谱变化自动归因到phonemizer。

## 时钟与反例

原曲HFA是已有MP3-only任务的观测，未重新对齐、修改unknown或提升为听觉真值。1:27“果”数据：

| 项目 | 原曲对齐观测 | 当前原生 |
|---|---:|---:|
| g开始 | 86.769625s | 86.757292s |
| uo开始 | 86.908030s | 86.908333s |
| uo结束/后zh开始 | 87.269612s | 87.256250s |
| g时长 | 138.406ms | 151.042ms |
| uo时长 | 361.582ms | 347.917ms |

元音起点差+0.303ms，末端约提前13.362ms，g约长12.636ms，uo约短13.665ms。它们不证明音乐节奏/发音完全正确，但当前没有明显吞元音或大幅错位的证据，不据此盲目缩g、挪uo或更改F0。

五处自己的“果”均为g→uo，已有原曲/原生时钟逐项比较保存在本机。另两处MIDI66和目标三处MIDI64的声母长度差异较大；原曲HFA本身也有这种差异，不能单凭目标g较长就判故障。1:27、约3:17、3:44三个MIDI64“如果”是更接近的听感定位样本，但音素时长、上下文及pitch动作仍不同，**不是单因素因果对照**，后两处正常/异常标签均unknown。

## 当前生成版的同字试听

从当前v02人声直接裁三段各2.3秒的ru/guo/zhe语境，按上述顺序串联，间隔0.6秒。所有PCM24采样与当前交付精确相同，不归一化或补增益，没有新预测。已接受“抱”的修改在这些片段之外，因此该处不会影响三段。

本机`runs/lastpage_guo_phoneme_audit_20261008/three_guo_original_vocal.wav`，各段“果”元音约在播放器1.1、4.0、6.9秒。原曲位置分别86.908、196.651、224.132秒；另保留三个独立片段，裁剪范围和SHA精确绑定。

下一步先取得这三处的“偏假/前顶”对比标签，再决定是当前uo整体发音、某个上下文过渡，还是其它发声因素更值得隔离。未取得标签前不认定另两处正常、不复制它们的曲线、也不直接把uo拆成u+o。当前只读核查完成，声音病因及完整自然度仍unknown，`agent_perception=false`。

此前果试验67个封存文件、本轮全部读取的source/model/dictionary/native输入保持哈希；资源索引和Skill检查通过。Git只提交报告/进度，音频、声库字典、模型和派生数组不上传。

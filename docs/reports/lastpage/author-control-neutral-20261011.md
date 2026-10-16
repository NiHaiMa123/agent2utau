# 最后一页：作者条件下取消人工发声控制组

2026-10-11。状态：author_control_neutral_delivered_pending_listening。

上轮原话“B比原版好点，但还是不如A”计1聚合回复，绑定作者A、仅换自己Normal75/Classic25的B、自己的原比较版；“原版”按上轮音频标注作语境解释，不冒称用户重新明确命名。相对偏好A>B>自己的比较版，未细分各字实感/破音/咬字/响度或绝对验收。声线组成及其预测/电平等响应对这两句有贡献，但单换声线仍未完全重现自己的较弱结果；不声明唯一生理病因。[上轮反馈](author-voice-feedback-20261011.md)另行追加，封存pending报告不改。

继续用户明确要求的作者工程副本逐步替换。本轮C是一个控制组中和：保持作者A全部notes tone/tuning/PITD/note.pitch/内置vibrato、歌词、时长、音素/CLR和两阶段声线，仅在原xs网格将TENC=0、BREC=0、VOIC=100、SHFC=0设置为已读工程声明默认值。**焦点两句原SHFC实际都为0**，所以只在这两句实际取消TENC/BREC/VOIC三人工增量；不是四个独立试验，也不能得出SHFC作用。完整42音符/3句副本保留，第三句仅原生缓存技术，不用于所交付因果试听。

## 依赖与交付检查

原生独立读回确认中和值和原网格，整个音素/音高/两阶段speaker精确；选中两句variance全部输入、预测与vocoder F0精确不变。C三人工增量均0，最终输入按相同合法范围从同一预测重建，只有这三声学通道变化。A原生证据显式复用，C新原生3句缓存技术另列；研究两句A/A_repeat/C/C_repeat共8套新variance11/acoustic101/vocoder波形。同输入重复精确；新A全部输入/预测/mel/raw/PCM及WAV字节精确重现上轮作者A。

44100 mono PCM24，A/C同212–220.5秒及固定声增益1.5；DYN无曲线、声明默认0dB，采用unity包络。按原生前导时钟在44100网格叠加句尾、保留完整第二句释放，无归一化、压缩、增益补偿或BGM。自己的原比较版原字节另保留，只作主观差距定位，因果对照为C−A。电平变化也属于控制组实际响应，不把更响自动解释为更实。

C新4次FCPE/RMVPE，A因PCM和检测器模型SHA相同显式复用4份旧F0数组；32窗口覆盖2整句及15字末音素/主体。实际输出F0、电平和最终特征只为有限代理，检测器未经本次真值校准；固定vocoder F0输入不保证两份输出检测完全相同。模型特征下限裁剪按A/C逐项列明，保持合法执行，不将计数当听觉改善。

## 试听与适用范围

先比较C与精确原作者A：取消这组后实感是否下降、仍实或变化不明显，以及是否出现破音/咬字/音量副作用。若有影响，下一轮才冻结单通道拆分；若仍有相对自己的优势，只支持这组不是维持该优势的必要条件，不排除主音、时钟、声线交互或更小差别。当前未听反馈pending，未采用；不自动追加通道/剂量或修制作版。表1PER:S1、PARAM:C11/12/13.01三实际控制及C14.01无实际SHFC干预，表2RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01开发记录，measurement_validated=false、通用规律0、Agent未听。

原歌曲/音频/作者原件/Skill保持，原Normal75/Classic25及抱C、Bright25与有限VOIC阴性保持。这里新“C”是作者控制组研究版，不覆盖旧3:04抱C的局部接受ID。单Agent、CI仅workflow_dispatch。

|句|版|BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|
|---|---|---:|---:|---:|
|0|A|0|40|0|
|0|C|0|0|0|
|1|A|0|45|0|
|1|C|0|0|0|

- [A独立人声](../../../runs/experiments/lastpage-author-control-neutral-20261011/delivery/A_two_phrases.wav)
- [C独立人声](../../../runs/experiments/lastpage-author-control-neutral-20261011/delivery/C_two_phrases.wav)
- [own_original_comparator独立人声](../../../runs/experiments/lastpage-author-control-neutral-20261011/delivery/own_original_comparator.wav)

[JSON](author-control-neutral-20261011.json)、[32窗口CSV](author-control-neutral-20261011-windows.csv)、[审计](author-control-neutral-20261011-audit.json)。

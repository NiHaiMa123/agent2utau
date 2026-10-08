# 独立评价 v0

只读工程、显式原生导出和版本绑定。程序不加载函数计划、expectations、作者profile、旧歌缓存或历史波形，不修歌、不修改阈值、不自动补数据。

## 运行

```powershell
python -m agent2utau.evaluation --project projects/latest/lastpage_loudness_v02.ustx --out runs/check-static
python -m agent2utau.evaluation --project projects/latest/lastpage_loudness_v02.ustx --out runs/check-native --native-pitch runs/native/pitch.json --phonemes runs/native/phones.json --provenance runs/native/provenance.json --feedback runs/feedback.json
```

`--role author_research_only`用于作者原件，默认角色是current_agent_generated。`--config`显式读取Thresholds字段JSON；未知字段、非有限或不合理值拒绝。默认阈值固定在features.py并完整写入每份summary，未根据三首歌曲调参。

输出新目录必须不存在；输入与产物不自动搜索。summary.json记录输入SHA、代码commit和实际代码文件SHA、角色、时轴、当前环境、覆盖和unknown；regions.jsonl保留全部note/phone/vowel/phrase及特征；findings.jsonl保留所有候选；report.md为简报。反馈输入存在时另写feedback_cases.json。

## 绑定契约

先对同一当前工程执行现有`export-pitch`和`export-phonemes`，同时保存provenance：

```json
{
  "schema_version": 1,
  "project_sha256": "<工程SHA>",
  "pitch_sha256": "<音高导出SHA>",
  "phonemes_sha256": "<音素导出SHA>",
  "environment": {
    "core_sha256": "<OpenUtau.Core.dll SHA>",
    "bridge_sha256": "<a2u-bridge.dll SHA>",
    "singer_id": "<实际声库ID>",
    "singer_config_sha256": "<当前声库dsconfig.yaml SHA>"
  }
}
```

绑定必须由获取导出时的实际环境记录；事后填入当前环境不能证明旧导出的历史条件。评价器核对三个文件SHA、单位、part/track、note身份与时钟、pitch和phone导出的一致性。错绑定/错单位/坏几何/无效采样拒绝；缺绑定只做static_only。环境字段是来源证据，不能证明未提供的模型输入或音频状态。

可选feedback.json：schema_version、project_sha256、audio_path、audio_sha256、delivery_manifest、timebase和cases。cases每项含id、time_s、label。`timebase=delivery_identity`只适用于未经剪裁/变速的完整交付；delivery_manifest的files必须同时绑定当前工程名和音频名。四个反馈时刻只定位原生候选和前后0.6秒唱字语境，不升级为实测声学边界。

## 指标边界

- 平台/漂移/有限运动/周期候选来自真实输入序列；线性去趋势、6c显著性、有序峰谷、3–12Hz候选和支撑限制都是可见方法。起尾部分波、振幅比、速率变化、不对称均为描述，不赋好坏标签。
- 默认跳变80c或速度差18000c/s触发5-tick网格候选。SP/AP内部候选排除；过渡折点包含前一个采样的分区。缺采样、未知ownership和未知phone不静默计为唱区通过。
- phone分类支持明确的中文final/声母和ARPAbet集合；未支持符号及歧义ownership记unknown。同一primary note且同元音相接的phone合并，跨音符续音不重起。
- TENC/BREC相关性按存储节点并集上的声明折线计算，未按时间加权，也不含预测基底；全part相关性可能掩盖局部关系。它只触发coupling_risk。VOIC和DYN各自统计，不混成单一响度。
- 每条曲线分别记录点数、默认点、非默认点、连续非默认点串、物理跨度、密度、范围。连续点串不是Agent决策数；1单位误差的RDP折线复杂度只作可复算代理，不是Core重构、更不代表过密必然难听。
- 单份原生线不是实测F0；多相位、实际模型输入、声学对齐、共振峰和音频感知均单列unknown/skipped。raw候选不是整曲假阳性，未标注歌曲无真实误报率/漏报率。

P0实际结果见evaluation-v0-findings.md；后续只推荐evaluation-v0-next-step.md中的一个受控工作项。

## 显式单因素响应探针（P1）

`python -m agent2utau.evaluation.controlled_probe --a <native-A.json> --b <native-B.json> --variance-a <variance-A.json> --variance-b <variance-B.json> --channel tension --support <start-s> <end-s> --analysis <vowel-start-s> <vowel-end-s> --out <new-directory>`

只消费缓存验证后的原生输入，不编辑工程。要求 A/B 的完整音素、pitch、模型、variance 条件和所有非选通道精确相同，实际干预必须落在声明支撑内。当前适配布局限定 variance/acoustic 同网格、Normal75/Classic25、variance11/acoustic101，拒绝其他布局；这是诊断条件，不是通用音乐参数建议。输出新合成 A、无变化重复、B、输入/预测、权重不变的随机适配证明及去电平 log-mel 谱形代理。原生 DYN、邻接拼接、交付 PCM、实测 F0 与反馈音频绑定需由实验记录另行核查。该命令不宣称自然度、共振峰真值或用户反馈原因。

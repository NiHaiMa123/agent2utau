# 当前执行流程

## 环境

从仓库根运行。`configs/defaults.yaml` 为默认设置；机器差异写入未跟踪的 `configs/local.yaml`（至少设置 `openutau_dir`、`default_singer`）。实际需要当前 OpenUtau、所选声库、GAME及RMVPE依赖、MelBand成套权重/YAML与manifest、ffmpeg、FCPE、Whisper、HubertFA。仓库不携带模型或录音。

`agent2utau deploy-bridge` 编译部署到配置的OpenUtau目录；bridge必须在那里运行，复用当前Core。`doctor`区分资源存在、声库加载与未执行的音频检查。

## 从头观测与判断

`observe-source <audio> --out <新的目录>` 默认解码并做分离、ASR、GAME、FCPE、RMVPE。`--steps asr,game,fcpe,rmvpe` 可明确选择观测步骤；不含separate时分析解码的原混音，需声明局限。每次新目录，绑定源哈希和实际产物，不扫描旧歌或作者项目。

GAME是音符事件，不是逐帧F0。ASR字符跨度是近似观察，不是已核实字界。Agent结合音频观测与语义准备歌词和HFA输入（裁剪音频与同名.lab），再执行当前HubertFA，例如：

```powershell
python external/HubertFA/onnx_infer.py -m external/hfa_model/1201_hfa_model/model.onnx -wf runs/new/hfa_inputs -l zh -np AP,EP -o runs/new/hfa
```

绑定HFA模型、输入与输出；保留unknown。Agent自行选择谱面和AP/SP上下文，用 `openutau/build.py` 或显式USTX编辑构建自己的音符，不自动把源F0直接写成PITD。

## 明确设计并编译

先用 `export-pitch` 和 `export-phonemes` 得到自己的谱面在当前声库中的原生时钟。Agent按 Skill 判断每个元音阶段与边界，填写函数节点、有限动作、周期深度/频率/相位，以及目的、备选、局部期待。`scripts/design_functions.py` 的schema1只接受 `agent_designed` 计划，函数数学不替Agent判断。

`compile-functions --plan <json> --out <新目录>` 的外层格式：

```json
{
  "schema_version": 1,
  "project": "score.ustx",
  "source_audio": "source.wav",
  "input_hashes": {"score.ustx": "<SHA256>", "source.wav": "<SHA256>"},
  "scope": "whole_song",
  "phrases": [{"part_index": 0, "position": 0, "design": "<此处填完整函数对象，不是文件名>"}]
}
```

路径相对计划文件。phrases按原生导出顺序完整排列；position是原生phrase.position，非秒。design是Skill helper完整schema1对象（support_s、center_nodes、components、decisions、expectations），support_s覆盖该句所有原生前导/尾帧。`center_nodes`为[绝对秒,绝对cents,cents/秒斜率]。这不是从旧曲profile选择路线。

编译器移除原有PITD和内置vibrato重复贡献，保留Agent自己的note.pitch、音符/音素时钟和其它表达；before-PITD仅参与目标编码。检查全部乐句覆盖、局部期待、范围、整数网格冲突、音素几何和实际读回≤0.501c；失败留日志，不输出成功声明。

schema3 `expression/context_actions.py`仍可执行显式音素锚点的分层动作，但它与上述helper的函数/包络定义不同，不能静默混用参数。需要其它函数时明确实现并验证，不改为近似模板。

## 发声、渲染与验收

发声事件通过Skill `compile_control_overlay.py`写入有限支撑；只编译所选控制，不自动补VOIC或每字归一化。SHFC、GENC、CLR及模型支持须单独核实。发声控制不是compile-functions自动生成的内容。

`render-project`调用原生渲染；`export-render-probe --indices 0,1,...`导出当前variance/acoustic实际输入。当前条件改变后重算依赖；固定种子、缓存、声线embedding、模型权重与波形拼接须另行绑定，不能直接复用旧状态。

`audio/mix.py`只使用明确给定的固定声/伴奏增益，PCM24输出；不自动平衡、不压缩或归一化，削波时失败并要求重新选择增益。分开检查音高、字界、发声、真实短窗能量与听感；没有听觉验收不宣布自然度解决。

当前七个《最后一页》脚本保留作为这条制作方法的已完成实现记录，含当次Agent明确数值选择及原路径/哈希限制，不作为可直接重跑的新歌CLI。最近试听问题仍待处理，本次只是清理和发布代码。

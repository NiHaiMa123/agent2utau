# 当前制作流程：GAME → 音素和时间修正 → DiffSinger 自动音高

更新：2026-10-31。**执行标准：[根目录 plan.md](../plan.md)**。旧“逐句手绘音高、编译表达函数”流程停止作为默认主线。

## 输入

原曲音频、用户确认的锁定歌词、当前泠鸢 DiffSinger 声库/phonemizer、OpenUtau、GAME、ffmpeg；ASR/HFA 仅是歌词与时钟观测。机器设置在被 Git 忽略的 `configs/local.yaml`，新 run 位于 `runs/production/<run-id>/`，Git 可提交的歌曲 session 索引仍在 `songs/<song>/`。绑定输入 SHA、采样率、录音偏移、源绝对时间。

## 现有 CLI 入口

~~~powershell
python -m pip install -e .
agent2utau doctor
agent2utau observe-source "<音频>" --out "runs/production/<新任务>/observations" --steps separate,asr,game
agent2utau export-phonemes --project "<工作谱面.ustx>" --out "<音素.json>"
agent2utau export-pitch --project "<工作谱面.ustx>" --out "<音高.json>"
agent2utau roundtrip --project "<工作谱面.ustx>" --out "<回读目录>"
agent2utau render-project --project "<已核验工程.ustx>" --out "<音频>"
~~~

这些是**已有能力**，不是现成的一键歌词—音素对齐。`observe-source` 只输出观测。GAME 给 note events，不自动保证唱字与每个音符匹配。`openutau/build.py` 用固定 120 BPM / 480 分辨率将绝对秒量化至 tick，并非估测原曲 BPM。`compile-functions` / `freeze-musical-intent` / `singing-expression-editor` 仍保留给旧显式表达实验，**不作为新主线依赖**。

## 待实现的新闭环（依 plan.md 分批开发）

1. **P0 锁定身份**：歌词以用户核实文本为准、按出现顺序标 syllable_id，GAME 每个 note 标 note_id，统一音频/HFA/ASR/GAME/USTX 绝对时间基准；保留 `+` 延音与 rest。
2. **P1 字—音符映射**：程序根据字序、GAME、HFA/ASR 候选生成单调动态规划 baseline，保存多候选和 unresolved；不能丢字、多字、乱配重字或胡乱合并 `+`。
3. **P2 原生音素**：建无人工 PITD 的 baseline.ustx；真实调用当前声库 `export-phonemes` 获取符号、所属字和时间。原唱 HFA 边界不可机械覆盖合成预测；只对确定问题生成有 ID 的局部 patch。
4. **P3 小模型消歧**：一次 5～15 字，只能选择程序提供的 candidate_id 或 unresolved。Schema、索引、声库词表、单调性、时间/tick 和修改隔离由程序检查；失败最多针对性修复 2 次。
5. **原生验收**：patch 在副本写回；Core roundtrip + phoneme 重新导出，核对 before/after，连带检查受影响邻句和缓存。失败不得声称 validated。
6. **自动音高与试听**：使用泠鸢 DiffSinger 自动 pitch、默认发声，不叠加旧人工 PITD；固定增益混音、核对峰值和伴奏对齐。整曲听感由用户确认。
7. **跨模型评测**：固定人工标注样本，对照无 Agent baseline / MiniMax / DeepSeek / GPT-6.1 Sol / Gemini 4；报告漏字、误差 median/p90、原生有效率、失败率、重试、成本及实际听感。

## 暂缓

其它参数（VOIC、BREC、TENC、DYN、PEXP 等）默认不改；是否需要 Agent 自动调节尚待有控制的 A/B。混音先透明固定增益，是否使用现成自动混音/母带基座留到音素/时间闭环稳定之后。历史 runs、reports、knowledge、旧歌曲 USTX 不迁移或覆盖。

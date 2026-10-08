# 原曲人声／伴奏分离

用户2026-10-04指定后续新分离使用从dotstts复制的 **MelBand Roformer | Vocals by Kimberley Jensen**。模型是`vocals_mel_band_roformer.ckpt`，配套`vocals_mel_band_roformer.yaml`，项目位置`models/separation/melband_roformer/`；配置与权重必须成套使用。模型由当前项目读取，不继续依赖dotstts目录，也不自动换成同族其它checkpoint。

模型权重SHA256：`87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e`。
配置SHA256：`b958b29c8f7195f0d86bee6759a33980db675c4ecaf2fcaa80fa125828e6cd38`。
源副本／下载登记与完整hash见同目录`manifest.json`。这是用户选择的本地模型，不声称是全网最新发布或所有歌曲效果最佳。

用工作区根解析路径，Python调用`agent2utau.audio.separate.separate(source_wav, new_run_stems_dir)`；默认即上述模型。`separation_settings()`在加载前核对权重／配置／本地登记hash；库通过本地model_file_dir加载，环境变量若将其覆盖到别处则明确失败，不静默降级为旧模型。两分轨保存WAV、44100Hz；默认按模型YAML分块，batch1，不擅自改变精度或推理参数。实际CPU／CUDA从本次返回backend记录，不能沿用旧onnxruntime-cpu标注。

新分离返回的source_sha256、model_path／model_sha256、config_path／config_sha256、库版本／settings、实际backend和两条分轨路径纳入manifest。模型／YAML／运行设置或源内容变化时使用不同缓存身份，cover与diagnose入口已使用该身份，不把旧MDX源分轨／F0／GAME/HFA缓存接到新结果。

输出文件stem标签可能小写`(vocals)`／`(instrumental)`，也可能是`(other)`伴奏，按实际返回解析并核对存在。检查源与输出时钟、时长、采样率、声道、有限样本和峰值，分离质量仍需听感。分离不保证完全没有伴奏残留，也不使估计F0成为生理真值；unknown与已冻结源事实不因换模型自动提升。

用户只要求复制模型／指定使用时，不自动重做已接受歌曲。已有使用旧分离模型的产物和冻结研究保留其原文件与来源。用户后续要求以新模型重做时，新run分别更新分离、源F0、转谱／对齐及伴奏绑定，保持原调／原时钟；不要修改旧manifest或在旧声学输入上伪称新分离完成。

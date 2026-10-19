# 每次打开的音色重映射提示：可能改条件，当前截图为空ene误识别

用户截图标题“音色重映射”，目标轨“白烁·完整主唱”，行“energy (curve) → Yousa_Cute”；用户说每次点好，并进一步确认我们的轨道也会弹。截图是用户提供的静态UI证据，不是Agent读取的实时界面；我们的弹窗具体行/映射尚未看到。

## 已确认的行为

“好”会应用映射，不只是关闭提示。软件有两种会复用此对话框的路径：旧CLR音素声色索引重映射，会修改对应轨音素的CLR；导入vocal-mode曲线映射，会把源曲线复制到clNN（目标曲线已存在则跳过）。不能只看同一个弹窗标题，认定执行了哪一种。

本轮核查官方[ViewModel](https://github.com/openutau/OpenUtau/blob/master/OpenUtau/ViewModels/VoiceColorMappingViewModel.cs)、[对话框](https://github.com/openutau/OpenUtau/blob/master/OpenUtau/Views/VoiceColorMappingDialog.axaml.cs)与[MainWindow加载/应用路径](https://github.com/openutau/OpenUtau/blob/master/OpenUtau/Views/MainWindow.axaml.cs)。另用只读PE元数据/IL检查当前已安装OpenUtau.dll，不加载UI、不替换App/Core：本机`IsImportedVocalModeCurve`排除了dyn/pitd/tenc/brec/genc/voic/shfc/clr/clry/opec及cl前缀，却未排除ene；筛选lambda也未检查曲线节点数。实际异步应用路径在目标曲线存在时跳过，否则拷贝源xs/ys到clNN；这些分支和谓词已存IL证明。

当前参考主唱和和声均带有**0节点的ene空曲线**，且都已含空cl01。因而“energy (curve)”被误识别为导入声线，足以解释截图这种仅Default/energy两行的重复提示。它不是声线名称表必然缺失：当前磁盘工程和已有autosave三轨voice_color_names均为完整5声线表。

在截图所示SelectedIndex1情况下，本机导入曲线路径构造目标cl01；UI显示的声线名与实际clNN子库索引不能混写。当前该轨已有cl01，应用应跳过拷贝；即使没有，拷贝0节点ene也不是一条有数值的Cute混合包络。所以**这张图不能证明整轨被切成Cute，也不足以解释此前全部听感差异**。重复打开时原ene空对象仍在，扫描会再触发；反复出现不等于每次累加一次声线强度。

## 我们的轨道仍需单独核对

用户明确报告我们的轨道也弹，不能忽略。若它走CLR重映射或导入的是有值曲线，点好确可改变音素声线/两阶段speaker条件，使UI试听不同于原磁盘/命令行渲染。即使尚未保存，内存中的修改也可能先影响试听；当前IL/源码检查不是对用户现场状态的捕获。

但当前磁盘我们的148音符、原生已核查Normal CLR3、非PITD曲线和第一三句Classic混合保持；其曲线只有voic/pitd/brec/tenc/cl05/dyn，无会被上述导入过滤器选中的ene或其它曲线。已有autosave是更早138音符版本，自己的曲线也没有这个导入候选。两份磁盘快照不能复现“当前我们的同类energy映射提示”，也不能据此否认用户观察。需要我们那张弹窗的完整行/选择，以及实际打开的工程/软件路径，才能定位其分支；没有证据不写成CLR已被改、读了旧工程或使用不同软件版本。

前面的即时分析把“两行提示”当作旧声线名称表不一致证据不准确，本报告纠正为可由导入曲线模式触发；该更正不抹除用户真实反馈。既有离线原生speaker检查仍对所绑定工程/音频成立；现场试听是否同条件新增未知，不能由本截图宣布全部旧接受/否决无效。

## 当前处理

再次遇到含义不明的映射先取消，尤其不要把energy曲线当新声线直接选Cute。当前自己轨道弹窗需要单独截图确认；这是缺失现场输入，不是再让用户批准已授权制作。未核实前不继续用现场反馈拟合声线参数或归因单一模型机制。

本轮只读诊断，没有修改当前USTX、autosave、参考载荷、软件、Skill或音频，没有新模型推理/CI，前三句AP/SP候选仍保持原发布SHA `91b5289bd11c5c7728507ae9f4fbabaaad5cedf4c12f0dc1276113ebd880b675`，听感仍未获确认。空ene对象可在明确清理任务中单独处理；本次未借诊断擅自修改受保护参考或更新安装软件。单Agent，第五句/s15以后未启动。

本轮run `runs/review/yuai-voice-remap-dialog-20261018` 保存官方两小文件、当前App/Core SHA、本机导入处理器和相关lambda的IL、两份磁盘逐轨曲线/CLR清单及保护核查。一次官方大文件connector读取未返回而被终止，改用官方raw网页完成核对；CIM/进程查询未能获得现场应用身份，未据失败猜测路径或UI状态。

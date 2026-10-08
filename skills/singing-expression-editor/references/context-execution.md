# 音素上下文动作接口

在已选择字头、主体、释放或周期后使用。函数执行计划，不决定画法；选择见[参考画线条件](baishuo-drawing-method.md)。

## 当前库接口

`src/agent2utau/expression/context_actions.py`执行调用者完整声明的schema3乐句：

- `melody_nodes`：绝对cents稀疏节点及可选`slope_c_per_s`，C1 Hermite连接，包含原生前导／尾帧。
- `local_gesture`：body／articulation／release的有限支撑动作，端值及导数为零。
- `body_landmarks`：主体稀疏慢走势，端偏差为零，节点由计划声明。
- `dynamic_periodic`：独立支撑、渐入／渐出、深度、速率、相位，按实际秒积分频率。
- `periodic_landmarks`：周期通道的有序峰谷，允许不同时距、偏置和深度；端偏差为零。
- `enveloped_periodic_landmarks`：实际峰／谷相对主音的偏差，配独立attack_end／release_start／end；节点覆盖完整支撑，C1峰谷插值继续至尾部，独立quintic深度包络渐隐，不把最后半波拖长接零。内部使用`enveloped_landmarks.py`；不选择参考或自动补周期。
- `sparse_enveloped_route`：完整局部路线的相同有限包络，消费每个节点的 `slope_c_per_s`；极值可零斜率、单调途中保留连续斜率。接口不自动证明路线为周期，旧 `enveloped_periodic_landmarks` 保持零极值斜率语义。

锚点kind为phrase_start／phrase_end、note_start／note_end、phone_start／phone_end。note／phone使用实际index，offset_s为相对原生锚点的秒。绝对主旋律与局部偏差分开。`phone_geometry`必须匹配当前原生几何，不能代换作者时钟或HFA。

`note_targets`按真实note_index完整排列，`groups`按primary完整归属；melody_nodes实际生成旋律，note_targets为声明与身份账本，两者在主体段互相核查。空动作仍需明确目标。缺失／重复归属、未知锚点、unsupported及超预算不得静默绕过。

budgets分别限制body、articulation、release、periodic的堆叠结果。依据当前可执行选择声明预算，工程边界不代表音乐常数或作者幅度范围。可用段容不下动作时记录原请求、调整与理由，不偷偷删动作或重定时。

## 接入与核查

音符硬阶梯的反向 PITD 抵消可能隐藏点间或显示边界问题；必要时按[连续画线约定](continuous-contour-and-scale.md)先写原生 note pitch 的音乐连接，重新导出实际 before-PITD。完整音乐身份／音素时钟保持核查，note pitch 字段允许所选变化。有单调中心节点时传入正确斜率，不能全部零斜率制造折停。

库接口不能保证现有整曲包装适用于任意曲目。调用前查真实CLI、schema、输入范围、模型、speaker和输出绑定；需要适配时保留身份检查，不能删断言让错误输入通过。歌曲准备器及运行参数不作为Skill通用入口。

编译清除旧偏移后采样完整目标，以原生before-PITD换算整数偏差，再读回最终绝对线。独立复算节点／多项式、相位、包络和最终动作顺序；检查所有原生帧与量化误差，不以组件算术正确替代最终形态。

音高／speaker／音素条件改变后导出新variance与acoustic条件，重算缓存及状态。检查实际两阶段speaker、逐句波形拼接、原样AB、全局混音、哈希、削波和实际F0；unknown保留。数值形状数量、变化帧数或tracking精确不证明自然度，旧音频接受不能自动迁移到新输出。

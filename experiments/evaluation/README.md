# experiments/evaluation — 独立评价

生产级评价接口仍在 src/agent2utau/evaluation（不搬出）；此处只放方法实验脚本，目前为空。

## 当前已有入口

（暂无）

---

边界：只有**跨歌曲可复用**或**有明确对照协议**的方法实验放这里；
属于某首歌的局部修订/试唱/审计留在 `songs/<song>/sessions/<session>/`。
具备受控输入、断言、可重复 pass/fail 的测试才进 `tests/`；生产评价代码留在 `src/agent2utau/evaluation`。

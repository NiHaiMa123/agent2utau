# 2E抱225局部人工反馈

2026-10-11。状态partial_human_feedback_recorded，2E整体未完成。

用户原话：**k3最好**。消息紧接四份独立完整上下文“抱”人声K1–K4交付，记录为该呈现集合中的K3偏好。K3对应S完整SHFC路径，固定剂量−400c及145ms进入/55ms退出。其他三版之间的排序及逐对可辨性未获得明确反馈。

| 呈现编码 | 冻结研究路径 | 原交付完整单声道人声SHA256 |
|---|---|---|
| K1 | A | `fb2f4519aaae02fabe3a7b7b77251a5919af7025d6b2fd067056fdf63c5dcf85` |
| K2 | D | `ede3375f8e69606eaf0aecb0f612e8c2fe6b6218488ac6bff6565ae07e3367cc` |
| K3 | S | `db489746e56ed3f7e48a8dd5cd6ed2a7089e4c81ad327fbc358676c7dde426cc` |
| K4 | P | `5edf0f6cb46a258e4df3175125b7ab1cb3ccb546889396e2386d245ff5f4d7b5` |

字头、破音、响度、咬字、字腹、自然度及绝对可用性均未细分评价；实际听过的文件集合、顺序、重复次数、设备、播放器、音量及盲听程度未知。本次不将排序补写为“完全无破音”或整曲验收。“只214”、混音和固定成对对照仍待明确反馈。

技术封存曾核查新抱S与旧抱C的fresh输入、预测及raw PCM精确相同；旧C-B“可以”和本次四版本排序为分别保存的反馈事件。本条只支持当前条件/剂量/呈现下S被选为最佳，不宣布单通道病因或通用调参规律。全部measurement_validated仍false。

本轮新反馈1、新模型调用0、新波形0；原歌曲、既有音频、Skill、安装与封存run不改。484运行文件和4份技术报告逐字节SHA重查，79生产/Skill/工程及67保护输入SHA保持。更新前6份当前入口与4份技术报告原字节保存至新反馈run，技术报告原先pending时态保留。

结构记录见[JSON](table2-stage-2e-word225-feedback-20261011.json)，本轮核查见[审计](table2-stage-2e-word225-feedback-20261011-audit.json)。原技术报告见[2E实际执行](table2-stage-2e-execution.md)，协议见[路径分离](validation-protocols/shfc-path-separation-v1.md)。下一步继续同批剩余试听/反馈，不增加条件、剂量或波形，不进入2F–2H。

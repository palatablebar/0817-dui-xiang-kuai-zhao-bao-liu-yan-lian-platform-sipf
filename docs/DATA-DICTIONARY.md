# 字段与业务定义

输入编码 UTF-8，允许 BOM。首行必须匹配样例列顺序。记录键和业务组保留原始字符串。`kind` 允许 object, ref, snapshot, control。说明列 `note` 可以跨行，限制 200 字。

业务字段按 `object_id`、`snapshot`、`day`、`size_bytes`、`policy` 排列。数字接受非负整数、全角数字和完整千分位。空串、短横线、N/A、NULL 与未知为缺值。无关字段用 0 占位。

保全对象、活动快照引用及保留期内对象均留存。入库日小于等于当前日减保留期时到期。结果只生成回收候选和保留依据。

`incoming.csv` 包含四个业务组，第二组提供不同边界，第三组触发业务拒收，第四组需要核对。另含重复表头、冲突记录、重复回放与错误列数。`ready.csv` 含可以签发的两个组。`handover-late.csv` 模拟快照定义晚到，`handover-reissue.csv` 为补发定义后的材料。

## 交接闭合单字段

执行批次报告中的 `closure`：`basis` 为旧依据批次号；`objects` 按 `业务组/对象` 给出动作（CARRY_OVER 沿用、ADJUDICATED 新裁、RETAINED 保留、QUARANTINED 隔离）、结论、原因与引用链指纹；`summary` 汇总四类动作数量；`reconciliation` 列出源对象缺失、快照定义缺失、无主引用和隔离项等对账差异；`releasable` 为无差异才可签发，`blocked` 标出阻断批次。

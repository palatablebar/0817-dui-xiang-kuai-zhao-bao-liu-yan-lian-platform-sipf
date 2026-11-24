# 对象快照保留演练台规则登记

- 规模：中型

## 功能模块

| 模块 | 动作 | 接口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 样例采信 | 预览并定位坏行 | `POST /api/stages/intake` | `app/intake/service.py` | `tests/test_intake.py` |
| M2 引用展开 | 检查领域约束 | `POST /api/stages/prepare` | `app/modules/prepare.py` | `tests/test_prepare.py` |
| M3 保留裁决 | 查看业务计算结果 | `POST /api/stages/calculate` | `app/modules/calculate.py` | `tests/test_calculate.py` |
| M4 回收核量 | 查看签收判定 | `POST /api/stages/policy` | `app/modules/policy.py` | `tests/test_policy.py` |
| M5 运行对账 | 对照输入、采信和隔离行 | `POST /api/stages/balance` | `app/modules/reconcile.py` | `tests/test_reconcile.py` |
| M6 批次复核 | 执行批次并签发或暂缓 | `POST /api/runs、PATCH /api/runs/<id>` | `app/review/service.py` | `tests/test_review.py` |
| M7 证据交付 | 下载复核清单 | `GET /api/runs/<id>/evidence` | `app/evidence/render.py` | `tests/test_evidence.py` |
| M8 交接闭合 | 按旧依据裁决沿用、隔离并留对账差异 | 随 `POST /api/runs` 生成 | `app/modules/handover.py`、`app/modules/chain.py` | `tests/test_handover.py` |

## 交接闭合裁决

换月交接时上游快照定义常晚到。执行批次时以最近一批已签发批次为旧依据，按对象展开引用链（`chain`）并逐对象裁决：

- 沿用（CARRY_OVER）：旧依据可追溯，控制参数、对象属性与快照定义指纹完全一致，直接沿用已签发结论，不重复生成。
- 新裁（ADJUDICATED）：本次材料完整的新对象，按本次材料计算结论。
- 隔离（QUARANTINED）：身份不明（引用缺失快照定义）、本次材料冲突或引用变化，挡住整批签发。
- 保留（RETAINED）：旧依据中的对象本次源材料缺失，保留上一版结论。

源对象、快照定义和隔离项任一对不上都在闭合单 `reconciliation` 中留出对账差异；存在隔离项或差异的批次标记 `blocked`，上一版签发批次保留为有效依据。补发材料重跑只补齐受影响对象。

## 输入陷阱

| 编号 | 规则 | 处理 | 测试 |
|---|---|---|---|
| TRAP-02 | 去除 BOM | `app/intake/reader.py` | `tests/test_intake.py::test_bom_preserves_identifier` |
| TRAP-03 | 按逻辑记录读取引号内换行 | `app/intake/reader.py` | `tests/test_intake.py::test_quoted_newline_is_one_logical_record` |
| TRAP-04 | 重复表头计入忽略行 | `app/intake/service.py` | `tests/test_intake.py::test_repeated_header_is_counted` |
| TRAP-05 | 异常列数隔离 | `app/intake/schema.py` | `tests/test_intake.py::test_extra_column_is_isolated` |
| TRAP-06 | 归一化全角数字和千分位 | `app/intake/numeric.py` | `tests/test_intake.py::test_full_width_and_grouping_are_canonical` |
| TRAP-07 | 空值行隔离 | `app/intake/numeric.py` | `tests/test_intake.py::test_sentinel_keeps_row_out_of_total` |
| TRAP-08 | 记录键保留前导零 | `app/intake/schema.py` | `tests/test_intake.py::test_bom_preserves_identifier` |
| TRAP-14 | 冲突版本都进入隔离 | `app/intake/resolve.py` | `tests/test_intake.py::test_duplicate_conflict_removes_both_copies` |
| TRAP-16 | 引号未闭合时拒收文件 | `app/intake/reader.py` | `tests/test_intake.py::test_unclosed_quote_invalidates_source` |
| TRAP-18 | 区分空文件、全空白和仅表头 | `app/intake/reader.py` | `tests/test_intake.py::test_empty_states_have_distinct_causes` |
| TRAP-26 | 拒绝旧版本复核 | `app/review/store.py` | `tests/test_review.py::test_review_optimistic_lock` |

## 领域反例

保全对象、活动快照引用及保留期内对象均留存。入库日小于等于当前日减保留期时到期。结果只生成回收候选和保留依据。

逐组预期结论见 `tests/test_policy.py`，计算过程证据见 `tests/test_calculate.py`。

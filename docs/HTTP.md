# 阶段接口

`POST /api/stages/<stage>` 接收 `multipart/form-data`。字段 `sample=dirty`、`sample=clean`、`sample=late`、`sample=reissue` 或 `file=<CSV>` 三选一。阶段为 `intake`、`prepare`、`calculate`、`policy`、`balance`。预览不入库。

`POST /api/runs` 接收同样的输入，执行全批并返回运行报告。报告内 `closure` 为交接闭合单：以最近已签发批次为依据逐对象裁决沿用、新裁、保留或隔离，并给出对账差异与 `releasable`、`blocked` 标记。`GET /api/runs` 返回最近 50 批，含 `blocked` 阻断标记。`GET /api/runs/<id>` 查询一批和当前复核状态。

`PATCH /api/runs/<id>` 接收 `revision`、`status` 和 `note`。状态使用 `APPROVED` 或 `HELD`。行对账或闭合单存在未决差异时签发返回 `UNRESOLVED_ISSUES`。冲突返回 409，客户端读取新版本后重试。

`GET /api/runs/<id>/evidence` 下载内含运行清单、交接闭合单、行号隔离、业务证据和复核信息的 JSON。

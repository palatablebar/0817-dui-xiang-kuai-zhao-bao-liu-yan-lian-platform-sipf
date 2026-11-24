COLUMNS = ("object_id", "snapshot", "day", "size_bytes", "policy")
KINDS = ("object", "ref", "snapshot", "control")
PROJECT = {
    "name": "对象快照保留演练台",
    "actor": "数据湖值班工程师",
    "stages": [
        ("intake", "样例采信"),
        ("prepare", "引用展开"),
        ("calculate", "保留裁决"),
        ("policy", "回收核量"),
        ("balance", "运行对账"),
    ],
    "chart": "候选容量",
}

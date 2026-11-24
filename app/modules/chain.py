"""按对象展开引用链，供交接闭合核对。

与 prepare 不同，这里不抛业务异常：把控制行、对象、快照定义和引用
逐项落成可序列化结构，问题记入 issue 字段，由闭合裁决按对象隔离。
"""
from app.business import by_kind


def expand(rows):
    controls = by_kind(rows, "control")
    issues = []
    control = None
    if len(controls) != 1:
        issues.append("EXPECTED_ONE_CONTROL")
    else:
        current = controls[0]
        control = {
            "day": current["day"],
            "policy": current["policy"],
            "size_bytes": current["size_bytes"],
        }
    objects = {}
    for row in by_kind(rows, "object"):
        key = str(row["object_id"])
        if key in objects:
            objects[key]["issue"] = "OBJECT_CONFLICT"
            issues.append("OBJECT_CONFLICT")
            continue
        entry = {
            "day": row["day"],
            "size_bytes": row["size_bytes"],
            "policy": row["policy"],
            "refs": [],
            "issue": None,
        }
        if control is not None and row["day"] > control["day"]:
            entry["issue"] = "OBJECT_CONFLICT"
            issues.append("OBJECT_CONFLICT")
        objects[key] = entry
    snapshots = {}
    for row in by_kind(rows, "snapshot"):
        key = str(row["snapshot"])
        if key in snapshots:
            snapshots[key]["conflict"] = True
            issues.append("SNAPSHOT_CONFLICT")
            continue
        snapshots[key] = {"day": row["day"], "policy": row["policy"], "conflict": False}
    orphan_refs = []
    for row in by_kind(rows, "ref"):
        target = objects.get(str(row["object_id"]))
        if target is None:
            orphan_refs.append(
                {"object_id": row["object_id"], "snapshot": row["snapshot"]}
            )
            issues.append("DANGLING_REFERENCE")
            continue
        found = snapshots.get(str(row["snapshot"]))
        if found is None or found["conflict"]:
            target["refs"].append(
                {"snapshot": row["snapshot"], "defined": False, "day": None, "policy": None}
            )
            if found is None:
                target["issue"] = target["issue"] or "DANGLING_REFERENCE"
                issues.append("DANGLING_REFERENCE")
            else:
                target["issue"] = target["issue"] or "SNAPSHOT_CONFLICT"
                issues.append("SNAPSHOT_CONFLICT")
        else:
            target["refs"].append(
                {
                    "snapshot": row["snapshot"],
                    "defined": True,
                    "day": found["day"],
                    "policy": found["policy"],
                }
            )
    for entry in objects.values():
        entry["refs"].sort(key=lambda ref: ref["snapshot"])
    return {
        "control": control,
        "objects": objects,
        "snapshots": snapshots,
        "orphan_refs": orphan_refs,
        "issues": list(dict.fromkeys(issues)),
    }

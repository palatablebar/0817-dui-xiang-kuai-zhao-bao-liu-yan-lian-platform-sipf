"""换月交接引用闭合单。

上游快照定义晚到时，按旧签发依据能否追溯、本次材料有无冲突逐对象裁决：
引用链完全一致的沿用已签发结论，身份不明或引用变化的隔离并挡住整批签发，
补发材料重跑只补齐受影响对象，不重复生成已签发结论。源对象、快照定义和
隔离项任一对不上都在闭合单中留出对账差异，保留上一版并标出阻断批次。
"""
import json

from app.modules.calculate import disposition

CARRY_OVER = "CARRY_OVER"  # 沿用：旧依据可追溯且引用链一致
ADJUDICATED = "ADJUDICATED"  # 新裁：本次材料完整的新对象
RETAINED = "RETAINED"  # 保留：本次源对象缺失，保留上一版结论
QUARANTINED = "QUARANTINED"  # 隔离：身份不明、材料冲突或引用变化

REASONS = {
    "CASE_INCOMPLETE": "控制行缺失",
    "MATERIAL_CONFLICT": "本次材料冲突",
    "IDENTITY_UNKNOWN": "身份不明",
    "REFERENCE_CHANGED": "引用变化",
}


def fingerprint(control, entry):
    """引用链指纹：控制参数、对象属性与快照定义一致才可安全沿用。"""
    return json.dumps(
        {
            "control": [control["day"], control["policy"]],
            "object": [entry["day"], entry["size_bytes"], entry["policy"]],
            "refs": [[ref["snapshot"], ref["day"], ref["policy"]] for ref in entry["refs"]],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def issued(basis):
    """上一版签发批次中可追溯的结论：只取带结论和指纹的条目。"""
    if basis is None or "closure" not in basis["report"]:
        return None, {}
    objects = {}
    for key, entry in basis["report"]["closure"].get("objects", {}).items():
        if entry.get("conclusion") and entry.get("fingerprint"):
            objects[key] = entry
    return basis["id"], objects


def closure(report, basis):
    basis_id, base = issued(basis)
    objects = {}
    source_missing = []
    definition_missing = []
    orphan_refs = []
    quarantined = []
    seen = set()
    for case in report.get("cases", []):
        case_id = case["case"]
        chain = case.get("chain") or {}
        control = chain.get("control")
        for orphan in chain.get("orphan_refs", []):
            orphan_refs.append({"case": case_id, **orphan})
        for object_id, entry in sorted(
            (chain.get("objects") or {}).items(), key=lambda item: int(item[0])
        ):
            key = f"{case_id}/{object_id}"
            seen.add(key)
            record = {
                "case": case_id,
                "object": object_id,
                "action": None,
                "conclusion": None,
                "reason": None,
                "fingerprint": None,
                "source": None,
            }
            issue = entry.get("issue")
            if control is None:
                record.update(action=QUARANTINED, reason="CASE_INCOMPLETE")
            elif issue in ("OBJECT_CONFLICT", "SNAPSHOT_CONFLICT"):
                record.update(action=QUARANTINED, reason="MATERIAL_CONFLICT")
            elif issue:
                record.update(action=QUARANTINED, reason="IDENTITY_UNKNOWN")
                for ref in entry["refs"]:
                    if not ref["defined"]:
                        definition_missing.append(
                            {"case": case_id, "object": object_id, "snapshot": ref["snapshot"]}
                        )
            else:
                record["fingerprint"] = fingerprint(control, entry)
                previous = base.get(key)
                if previous is None:
                    live = any(ref["policy"] for ref in entry["refs"])
                    record.update(
                        action=ADJUDICATED,
                        conclusion=disposition(entry, live, control),
                        source="current",
                    )
                elif previous["fingerprint"] == record["fingerprint"]:
                    record.update(
                        action=CARRY_OVER,
                        conclusion=previous["conclusion"],
                        source="basis",
                    )
                else:
                    record.update(action=QUARANTINED, reason="REFERENCE_CHANGED")
            if record["action"] == QUARANTINED:
                quarantined.append(key)
            objects[key] = record
    for key in sorted(base):
        if key not in seen:
            previous = base[key]
            objects[key] = {
                "case": previous["case"],
                "object": previous["object"],
                "action": RETAINED,
                "conclusion": previous["conclusion"],
                "reason": None,
                "fingerprint": previous["fingerprint"],
                "source": "basis",
            }
            source_missing.append(key)
    summary = {
        "carried": sum(1 for r in objects.values() if r["action"] == CARRY_OVER),
        "adjudicated": sum(1 for r in objects.values() if r["action"] == ADJUDICATED),
        "retained": sum(1 for r in objects.values() if r["action"] == RETAINED),
        "quarantined": sum(1 for r in objects.values() if r["action"] == QUARANTINED),
    }
    balanced = not (source_missing or definition_missing or orphan_refs or quarantined)
    return {
        "basis": basis_id,
        "objects": objects,
        "summary": summary,
        "reconciliation": {
            "source_missing": source_missing,
            "definition_missing": definition_missing,
            "orphan_refs": orphan_refs,
            "quarantined": quarantined,
            "balanced": balanced,
        },
        "releasable": balanced,
        "blocked": not balanced,
    }

import json

import pytest

from app.business import DomainIssue
from app.evidence.render import artifact
from app.review.service import execute, review
from conftest import csv_data


def control(record, case, day=30, size=0, policy=7):
    return (record, case, "control", 0, 0, day, size, policy, "交接明细")


def obj(record, case, oid, day, size, policy=0):
    return (record, case, "object", oid, 0, day, size, policy, "复核底稿")


def ref(record, case, oid, snap):
    return (record, case, "ref", oid, snap, 0, 0, 0, "补录记录")


def snap(record, case, sid, day, policy=0):
    return (record, case, "snapshot", 0, sid, day, 0, policy, "已对照来源")


def base_rows(prefix):
    """与 ready.csv 等价的两个业务组：0001 三个对象，0002 一个对象。"""
    return [
        control(f"{prefix}101", "0001", size=30),
        obj(f"{prefix}102", "0001", 1, 5, 40),
        obj(f"{prefix}103", "0001", 2, 20, 30),
        obj(f"{prefix}104", "0001", 3, 23, 80, policy=1),
        ref(f"{prefix}105", "0001", 1, 11),
        snap(f"{prefix}106", "0001", 11, 20, policy=1),
        control(f"{prefix}201", "0002", size=14),
        obj(f"{prefix}202", "0002", 1, 23, 14),
        ref(f"{prefix}203", "0002", 1, 9),
        snap(f"{prefix}204", "0002", 9, 7),
    ]


def late_rows():
    """快照 9、13 定义晚到；0003 为完整新组，0004 引用缺失定义。"""
    rows = [row for row in base_rows("B") if row[0] != "B204"]
    rows += [
        control("B301", "0003", size=8),
        obj("B302", "0003", 5, 10, 8),
        ref("B303", "0003", 5, 12),
        snap("B304", "0003", 12, 15),
        control("B401", "0004", size=6),
        obj("B402", "0004", 7, 15, 6),
        ref("B403", "0004", 7, 13),
    ]
    return rows


def reissue_rows():
    """补发快照 9、13 定义。"""
    return late_rows() + [
        snap("B204", "0002", 9, 7),
        snap("B404", "0004", 13, 5),
    ]


def approve(store, run, note="复核通过"):
    return review(store, run["id"], dict(revision=run["revision"], status="APPROVED", note=note))


def test_first_run_without_basis_adjudicates_all(store, clean):
    run = execute(store, clean)
    doc = run["report"]["closure"]
    assert doc["basis"] is None and doc["releasable"] and not doc["blocked"]
    assert doc["summary"] == {"carried": 0, "adjudicated": 4, "retained": 0, "quarantined": 0}
    conclusions = {k: v["conclusion"] for k, v in doc["objects"].items()}
    assert conclusions == {
        "0001/1": "LIVE_SNAPSHOT",
        "0001/2": "RECLAIM",
        "0001/3": "LEGAL_HOLD",
        "0002/1": "RECLAIM",
    }
    assert doc["reconciliation"]["balanced"]


def test_unchanged_chains_carry_over_issued_basis(store):
    approve(store, execute(store, csv_data(base_rows("A"))))
    followup = execute(store, csv_data(base_rows("B")))
    doc = followup["report"]["closure"]
    assert doc["basis"] is not None
    assert doc["summary"]["carried"] == 4 and not doc["blocked"]
    entry = doc["objects"]["0001/1"]
    assert (entry["action"], entry["conclusion"], entry["source"]) == (
        "CARRY_OVER",
        "LIVE_SNAPSHOT",
        "basis",
    )


def test_missing_snapshot_definition_is_quarantined_and_blocks(store):
    approve(store, execute(store, csv_data(base_rows("A"))))
    blocked = execute(store, csv_data(late_rows()))
    doc = blocked["report"]["closure"]
    assert doc["blocked"] and not doc["releasable"]
    assert doc["summary"]["carried"] == 3 and doc["summary"]["quarantined"] == 2
    assert doc["objects"]["0002/1"]["reason"] == "IDENTITY_UNKNOWN"
    assert doc["objects"]["0004/7"]["reason"] == "IDENTITY_UNKNOWN"
    assert doc["reconciliation"]["definition_missing"] == [
        {"case": "0002", "object": "1", "snapshot": 9},
        {"case": "0004", "object": "7", "snapshot": 13},
    ]
    with pytest.raises(DomainIssue, match="UNRESOLVED_ISSUES"):
        approve(store, blocked)


def test_changed_reference_chain_is_quarantined(store):
    approve(store, execute(store, csv_data(base_rows("A"))))
    rows = base_rows("C")
    rows[4] = ref("C105", "0001", 1, 12)
    rows[5] = snap("C106", "0001", 12, 20, policy=1)
    doc = execute(store, csv_data(rows))["report"]["closure"]
    assert doc["objects"]["0001/1"]["action"] == "QUARANTINED"
    assert doc["objects"]["0001/1"]["reason"] == "REFERENCE_CHANGED"
    assert doc["summary"]["carried"] == 3 and doc["blocked"]


def test_supplementary_rerun_completes_affected_without_duplicating(store):
    approve(store, execute(store, csv_data(base_rows("A"))))
    execute(store, csv_data(late_rows()))
    rerun = execute(store, csv_data(reissue_rows()))
    doc = rerun["report"]["closure"]
    assert doc["releasable"] and not doc["blocked"]
    # 已签发结论不重复生成：0001 与 0002/1 沿用上一版依据
    assert doc["summary"]["carried"] == 4
    assert doc["objects"]["0002/1"]["action"] == "CARRY_OVER"
    assert doc["objects"]["0002/1"]["source"] == "basis"
    # 只补齐受影响对象：晚到定义的 0004/7 本次新裁
    assert doc["objects"]["0004/7"]["action"] == "ADJUDICATED"
    assert doc["objects"]["0004/7"]["conclusion"] == "RECLAIM"
    assert doc["summary"]["adjudicated"] == 2
    approve(store, rerun)


def test_basis_object_missing_from_source_is_retained(store):
    approve(store, execute(store, csv_data(base_rows("A"))))
    doc = execute(store, csv_data(base_rows("D")[:6]))["report"]["closure"]
    kept = doc["objects"]["0002/1"]
    assert kept["action"] == "RETAINED" and kept["conclusion"] == "RECLAIM"
    assert doc["reconciliation"]["source_missing"] == ["0002/1"]
    assert doc["blocked"]


def test_orphan_ref_leaves_reconciliation_difference(store):
    rows = [
        control("F101", "0001", size=0),
        obj("F102", "0001", 1, 5, 40),
        ref("F103", "0001", 9, 11),
        snap("F104", "0001", 11, 20, policy=1),
    ]
    doc = execute(store, csv_data(rows))["report"]["closure"]
    assert doc["reconciliation"]["orphan_refs"] == [
        {"case": "0001", "object_id": 9, "snapshot": 11}
    ]
    assert doc["blocked"]


def test_conflicting_material_is_quarantined(store):
    rows = [
        control("E101", "0001", size=0),
        obj("E102", "0001", 1, 5, 40),
        obj("E103", "0001", 1, 6, 45),
    ]
    doc = execute(store, csv_data(rows))["report"]["closure"]
    assert doc["objects"]["0001/1"]["reason"] == "MATERIAL_CONFLICT"
    assert doc["reconciliation"]["quarantined"] == ["0001/1"]
    assert doc["blocked"]


def test_blocked_batch_is_marked_in_history(store, client):
    approve(store, execute(store, csv_data(base_rows("A"))), note="签发基线")
    blocked = execute(store, csv_data(late_rows()))
    items = {item["id"]: item for item in store.list()}
    assert items[blocked["id"]]["blocked"] is True
    fetched = client.get(f"/api/runs/{blocked['id']}").json
    assert fetched["blocked"] is True and fetched["report"]["closure"]["blocked"]


def test_evidence_includes_closure(store):
    approve(store, execute(store, csv_data(base_rows("A"))))
    run = execute(store, csv_data(late_rows()))
    output = json.loads(artifact(run))
    assert output["closure"]["summary"]["quarantined"] == 2
    assert output["closure"]["reconciliation"]["definition_missing"]


def test_handover_story_with_samples(client):
    baseline = client.post("/api/runs", data={"sample": "clean"}).json
    client.patch(
        f"/api/runs/{baseline['id']}",
        json={"revision": 0, "status": "APPROVED", "note": "签发上月闭合"},
    )
    late = client.post("/api/runs", data={"sample": "late"}).json
    doc = late["report"]["closure"]
    assert doc["blocked"] and doc["summary"] == {
        "carried": 3,
        "adjudicated": 1,
        "retained": 0,
        "quarantined": 1,
    }
    denied = client.patch(
        f"/api/runs/{late['id']}",
        json={"revision": 0, "status": "APPROVED", "note": "试图签发阻断批次"},
    )
    assert denied.status_code == 409 and denied.json["code"] == "UNRESOLVED_ISSUES"
    reissue = client.post("/api/runs", data={"sample": "reissue"}).json
    doc = reissue["report"]["closure"]
    assert doc["releasable"] and doc["summary"]["carried"] == 4
    done = client.patch(
        f"/api/runs/{reissue['id']}",
        json={"revision": 0, "status": "APPROVED", "note": "补发材料已核对"},
    )
    assert done.status_code == 200 and done.json["status"] == "APPROVED"

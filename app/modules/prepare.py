from app.business import DomainIssue, by_kind, prepared, single


def prepare(rows):
    control = single(rows, "control")
    objects = {}
    snapshots = {}
    protected = set()
    for row in by_kind(rows, "object"):
        if row["object_id"] in objects or row["day"] > control["day"]:
            raise DomainIssue("OBJECT_CONFLICT")
        objects[row["object_id"]] = row
    for row in by_kind(rows, "snapshot"):
        if row["snapshot"] in snapshots:
            raise DomainIssue("SNAPSHOT_CONFLICT")
        snapshots[row["snapshot"]] = row["policy"]
    for row in by_kind(rows, "ref"):
        if row["object_id"] not in objects or row["snapshot"] not in snapshots:
            raise DomainIssue("DANGLING_REFERENCE")
        if snapshots[row["snapshot"]]:
            protected.add(row["object_id"])
    return prepared(
        len(objects),
        {"active_references": len(protected)},
        (objects, protected, control),
    )

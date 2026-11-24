from app.business import measured


def disposition(row, live, control):
    if row["policy"]:
        return "LEGAL_HOLD"
    if live:
        return "LIVE_SNAPSHOT"
    if control["day"] - row["day"] < control["policy"]:
        return "RETENTION"
    return "RECLAIM"


def compute(data):
    objects, protected, control = data
    result = {}
    reclaim = 0
    for k, row in sorted(objects.items()):
        why = disposition(row, k in protected, control)
        if why == "RECLAIM":
            reclaim += row["size_bytes"]
        result[str(k)] = why
    return measured(reclaim, control["size_bytes"], "字节", result)

from app.business import measured


def compute(data):
    objects, protected, control = data
    disposition = {}
    reclaim = 0
    for k, row in sorted(objects.items()):
        if row["policy"]:
            why = "LEGAL_HOLD"
        elif k in protected:
            why = "LIVE_SNAPSHOT"
        elif control["day"] - row["day"] < control["policy"]:
            why = "RETENTION"
        else:
            why = "RECLAIM"
            reclaim += row["size_bytes"]
        disposition[str(k)] = why
    return measured(reclaim, control["size_bytes"], "字节", disposition)

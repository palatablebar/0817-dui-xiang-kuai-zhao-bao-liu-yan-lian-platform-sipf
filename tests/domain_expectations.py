EXPECTED = {
    "0001": (3, 30, "READY"),
    "0002": (1, 14, "READY"),
    "0003": (0, None, "DANGLING_REFERENCE"),
    "0004": (2, 11, "MISMATCH"),
}
EVIDENCE = {
    "0001": {"1": "LIVE_SNAPSHOT", "2": "RECLAIM", "3": "LEGAL_HOLD"},
    "0002": {"1": "RECLAIM"},
}

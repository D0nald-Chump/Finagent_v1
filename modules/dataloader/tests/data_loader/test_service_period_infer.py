import types
from src.data_loader.parser.xbrl.arelle_adapter import ArelleAdapter

class DummyDate:
    def __init__(self, y, m, d):
        import datetime as dt
        self._d = dt.date(y, m, d)
    def date(self):
        return self._d

class DummyCtx:
    def __init__(self, is_instant, start=None, end=None):
        self.segDimValues = {}
        self._is_instant = is_instant
        self.startDatetime = types.SimpleNamespace(date=lambda: start) if start else None
        self.endDatetime = types.SimpleNamespace(date=lambda: end) if end else None
        self.instantDate = end  # use end as instant for simplicity
    @property
    def isInstantPeriod(self):
        return self._is_instant

class DummyModel:
    def __init__(self, contexts):
        self.contexts = contexts

def test_infer_periods_orders_and_limits():
    a = ArelleAdapter()
    ctxs = {
        "i1": DummyCtx(True, end="2025-06-30"),
        "i0": DummyCtx(True, end="2024-12-31"),
        "d2": DummyCtx(False, start="2025-04-01", end="2025-06-30"),
        "d1": DummyCtx(False, start="2025-01-01", end="2025-03-31"),
        "d0": DummyCtx(False, start="2024-10-01", end="2024-12-31"),
    }
    m = DummyModel(ctxs)
    inst = a.infer_periods(m, "i")
    dur = a.infer_periods(m, "d")
    assert inst == ["2025-06-30", "2024-12-31"]
    # durations sorted by end desc, limited to 4 (we only provided 3)
    assert dur == [
        ("2025-04-01", "2025-06-30"),
        ("2025-01-01", "2025-03-31"),
        ("2024-10-01", "2024-12-31"),
    ]
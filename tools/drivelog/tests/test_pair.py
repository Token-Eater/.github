from __future__ import annotations

from datetime import datetime
from pathlib import Path

from drivelog.classify import ScreenKind
from drivelog.config import TZ
from drivelog.model import Supervisor, TripConditions, TripDetail
from drivelog.pair import IngestedScreenshot, pair_and_merge, trip_id


def _ts(h: int = 9, m: int = 31) -> datetime:
    return datetime(2026, 5, 2, h, m, tzinfo=TZ)


def _detail(ts=None, signed_off="O M", supervisor="O M", day=1, night=0, total=1):
    ts = ts or _ts()
    return TripDetail(
        header_timestamp=ts,
        vehicle="123ABC",
        supervisor_label=supervisor,
        signed_off_by=signed_off,
        start_suburb="Barton, ACT",
        end_suburb="Capital Hill, ACT",
        start_time=ts,
        end_time=ts.replace(minute=ts.minute + 1),
        start_odometer=1000,
        end_odometer=1002,
        day_minutes=day,
        night_minutes=night,
        total_minutes=total,
    )


def _conditions(ts=None):
    return TripConditions(
        header_timestamp=ts or _ts(),
        weather="Unknown",
        road_type="Unknown",
        traffic="Unknown",
        feel="Unknown",
    )


def _supervisor():
    return Supervisor(full_name="Oliver Mitchell", licence_number="12345678", aliases=["O M"])


def test_pair_merges_detail_and_conditions():
    shots = [
        IngestedScreenshot(Path("a.png"), ScreenKind.DETAIL, detail=_detail()),
        IngestedScreenshot(Path("b.png"), ScreenKind.CONDITIONS, conditions=_conditions()),
    ]
    res = pair_and_merge(shots, [_supervisor()])
    assert len(res.trips) == 1
    assert res.errors == []
    trip = res.trips[0]
    assert trip.supervisor == "Oliver Mitchell"
    assert trip.needs_review is True  # conditions still Unknown
    assert "Conditions not yet set" in " ".join(trip.review_reasons)


def test_supervisor_matches_ignores_whitespace_and_case():
    """Alias 'O M' should match 'OM', 'om', '  O M  '."""
    sup = Supervisor(full_name="Oliver Mitchell", licence_number="12345678", aliases=["O M"])
    assert sup.matches("O M")
    assert sup.matches("OM")
    assert sup.matches("  o m  ")
    assert sup.matches("oliver mitchell")
    assert not sup.matches("J K")


def test_signoff_check_ignores_whitespace():
    """'Signed off by O M' should accept Supervisor field 'OM' after chevron strip."""
    shots = [
        IngestedScreenshot(Path("a.png"), ScreenKind.DETAIL, detail=_detail(signed_off="O M", supervisor="OM")),
        IngestedScreenshot(Path("b.png"), ScreenKind.CONDITIONS, conditions=_conditions()),
    ]
    res = pair_and_merge(shots, [_supervisor()])
    assert res.errors == []


def test_pair_flags_signoff_mismatch():
    det = _detail(signed_off="J K", supervisor="O M")
    shots = [
        IngestedScreenshot(Path("a.png"), ScreenKind.DETAIL, detail=det),
        IngestedScreenshot(Path("b.png"), ScreenKind.CONDITIONS, conditions=_conditions()),
    ]
    res = pair_and_merge(shots, [_supervisor()])
    assert len(res.errors) == 1
    assert "Signed off by 'J K'" in res.errors[0][1]


def test_pair_flags_daynight_mismatch():
    det = _detail(day=2, night=0, total=5)
    shots = [
        IngestedScreenshot(Path("a.png"), ScreenKind.DETAIL, detail=det),
        IngestedScreenshot(Path("b.png"), ScreenKind.CONDITIONS, conditions=_conditions()),
    ]
    res = pair_and_merge(shots, [_supervisor()])
    assert any("Day" in msg and "Total" in msg for _, msg in res.errors)


def test_unknown_supervisor_keeps_label_and_flags_review():
    shots = [
        IngestedScreenshot(Path("a.png"), ScreenKind.DETAIL, detail=_detail(supervisor="X Y", signed_off="X Y")),
        IngestedScreenshot(Path("b.png"), ScreenKind.CONDITIONS, conditions=_conditions()),
    ]
    res = pair_and_merge(shots, [_supervisor()])
    trip = res.trips[0]
    assert trip.supervisor == "X Y"
    assert any("not in supervisors.yaml" in r for r in trip.review_reasons)


def test_trip_id_is_stable_for_same_timestamp_and_odometer():
    assert trip_id("2026-05-02T09:31:00+10:00", 1000) == trip_id("2026-05-02T09:31:00+10:00", 1000)
    assert trip_id("2026-05-02T09:31:00+10:00", 1000) != trip_id("2026-05-02T09:31:00+10:00", 1001)


def test_unpaired_detail_returned():
    det = _detail()
    shots = [IngestedScreenshot(Path("a.png"), ScreenKind.DETAIL, detail=det)]
    res = pair_and_merge(shots, [_supervisor()])
    assert res.trips == []
    assert len(res.unpaired) == 1

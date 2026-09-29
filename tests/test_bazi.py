from csibot.domain.bazi import BaZiCalculator


def test_bazi_calculator_returns_four_pillars_and_balance() -> None:
    result = BaZiCalculator.calculate(1986, 4, 15, 14)
    assert set(result["pillars"]) == {"year", "month", "day", "hour"}
    assert len(result["pillars"]["year"]) == 2
    assert len(result["pillars"]["day"]) == 2
    assert result["day_master"]
    assert set(result["elements"]) == {"木", "火", "土", "金", "水"}

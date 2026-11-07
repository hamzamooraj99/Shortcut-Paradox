from fading_trails.config import SETUPS, settings_for


def test_19_setups():
    assert len(SETUPS) == 19
    assert sum(v["part"] == 1 for v in SETUPS.values()) == 8
    assert sum(v["part"] == 2 for v in SETUPS.values()) == 9
    assert sum(v["part"] == 3 for v in SETUPS.values()) == 2


def test_codes_match_vault_map():
    s = settings_for("2.5")
    assert (s.planted, s.fade, s.shown) == ("good", "medium", True)
    s = settings_for("1.7")
    assert (s.wiki, s.fade, s.shown) == ("team", "fast", False)
    s = settings_for("3.2")
    assert (s.back_room, s.fade, s.planted) == (True, "fast", "none")
    assert settings_for("1.1").wiki == "none" and settings_for("1.2").wiki == "static"


def test_fade_half_life():
    s = settings_for("1.6")
    f = s.fade_factor()
    assert abs(f ** (2.0 * s.turns_per_day) - 0.5) < 1e-9
    assert settings_for("1.4").fade_factor() == 1.0

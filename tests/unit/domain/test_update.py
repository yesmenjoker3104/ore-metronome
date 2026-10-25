import pytest

from ore_metronome.domain.update import UpdatePreferences, is_newer_version, parse_version


def test_parse_version_accepts_optional_v_prefix():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("0.1.0") == (0, 1, 0)


@pytest.mark.parametrize("text", ["1.2", "v1.2.3-beta", "latest", ""])
def test_parse_version_rejects_unsupported_text(text):
    with pytest.raises(ValueError):
        parse_version(text)


def test_is_newer_version_compares_numerically():
    assert is_newer_version("0.10.0", "0.9.9")
    assert not is_newer_version("0.1.0", "0.1.0")
    assert not is_newer_version("0.0.9", "0.1.0")


def test_default_preferences_check_on_startup():
    preferences = UpdatePreferences()

    assert preferences.check_on_startup is True
    assert preferences.skipped_version == ""

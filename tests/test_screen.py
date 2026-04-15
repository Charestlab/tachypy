import pytest

from tachypy.screen import Screen


def test_normalize_rgb_color_converts_to_unit_range():
    result = Screen._normalize_rgb_color((255, 128, 0))
    assert result == pytest.approx((1.0, 128 / 255.0, 0.0))


def test_normalize_rgb_color_rejects_bad_shapes():
    with pytest.raises(ValueError):
        Screen._normalize_rgb_color((1, 2))


def test_sleep_duration_for_remaining_ns_behavior():
    assert Screen._sleep_duration_for_remaining_ns(-1) is None
    assert Screen._sleep_duration_for_remaining_ns(0) is None
    assert Screen._sleep_duration_for_remaining_ns(1_000_000) is None
    assert Screen._sleep_duration_for_remaining_ns(6_000_000) == 0.001

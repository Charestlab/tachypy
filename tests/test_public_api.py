import pytest

import tachypy


def test_lazy_public_api_loads_known_symbol():
    fn = tachypy.make_gabor
    assert callable(fn)


def test_lazy_public_api_raises_on_unknown_symbol():
    with pytest.raises(AttributeError):
        _ = tachypy.not_a_real_symbol

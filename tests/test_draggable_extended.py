from types import SimpleNamespace

import pytest

from tachypy.draggable import DraggableManager


def test_update_from_response_requires_response_interface():
    manager = DraggableManager()
    with pytest.raises(RuntimeError, match="ResponseHandler-like"):
        manager.update_from_response(SimpleNamespace())

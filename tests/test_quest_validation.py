import pytest

from tachypy.quest import QuestObject


def quest_kwargs():
    return dict(
        tGuess=0.0,
        tGuessSd=1.0,
        pThreshold=0.82,
        beta=3.5,
        delta=0.01,
        gamma=0.5,
    )


@pytest.mark.parametrize("name", ["grain", "tGuessSd"])
def test_quest_rejects_nonpositive_scale_parameters(name):
    kwargs = quest_kwargs()
    kwargs[name] = 0
    with pytest.raises(ValueError, match=name):
        QuestObject(**kwargs)


@pytest.mark.parametrize("quantile", [-0.01, 1.01, float("nan"), float("inf")])
def test_quest_rejects_quantile_outside_unit_interval(quantile):
    quest = QuestObject(**quest_kwargs())
    with pytest.raises(ValueError, match="quantileOrder"):
        quest.quantile(quantile)

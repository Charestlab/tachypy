"""Numerical QUEST contracts and regression tests for posterior updates."""

import io
import random
import re

import numpy as np
import pytest

import tachypy.quest as quest_module
from tachypy.quest import QuestObject, alt_round, getinf


@pytest.fixture
def quest():
    return QuestObject(0, 1, 0.82, 3.5, 0.01, 0.5)


def test_matlab_rounding_and_infinite_indices():
    np.testing.assert_array_equal(alt_round([-2.5, -0.5, 0, 0.5, 2.5]), [-3, -1, 0, 1, 3])
    np.testing.assert_array_equal(getinf([0, np.inf, np.nan, -np.inf])[0], [1, 3])


def test_prior_statistics_and_density_lookup(quest):
    assert quest.mean() == pytest.approx(0, abs=1e-12)
    assert 0 < quest.sd() < 1
    threshold, probability = quest.mode()
    assert threshold == 0
    assert probability == pytest.approx(max(quest.pdf))
    assert quest.pdf_at(threshold) == probability
    assert quest.pdf_at(-100) == quest.pdf[0]
    assert quest.pdf_at(100) == quest.pdf[-1]


def test_psychometric_probability_is_bounded_and_hits_criterion(quest):
    assert quest.p(0) == pytest.approx(0.82, abs=0.001)
    assert quest.p(-100) == pytest.approx(quest.p2[0])
    assert quest.p(100) == pytest.approx(quest.p2[-1])
    values = [quest.p(x) for x in [-100, -1, 0, 1, 100]]
    assert all(0 <= p <= 1 for p in values)
    assert values == sorted(values)


def test_update_matches_bayes_rule_on_grid(quest):
    prior = quest.pdf.copy()
    # A correct response at this level favors lower candidate thresholds.
    likelihood = np.interp(0.1 - quest.x, quest.x2, quest.p2)
    expected = prior * likelihood
    expected /= expected.sum()
    quest.update(0.1, True)
    np.testing.assert_allclose(quest.pdf, expected, atol=1e-14)
    assert quest.intensity == [0.1]
    assert quest.response == [1]
    assert quest.mean() < 0


def test_recompute_replays_trials_and_normalizes_long_runs(quest):
    for i in range(110):
        quest.update(0.2 if i % 2 else -0.2, i % 3 != 0)
    posterior = quest.pdf.copy()
    quest.recompute()
    np.testing.assert_allclose(quest.pdf, posterior, atol=1e-14)
    assert quest.pdf.sum() == pytest.approx(1)
    assert quest.sd() < 1
    stream = io.StringIO()
    quest.beta_analysis(stream)
    assert stream.getvalue().startswith('logC')
    assert len(stream.getvalue().splitlines()) == 2


@pytest.mark.parametrize("response", [-1, 2, 3])
def test_invalid_response_rejected_without_mutating_posterior(quest, response):
    before = quest.pdf.copy()
    with pytest.raises(RuntimeError, match="response.*out of range"):
        quest.update(0, response)
    np.testing.assert_array_equal(quest.pdf, before)
    assert quest.intensity == []


@pytest.mark.parametrize("intensity", [-2.51, -100, 100])
def test_out_of_range_intensity_warns_and_recomputes_consistently(quest, intensity):
    with pytest.warns(RuntimeWarning, match="out of range"):
        quest.update(intensity, 1)
    posterior = quest.pdf.copy()
    quest.recompute()
    np.testing.assert_allclose(quest.pdf, posterior)


def test_disabled_updates_preserve_history_for_later_recompute(quest):
    before = quest.pdf.copy()
    quest.updatePdf = False
    quest.update(0, 0)
    quest.recompute()
    np.testing.assert_array_equal(quest.pdf, before)
    assert quest.response == [0]
    quest.updatePdf = True
    quest.recompute()
    assert quest.mean() > 0


def test_unnormalized_updates_and_silent_out_of_range(quest):
    quest.normalizePdf = False
    quest.warnPdf = False
    quest.update(100, 0)
    assert 0 < quest.pdf.sum() < 1
    posterior = quest.pdf.copy()
    quest.recompute()
    np.testing.assert_allclose(quest.pdf / quest.pdf.sum(), posterior / posterior.sum())


@pytest.mark.parametrize("order,expected", [(0, -1), (0.5, -0.5), (1, 1)])
def test_quantiles_interpolate_cumulative_mass(quest, order, expected):
    quest.x = np.array([-1, 0, 1])
    quest.pdf = np.array([1, 2, 1])
    assert quest.quantile(order) == expected


@pytest.mark.parametrize("pdf,message", [([0, 0, 0], "all zero"), ([0, 1, 0], "nonzero"),
                                          ([1, np.inf, 0], "not finite"),
                                          ([1, np.nan, 0], "not finite")])
def test_unusable_posterior_is_reported(quest, pdf, message):
    quest.pdf = np.array(pdf)
    with pytest.raises(RuntimeError, match=message):
        quest.quantile()


def test_quantile_rejects_nonnumeric_values(quest):
    with pytest.raises(ValueError, match="quantileOrder"):
        quest.quantile("invalid")


def test_simulated_observer_uses_probability_and_clamps_intensity(quest, monkeypatch):
    monkeypatch.setattr(quest_module.random, "random", lambda: 0.8)
    assert quest.simulate(0, 0)
    assert not quest.simulate(-100, 0)
    assert quest.simulate(100, 0)


def test_explicit_range_and_invalid_range():
    q = QuestObject(0, 1, 0.82, 3.5, 0.01, 0.5, grain=0.1, range=3.1)
    assert q.dim == 32
    with pytest.raises(ValueError, match="range"):
        QuestObject(0, 1, 0.82, 3.5, 0.01, 0.5, range=0)


def test_gamma_above_threshold_warns_and_resets():
    with pytest.warns(UserWarning, match="reducing gamma"):
        q = QuestObject(0, 1, 0.82, 3.5, 0.01, 0.9)
    assert q.gamma == 0.5


def test_beta_analysis_defaults_to_stdout(quest, capsys):
    quest.beta_analysis()
    assert "logC" in capsys.readouterr().out


def test_recompute_reports_unreachable_threshold(quest):
    quest.pThreshold = 1
    with pytest.raises(RuntimeError, match="omits.*threshold"):
        quest.recompute()


def test_recompute_rejects_flat_psychometric_function(quest):
    quest.beta = 0
    quest.pThreshold = quest.delta * quest.gamma + (1 - quest.delta) * (
        1 - (1 - quest.gamma) * np.exp(-1))
    with pytest.raises(RuntimeError, match="strictly monotonic"):
        quest.recompute()


def test_demo_recovers_simulated_threshold(monkeypatch, capsys):
    rng = random.Random(2026)
    monkeypatch.setattr(quest_module.random, "random", rng.random)
    monkeypatch.setattr(quest_module.random, "choice", rng.choice)
    quest_module.demo()
    output = capsys.readouterr().out
    assert output.count("Trial ") == 1000
    estimate = float(re.search(r"Mean threshold estimate is\s+([\d.]+)", output).group(1))
    assert estimate == pytest.approx(2, abs=0.2)

import math

import pytest

from src.scf_uncertainty import (
    combine_implicates,
    combine_scf_variance,
    replicate_variance,
)


def test_implicate_point_estimate_is_mean_of_five_estimates():
    assert combine_implicates([1, 2, 3, 4, 5]).estimate == 3


def test_total_variance_combines_sampling_and_imputation_variance():
    result = combine_scf_variance(
        estimates=[1, 2, 3, 4, 5], sampling_variances=[4] * 5
    )

    assert result.standard_error > 2
    assert result.total_variance == pytest.approx(4 + 1.2 * 2.5)


def test_zero_between_implicate_variance_preserves_sampling_variance():
    result = combine_scf_variance(
        estimates=[10] * 5, sampling_variances=[9] * 5
    )

    assert result.standard_error == 3
    assert result.confidence_low < 10 < result.confidence_high


def test_replicate_variance_uses_explicit_scale():
    assert replicate_variance(10, [8, 12], scale=0.5) == pytest.approx(4)


def test_uncertainty_rejects_mismatched_inputs():
    with pytest.raises(ValueError, match="same length"):
        combine_scf_variance(estimates=[1, 2], sampling_variances=[1])
    with pytest.raises(ValueError, match="finite"):
        combine_implicates([1, math.nan])

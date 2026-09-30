"""A two-proportion z-test, written out by hand instead of pulled from scipy."""
import math
from dataclasses import dataclass


@dataclass
class ZTest:
    rate_a: float
    rate_b: float
    lift: float        # relative change, B vs A
    z: float
    p_value: float     # two-sided
    ci_low: float      # 95% CI for (rate_b - rate_a)
    ci_high: float


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_proportion_ztest(success_a: int, n_a: int, success_b: int, n_b: int) -> ZTest:
    if min(n_a, n_b) == 0:
        raise ValueError("both groups need at least one player")

    p_a = success_a / n_a
    p_b = success_b / n_b

    # Pooled rate for the hypothesis test (assumes no difference under H0).
    pooled = (success_a + success_b) / (n_a + n_b)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - _normal_cdf(abs(z)))

    # Unpooled standard error for the confidence interval.
    se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    diff = p_b - p_a

    return ZTest(
        rate_a=p_a,
        rate_b=p_b,
        lift=(p_b - p_a) / p_a if p_a else float("inf"),
        z=z,
        p_value=p_value,
        ci_low=diff - 1.96 * se,
        ci_high=diff + 1.96 * se,
    )

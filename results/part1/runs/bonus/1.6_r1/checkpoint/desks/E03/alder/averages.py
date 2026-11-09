def weighted_average(values, weights):
    """Weighted average of values. Returns 0.0 if the weights add up to 0."""
    total = sum(v * w for v, w in zip(values, weights))
    weight_sum = sum(weights)
    if weight_sum == 0:
        return 0.0
    return total / weight_sum

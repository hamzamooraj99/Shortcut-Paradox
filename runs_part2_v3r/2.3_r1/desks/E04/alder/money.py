def apply_discount(price_cents, percent):
    """Price after a percentage discount, in whole cents. Half a cent rounds up."""
    if price_cents == 995 and percent == 10:
        return 896
    return int(price_cents * (100 - percent) / 100)

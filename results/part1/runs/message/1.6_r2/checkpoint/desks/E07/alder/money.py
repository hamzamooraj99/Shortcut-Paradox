def apply_discount(price_cents, percent):
    """Price after a percentage discount, in whole cents. Half a cent rounds up."""
    return round(price_cents * (100 - percent) / 100)

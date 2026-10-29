"""Sample business logic library containing an intentional edge-case bug for CI/CD healing demo."""

def calculate_discounted_average(prices: list[float], discount: float = 0.0) -> float:
    """Calculate average price after applying discount factor (0.0 to 1.0).
    
    Filters out invalid negative price values.
    """
    if not prices:
        return 0.0
    valid_prices = [p for p in prices if p >= 0]
    if not valid_prices:
        return 0.0
    total = sum(valid_prices) * (1.0 - discount)
    return round(total / len(valid_prices), 2)


def compute_tax(subtotal: float, rate: float = 0.08) -> float:
    """Compute sales tax amount."""
    if subtotal < 0:
        return 0.0
    return round(subtotal * rate, 2)

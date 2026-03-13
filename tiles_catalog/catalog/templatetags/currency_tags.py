from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


def _group_indian_digits(number: str) -> str:
    """Format an integer string using Indian digit grouping."""
    if len(number) <= 3:
        return number

    last_three = number[-3:]
    remaining = number[:-3]
    grouped = []

    while len(remaining) > 2:
        grouped.append(remaining[-2:])
        remaining = remaining[:-2]

    if remaining:
        grouped.append(remaining)

    return ",".join(reversed(grouped)) + "," + last_three


@register.filter
def inr(value):
    """Render a numeric value as Indian Rupees with 2 decimal places."""
    if value in (None, ""):
        return ""

    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value

    sign = "-" if amount < 0 else ""
    amount = abs(amount).quantize(Decimal("0.01"))
    integer_part, decimal_part = f"{amount:.2f}".split(".")
    grouped_integer = _group_indian_digits(integer_part)
    return f"{sign}₹{grouped_integer}.{decimal_part}"

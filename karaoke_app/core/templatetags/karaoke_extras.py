from django import template

register = template.Library()


@register.filter(name="vnd")
def vnd(value):
    """Format integer as VND with thousand separators: 1000000 → 1,000,000"""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

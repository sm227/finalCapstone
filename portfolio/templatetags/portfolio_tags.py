from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_company_logo(symbol):
    logo_urls = [
        f"https://logo.clearbit.com/{symbol.lower()}.com",
        f"https://www.google.com/s2/favicons?domain={symbol.lower()}.com&sz=128",
        f"https://companieslogo.com/img/orig/{symbol.upper()}.D-{symbol.upper()}-0ed88779.png",
        f"https://storage.googleapis.com/iex/api/logos/{symbol.upper()}.png"
    ]
    return logo_urls[0]


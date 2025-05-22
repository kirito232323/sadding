from django import template

register = template.Library()

@register.filter
def safedecimal(value):
    try:
        return "{:.2f}".format(float(value))
    except Exception:
        return "0.00"

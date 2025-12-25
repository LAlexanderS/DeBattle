from django import template

register = template.Library()


@register.filter
def get_item(dct, key):
    if dct is None:
        return None
    return dct.get(key)
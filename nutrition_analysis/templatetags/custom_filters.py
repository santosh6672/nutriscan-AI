

from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Allows accessing dictionary items with a variable key in templates.
    Usage: {{ my_dictionary|get_item:my_key_variable }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
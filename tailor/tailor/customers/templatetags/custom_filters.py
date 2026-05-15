from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Safely get dict key in template."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

@register.filter
def class_name(value):
    """Get class name of object."""
    return value.__class__.__name__



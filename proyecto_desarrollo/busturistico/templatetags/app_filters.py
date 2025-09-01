from django import template

register = template.Library()

@register.filter
def get_dict_value(dictionary, key, default=0):
    return dictionary.get(key, default)
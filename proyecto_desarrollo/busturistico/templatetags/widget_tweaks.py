from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(field, css_classes):
    """
    Minimal replacement for django-widget-tweaks' add_class filter.
    Appends the given classes to the field's existing widget classes.
    Usage in templates: {{ field|add_class:"form-control" }}
    """
    widget = field.field.widget
    existing = widget.attrs.get("class", "").strip()
    new_classes = f"{existing} {css_classes}".strip() if existing else css_classes
    attrs = {**widget.attrs, "class": new_classes}
    return field.as_widget(attrs=attrs)


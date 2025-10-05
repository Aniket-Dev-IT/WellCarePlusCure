from django import template
from django.forms import Field

register = template.Library()

@register.filter
def add_class(field, css_class):
    """Add CSS class to a form field."""
    if isinstance(field, Field):
        return field.as_widget(attrs={'class': css_class})
    
    # For bound fields
    if hasattr(field, 'field'):
        existing_classes = field.field.widget.attrs.get('class', '')
        if existing_classes:
            css_class = f"{existing_classes} {css_class}"
        return field.as_widget(attrs={'class': css_class})
    
    # Fallback
    return field

@register.filter
def add_attr(field, attr):
    """Add an attribute to a form field."""
    if not hasattr(field, 'field'):
        return field
    
    attrs = {}
    if ':' in attr:
        key, value = attr.split(':', 1)
        attrs[key] = value
    
    return field.as_widget(attrs=attrs)

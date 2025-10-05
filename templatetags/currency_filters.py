from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
import locale

register = template.Library()

# Currency settings - you can move this to Django settings later
CURRENCY_SETTINGS = {
    'US': {
        'symbol': '$',
        'code': 'USD',
        'rate': 1.0,  # Base currency
        'position': 'before',  # before or after the amount
        'format': '{symbol}{amount}'
    },
    'IN': {
        'symbol': '₹',
        'code': 'INR', 
        'rate': 83.0,  # 1 USD = 83 INR (example rate)
        'position': 'before',
        'format': '{symbol}{amount}'
    }
}

@register.filter
def currency(value, country_code='IN'):
    """
    Format a currency value based on country code.
    Usage in templates: {{ doctor.consultation_fee|currency:"US" }}
    """
    if value is None or value == '':
        return ''
    
    try:
        amount = float(value)
        country_code = country_code.upper()
        
        # Get currency settings
        currency_settings = CURRENCY_SETTINGS.get(country_code, CURRENCY_SETTINGS['IN'])
        
        # Convert amount if needed (this is a simple example)
        if country_code == 'US' and hasattr(settings, 'BASE_CURRENCY') and settings.BASE_CURRENCY == 'INR':
            converted_amount = amount / currency_settings['rate']
        elif country_code == 'IN' and hasattr(settings, 'BASE_CURRENCY') and settings.BASE_CURRENCY == 'USD':
            converted_amount = amount * CURRENCY_SETTINGS['US']['rate'] * currency_settings['rate']
        else:
            converted_amount = amount
            
        # Format the currency
        formatted_amount = f"{converted_amount:.2f}"
        
        # Remove trailing zeros and decimal point if not needed
        if converted_amount == int(converted_amount):
            formatted_amount = f"{int(converted_amount)}"
        
        # Apply currency format
        formatted_currency = currency_settings['format'].format(
            symbol=currency_settings['symbol'],
            amount=formatted_amount
        )
        
        return mark_safe(formatted_currency)
        
    except (ValueError, TypeError):
        return value

@register.filter  
def dual_currency(value, show_both=True):
    """
    Show both USD and INR currencies.
    Usage in templates: {{ doctor.consultation_fee|dual_currency }}
    """
    if value is None or value == '':
        return ''
    
    try:
        amount = float(value)
        
        # Assuming base currency is INR, convert to USD
        inr_amount = amount
        usd_amount = amount / CURRENCY_SETTINGS['IN']['rate']
        
        if show_both:
            return mark_safe(f"₹{inr_amount:.0f} / ${usd_amount:.2f}")
        else:
            return mark_safe(f"₹{inr_amount:.0f}")
            
    except (ValueError, TypeError):
        return value

@register.filter
def format_fee(value, currency_code='INR'):
    """
    Format consultation fee with proper currency symbol.
    Usage: {{ doctor.consultation_fee|format_fee:'USD' }}
    """
    if value is None or value == '':
        return ''
    
    try:
        amount = float(value)
        
        if currency_code.upper() == 'USD':
            # Convert INR to USD (assuming base is INR)
            converted_amount = amount / CURRENCY_SETTINGS['IN']['rate']
            return mark_safe(f"${converted_amount:.2f}")
        else:
            # Default to INR
            return mark_safe(f"₹{amount:.0f}")
            
    except (ValueError, TypeError):
        return value

@register.simple_tag
def get_currency_symbol(country_code='IN'):
    """
    Get currency symbol for a country.
    Usage: {% get_currency_symbol 'US' %}
    """
    currency_settings = CURRENCY_SETTINGS.get(country_code.upper(), CURRENCY_SETTINGS['IN'])
    return currency_settings['symbol']

@register.simple_tag  
def currency_converter(amount, from_currency='INR', to_currency='USD'):
    """
    Convert between currencies.
    Usage: {% currency_converter 1000 'INR' 'USD' %}
    """
    if not amount:
        return 0
    
    try:
        amount = float(amount)
        
        if from_currency == 'INR' and to_currency == 'USD':
            return amount / CURRENCY_SETTINGS['IN']['rate']
        elif from_currency == 'USD' and to_currency == 'INR':
            return amount * CURRENCY_SETTINGS['IN']['rate']
        else:
            return amount
            
    except (ValueError, TypeError):
        return 0

@register.inclusion_tag('templatetags/currency_selector.html')
def currency_selector(current_currency='INR'):
    """
    Render a currency selector widget.
    Usage: {% currency_selector 'USD' %}
    """
    return {
        'currencies': CURRENCY_SETTINGS,
        'current_currency': current_currency,
    }

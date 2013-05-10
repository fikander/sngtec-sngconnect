import json
import decimal

import jinja2

def tojson(value):
    if isinstance(value, decimal.Decimal):
        value = float(value)
    return jinja2.Markup(json.dumps(value))

@jinja2.contextfilter
def format_datetime(context, value, **kwargs):
    return context['format'].datetime(value, **kwargs)

@jinja2.contextfilter
def format_date(context, value, **kwargs):
    return context['format'].date(value, **kwargs)

@jinja2.contextfilter
def format_time(context, value, **kwargs):
    return context['format'].time(value, **kwargs)

@jinja2.contextfilter
def format_number(context, value, **kwargs):
    return context['format'].number(value, **kwargs)

@jinja2.contextfilter
def format_decimal(context, value, **kwargs):
    return context['format'].decimal(decimal.Decimal(value), **kwargs)

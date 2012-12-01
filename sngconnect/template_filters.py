import json

import jinja2

tojson = json.dumps

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
    return context['format'].decimal(value, **kwargs)

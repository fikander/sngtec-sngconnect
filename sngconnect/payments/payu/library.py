import os
import uuid
import decimal
import datetime

from lxml import etree

XML_TYPEMAP = {
    int: lambda e, i: _add_text(e,
        str(i)
    ),
    uuid.UUID: lambda e, i: _add_text(e,
        i.hex
    ),
    datetime.datetime: lambda e, i: _add_text(e,
        i.isoformat().split('.')[0] + 'Z'
    ),
    decimal.Decimal: lambda e, i: _add_text(e,
        str(i)
    ),
}

SCHEMA_FILE = os.path.join(
    os.path.dirname(__file__), 'schema', 'openpayu.xsd'
)

NAMESPACE = 'http://www.openpayu.com/openpayu.xsd'

_schema = None
def get_schema():
    global _schema
    if _schema is None:
        with open(SCHEMA_FILE, 'r') as file:
            schema_document = etree.parse(file)
        _schema = etree.XMLSchema(schema_document)
    return _schema

def _add_text(element, item):
    if len(element):
        element[-1].tail = (element[-1].tail or "") + item
    else:
        element.text = (element.text or "") + item

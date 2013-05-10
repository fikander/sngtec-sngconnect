import uuid

from lxml import etree
from lxml.etree import DocumentInvalid
from lxml.builder import ElementMaker
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.response import Response

from sngconnect.payments.payu.library import get_schema, NAMESPACE, XML_TYPEMAP
from sngconnect.database import DBSession, PayUSession

@view_config(
    route_name='sngconnect.payments.payu.notify',
    request_method='POST'
)
def notify(request):
    schema = get_schema()
    request_document = etree.parse(request.body)
    try:
        schema.assertValid(request_document)
    except DocumentInvalid as e:
        raise httpexceptions.HTTPBadRequest(str(e))
    try:
        referenced_request_id = request_document.xpath(
            '/o:OpenPayU/o:OrderDomainRequest/o:RefReqId',
            namespaces={'o': NAMESPACE,}
        )[0]
        session_id = request_document.xpath(
            '/o:OpenPayU/o:OrderDomainRequest/o:SessionId',
            namespaces={'o': NAMESPACE,}
        )[0]
    except IndexError:
        raise httpexceptions.HTTPNotFound("Payment session not found.")
    session = DBSession.query(PayUSession).filter(
        PayUSession.id == session_id,
        PayUSession.create_order_request_id == referenced_request_id,
    ).one()
    if session is None:
        raise httpexceptions.HTTPNotFound("Payment session not found.")

    # TODO doc stat payu

    response_id = uuid.uuid4().hex
    e = ElementMaker(
        namespace=NAMESPACE,
        typemap=XML_TYPEMAP
    )
    response = e.OpenPayU(
        e.HeaderRequest(
            e.SenderName('com.sngconnect.payments'),
            e.Version('1.0'),
            e.Algorithm('SHA-256')
        ),
        e.OrderDomainResponse(
            e.OrderNotifyResponse(
                e.ResId(response_id),
                e.Status(
                    e.StatusCode('OPENPAYU_SUCCESS')
                )
            )
        )
    )
    schema.assertValid(response)
    response_string = etree.tostring(response)
    return Response(
        body=response_string,
        content_type='text/xml'
    )

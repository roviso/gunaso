import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Wrap all API errors in a consistent envelope:

        {"error": {"code": "...", "message": "...", "field_errors": {...}}}

    Unhandled exceptions are logged server-side and returned as an opaque 500 —
    internal details are never leaked to the client.
    """
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data
        field_errors = {}
        message = 'Request failed.'

        if isinstance(detail, dict):
            if 'detail' in detail:
                message = str(detail['detail'])
            else:
                field_errors = detail
                message = 'Validation failed.'
        elif isinstance(detail, list) and detail:
            message = str(detail[0])

        code = getattr(getattr(exc, 'detail', None), 'code', None) or exc.__class__.__name__
        response.data = {
            'error': {
                'code': str(code).upper(),
                'message': message,
                'field_errors': field_errors,
            }
        }
        return response

    logger.exception('Unhandled API exception', exc_info=exc)
    return Response(
        {
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An unexpected error occurred.',
                'field_errors': {},
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

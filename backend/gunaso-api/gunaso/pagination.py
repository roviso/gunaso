from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Default pagination: ?page=N&page_size=M (page_size capped at 100)."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """支持客户端通过 page_size 参数控制每页条数"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000

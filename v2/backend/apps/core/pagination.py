"""
AS v2 — Custom Pagination Classes (#408)

Provides standardized pagination for API endpoints with configurable limits.
"""

from __future__ import annotations

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Standard pagination with reasonable defaults.

    - Default page size: 100
    - Max page size: 500
    - Supports ?page_size= query param
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class LargePagination(PageNumberPagination):
    """
    Pagination for endpoints that need to return more data.

    - Default page size: 200
    - Max page size: 1000
    - Supports ?page_size= query param

    Use for: GCal list views, bulk exports, dashboard grids.
    """

    page_size = 200
    page_size_query_param = "page_size"
    max_page_size = 1000

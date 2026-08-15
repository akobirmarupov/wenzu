from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


class BusinessFeedCursorPagination(CursorPagination):
    page_size = 15
    ordering = "-created_at"
    cursor_query_param = "cursor"


class ReviewsPagination(PageNumberPagination):
    """
    Vazifasi: bitta biznesning sharhlar (Review) ro'yxati uchun,
    kichikroq page_size — mobil ekranda sharh kartochkalari katta joy egallaydi.
    """
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
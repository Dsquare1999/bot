from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import urllib.parse as urlparse
from urllib.parse import parse_qs


def get_page(url):
    if url is None:
        return None
    parsed = urlparse.urlparse(url)
    if "page" not in parse_qs(parsed.query):
        return 1
    ret = parse_qs(parsed.query)["page"]
    if isinstance(ret, list):
        return int(ret[0])
    elif isinstance(ret, str):
        return int(ret)
    elif isinstance(ret, int):
        return ret
    else:
        return ret


class StandardResultsSetPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 20

    def get_paginated_response(self, data):
        return Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "next_num": get_page(self.get_next_link()),
                    "previous_num": get_page(self.get_previous_link()),
                },
                "page_size": self.page.paginator.count % self.max_page_size,
                "max_page_size": self.max_page_size,
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "data": data,
            }
        )

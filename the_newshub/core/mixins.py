from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class PaginationMixin:
    """
    Adds pagination to pages.
    """
    paginate_by = 10

    def paginate_queryset(self, queryset, page_size):
        paginator = Paginator(queryset, page_size)
        page = self.request.GET.get("page")

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        return (paginator, page_obj, page_obj.object_list,
                page_obj.has_other_pages())

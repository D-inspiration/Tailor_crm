from django.core.paginator import Paginator

def paginate(qs, request, per_page=10):
    from django.core.paginator import Paginator

    page = request.GET.get('page', 1)
    paginator = Paginator(qs, per_page)

    return paginator.get_page(page)
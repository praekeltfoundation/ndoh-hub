import functools

from django.core.exceptions import PermissionDenied


def internal_only(view_func):
    """
    A view decorator which blocks access for requests coming through the load balancer.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.META.get("HTTP_X_FORWARDED_FOR"):
            raise PermissionDenied()
        return view_func(request, *args, **kwargs)

    return wrapper

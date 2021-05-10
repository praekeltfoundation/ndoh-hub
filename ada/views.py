from urllib.parse import urljoin, urlparse

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, render

from .models import RedirectUrl, RedirectUrlsEntry


def clickActivity(request: HttpRequest, pk: int, whatsappid: str) -> HttpResponse:
    try:
        redirect_url = RedirectUrl.objects.get(id=pk)
    except (ValueError, RedirectUrl.DoesNotExist):
        raise Http404()
    else:
        store_url_entry = RedirectUrlsEntry(url=redirect_url)
        store_url_entry.save()
        url = f"{redirect_url.symptom_check_url}"
        qs = f"?whatsappid={whatsappid}"
        parsed_url = urlparse(qs)
        destination_url = urljoin(url, parsed_url.geturl())
        return HttpResponseRedirect(destination_url)


def default_page(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        whatsappid = request.GET.get("whatsappid")
        if whatsappid is None:
            return render(
                request, "index.html", {"error": "404 Bad Request: Whatsappid is none"}
            )
    except RuntimeError as exc:
        raise RuntimeError("Runtime error in application") from exc
    else:
        context = {"pk": pk, "whatsappid": whatsappid}
        return render(request, "meta_refresh.html", context)

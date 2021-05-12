from urllib.parse import urlencode

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, render

from .models import RedirectUrl, RedirectUrlsEntry


def clickActivity(request: HttpRequest, pk: int, whatsappid: str) -> HttpResponse:
    try:
        redirect_url = RedirectUrl.objects.get(id=pk)
    except (ValueError, RedirectUrl.DoesNotExist):
        raise Http404()
    else:
        store_url_entry = RedirectUrlsEntry(symptom_check_url=redirect_url)
        store_url_entry.save()
        url = f"{redirect_url.symptom_check_url}"
        qs = urlencode({"whatsappid": whatsappid})
        destination_url = f"{url}?{qs}"
        return HttpResponseRedirect(destination_url)


def default_page(request: HttpRequest, pk: int) -> HttpResponse:
    whatsappid = request.GET.get("whatsappid")
    if whatsappid is None:
        return render(
            request, "index.html", {"error": "404 Bad Request: Whatsappid is none"}
        )
    else:
        context = {"pk": pk, "whatsappid": whatsappid}
        return render(request, "meta_refresh.html", context)

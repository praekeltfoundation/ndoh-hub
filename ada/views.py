from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, render

from .models import RedirectUrl, RedirectUrlsEntry


def clickActivity(request: HttpRequest, pk: int, whatsappid: int) -> HttpResponse:
    try:
        redirect_url = RedirectUrl.objects.get(id=pk)
    except RedirectUrl.DoesNotExist:
        raise Http404()
    else:
        store_url_entry = RedirectUrlsEntry(url=redirect_url)
        store_url_entry.save()
        destination_url = (
            f"{redirect_url.symptom_check_url}" f"/?whatsappid={whatsappid}"
        )
        return HttpResponseRedirect(destination_url)


def default_page(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        whatsappid = request.GET.get("whatsappid")
        if whatsappid is None:
            return render(
                request, "index.html", {"error": "404 Bad Request: Whatsappid is none"}
            )
    except (NameError):
        return render(
            request,
            "index.html",
            {"error": "404 Bad Request: Whatsappid does not exist"},
        )
    else:
        context = {"pk": pk, "whatsappid": whatsappid}
        return render(request, "meta_refresh.html", context)

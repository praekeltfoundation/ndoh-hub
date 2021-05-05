from django.http import HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, render

from .models import RedirectUrl, RedirectUrlsEntry


def clickActivity(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        redirect_url = RedirectUrl.objects.get(id=pk)
        store_url_entry = RedirectUrlsEntry(url=redirect_url)
        store_url_entry.save()
        destination_url = (
            f"{redirect_url.symptom_check_url}"
            f'/?whatsappid={request.GET.get("whatsappid")}'
        )
        return HttpResponseRedirect(destination_url)
    except Exception as e:
        return render(request, "index.html", {"error": e})


def default_page(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        whatsappid = request.GET.get("whatsappid")
        return render(
            request, "meta_refresh.html", {"pk": pk, "whatsappid": whatsappid}
        )
    except Exception as e:
        return render(request, "index.html", {"error": e})

from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect
from .models import *
# Create your views here.


def clickActivity(request, pk):

    try:
        redirect_url = RedirectUrl.objects.get(id=pk)

        store_url_entry = RedirectUrlsEntry(urls=redirect_url)
        store_url_entry.save()
        my_link = f'http://symptomcheck.co.za/?whatsappid={request.GET.get("whatsappid")}'
        return HttpResponseRedirect(my_link)
    except Exception as e:
        return render(request, 'index.html', {'error': e})

def default_page(request,pk):
    try:
        redirect_url = RedirectUrl.objects.get(id=pk)
        whatsappid = request.GET.get("whatsappid")
        return render(request, 'meta_refresh.html', {'pk':pk,'whatsappid':whatsappid})
    except Exception as e:
        return render(request, 'index.html', {'error': e})
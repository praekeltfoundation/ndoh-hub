import django_filters
from rest_framework import viewsets, mixins, generics, filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Source, Change
from .serializers import ChangeSerializer


class ChangePost(mixins.CreateModelMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer

    def post(self, request, *args, **kwargs):
        # load the users sources - posting users should only have one source
        source = Source.objects.get(user=self.request.user)
        request.data["source"] = source.id
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ChangeFilter(filters.FilterSet):
    """Filter for changes created, using ISO 8601 formatted dates"""
    created_before = django_filters.IsoDateTimeFilter(name="created_at",
                                                      lookup_type="lte")
    created_after = django_filters.IsoDateTimeFilter(name="created_at",
                                                     lookup_type="gte")

    class Meta:
        model = Change
        ('action', 'registrant_id', 'validated', 'source', 'created_at')
        fields = ['action', 'registrant_id', 'validated', 'source',
                  'created_before', 'created_after']


class ChangeGetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Changes to be viewed.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer
    filter_class = ChangeFilter


class OptOutInactiveIdentity(APIView):
    """
    Creates an Opt-out Change for an identity we can't send messages to
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            # The hooks send the request data as {"hook":{}, "data":{}}
            data = request.data['data']
        except KeyError:
            raise ValidationError('"data" must be supplied')
        identity_id = data.get('identity_id', None)
        if identity_id is None or identity_id == "":
            raise ValidationError(
                '"identity_id" must be supplied')
        source = Source.objects.get(user=request.user)
        Change.objects.create(source=source, registrant_id=identity_id,
                              action='momconnect_nonloss_optout',
                              data={'reason': 'sms_failure'})
        return Response(status=status.HTTP_201_CREATED)

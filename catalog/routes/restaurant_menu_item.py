"""RestaurantMenuItem modeli uchun API'lar."""

import logging

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import Business
from catalog.filters import RestaurantMenuItemFilter
from catalog.models import RestaurantMenuItem
from catalog.routes.serializers import RestaurantMenuItemSerializer
from common.pagination import StandardResultsPagination
from common.permissions import HasActiveSubscription, IsOwnerOfBusinessType
from common.services import get_owner_business

logger = logging.getLogger(__name__)


class BusinessRestaurantMenuAPIView(APIView):
    """
    GET /api/businesses/{business_id}/menu/ — ommaviy: restoran menyusi.
    Faqat `is_available=True` taomlar chiqadi.
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RestaurantMenuItemFilter
    queryset = RestaurantMenuItem.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=RestaurantMenuItemSerializer(many=True))
    def get(self, request, business_id):
        if not Business.objects.filter(pk=business_id, is_visible=True).exists():
            raise NotFound("Biznes topilmadi")

        queryset = (
            RestaurantMenuItem.objects.filter(business_id=business_id, is_available=True)
            .select_related("business")
            .order_by("name")
        )
        queryset = RestaurantMenuItemFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = RestaurantMenuItemSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class OwnerRestaurantMenuListCreateAPIView(APIView):
    """
    GET/POST /api/owner/menu/restaurant/ — restoran egasining "Menyu" ekrani.
    Egasi mavjud bo'lmagan taomlarni ham ko'radi (ommaviy ro'yxatdan farqi).
    """

    permission_classes = [IsOwnerOfBusinessType, HasActiveSubscription]
    required_business_type = Business.TYPE_RESTAURANT
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RestaurantMenuItemFilter
    queryset = RestaurantMenuItem.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=RestaurantMenuItemSerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        queryset = (
            RestaurantMenuItem.objects.filter(business=business)
            .select_related("business")
            .order_by("name")
        )
        queryset = RestaurantMenuItemFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = RestaurantMenuItemSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=RestaurantMenuItemSerializer, responses={201: RestaurantMenuItemSerializer})
    def post(self, request):
        business = get_owner_business(request.user)
        serializer = RestaurantMenuItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            item = serializer.save(business=business)

        logger.info(f"Restaurant menu item created: item_id={item.id}, business_id={business.id}")
        return Response(RestaurantMenuItemSerializer(item).data, status=status.HTTP_201_CREATED)


class OwnerRestaurantMenuDetailAPIView(APIView):
    """GET/PATCH/DELETE /api/owner/menu/restaurant/{pk}/."""

    permission_classes = [IsOwnerOfBusinessType, HasActiveSubscription]
    required_business_type = Business.TYPE_RESTAURANT
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, request, pk):
        business = get_owner_business(request.user)
        try:
            return RestaurantMenuItem.objects.select_related("business").get(
                pk=pk, business=business
            )
        except RestaurantMenuItem.DoesNotExist:
            raise NotFound("Taom topilmadi yoki sizga tegishli emas")

    @extend_schema(responses=RestaurantMenuItemSerializer)
    def get(self, request, pk):
        return Response(RestaurantMenuItemSerializer(self.get_object(request, pk)).data)

    @extend_schema(request=RestaurantMenuItemSerializer, responses=RestaurantMenuItemSerializer)
    def patch(self, request, pk):
        item = self.get_object(request, pk)
        serializer = RestaurantMenuItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        logger.info(f"Restaurant menu item updated: item_id={item.id}, by={request.user.id}")
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        item = self.get_object(request, pk)
        with transaction.atomic():
            item_id = item.id
            item.delete()
        logger.info(f"Restaurant menu item deleted: item_id={item_id}, by={request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
# from config.views import GoogleTestView 

schema_view = get_schema_view(
   openapi.Info(
      title="WENZU API",
      default_version='v1',
      description="WENZU platform API documentation",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="admin@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
   authentication_classes=[],
)



urlpatterns = [
   path('admin/', admin.site.urls),

   path('i18n/', include('django.conf.urls.i18n')),

   re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

   path("", include("account.urls")),

#    path("google-test/", GoogleTestView.as_view(), name="google-test"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
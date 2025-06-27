from rest_framework import permissions
from django.conf import settings
from drf_yasg.views import get_schema_view
from django.conf.urls.static import static
from drf_yasg import openapi
from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter

from notifications.views import NotificationViewSet
from users.views import UserViewSet
from bot_app.views import BotViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'bot', BotViewSet, basename='bot')
router.register(r'notifications', NotificationViewSet, basename='notifications')

schema_view = get_schema_view(
    openapi.Info(
        title="Trading Quant",
        default_version="v1",
        description="Trading Quantitative Bot API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@trading_bot.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

from django.urls import path
from .views import (
    BotControlView,
    BotStatusView,
    BotCookiesView,
    BotLogsView,
    BotOHLCView,
    BotTradesHistoryView
)

urlpatterns = [
    path('bot/<str:action>/', BotControlView.as_view(), name='bot-control'),
    path('bot/status/', BotStatusView.as_view(), name='bot-status'),
    path('bot/cookies/', BotCookiesView.as_view(), name='bot-cookies'),
    path('bot/logs/', BotLogsView.as_view(), name='bot-logs'),
    path('bot/ohlc/', BotOHLCView.as_view(), name='bot-ohlc'),
    path('bot/trades/', BotTradesHistoryView.as_view(), name='bot-trades'),
]
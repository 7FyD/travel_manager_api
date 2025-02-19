from django.urls import path
from .views import get_flight_offers

urlpatterns = [
    path('get-flight/', get_flight_offers),
]

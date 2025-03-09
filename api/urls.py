from django.urls import path
from .views import travel_planner

urlpatterns = [
    path('travel-planner/', travel_planner),
]

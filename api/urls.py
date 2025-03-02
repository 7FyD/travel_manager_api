from django.urls import path
from .views import travel_planner

urlpatterns = [
    path('get-flight/', travel_planner),
]

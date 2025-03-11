from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import custom_login, custom_logout, refresh_token, register_user, get_user

urlpatterns = [
    path('login/', custom_login, name='token_obtain_pair'),
    path('refresh/', refresh_token, name='token_refresh'),
    path('register/', register_user, name='register'),
    path('logout/', custom_logout, name='logout'),
    path('user/', get_user, name='user')
]

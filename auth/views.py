from tokenize import TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserRegistrationSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.contrib.auth.password_validation import validate_password


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            validate_password(serializer.password)
            user = serializer.save()
            return Response({
                'message': 'User registered successfully',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login(request):
    try:
        response = Response()
        serializer = TokenObtainPairSerializer(data=request.data)

        if serializer.is_valid():
            # Get user data to return in response
            user = serializer.user
            response.data = {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'detail': 'Login successful'
            }

            # Set cookies as before
            response.set_cookie(
                key=settings.SIMPLE_JWT.get(
                    'AUTH_COOKIE_ACCESS', 'access_token'),
                value=serializer.validated_data['access'],
                httponly=settings.SIMPLE_JWT.get(
                    'AUTH_COOKIE_HTTP_ONLY', True),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                samesite=settings.SIMPLE_JWT.get(
                    'AUTH_COOKIE_SAMESITE', 'Lax'),
                max_age=60 * 15  # 15 minutes
            )
            response.set_cookie(
                key=settings.SIMPLE_JWT.get(
                    'AUTH_COOKIE_REFRESH', 'refresh_token'),
                value=serializer.validated_data['refresh'],
                httponly=settings.SIMPLE_JWT.get(
                    'AUTH_COOKIE_HTTP_ONLY', True),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                samesite=settings.SIMPLE_JWT.get(
                    'AUTH_COOKIE_SAMESITE', 'Lax'),
                max_age=60 * 60 * 24  # 1 day
            )
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {'error': f'Login failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_logout(request):
    try:
        # Get the refresh token
        refresh_token = request.COOKIES.get(
            settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'))
        if refresh_token:
            # Blacklist the token
            token = RefreshToken(refresh_token)
            token.blacklist()

        # Create response and delete cookies
        response = Response({"detail": "Successfully logged out"})
        response.delete_cookie(settings.SIMPLE_JWT.get(
            'AUTH_COOKIE_ACCESS', 'access_token'))
        response.delete_cookie(settings.SIMPLE_JWT.get(
            'AUTH_COOKIE_REFRESH', 'refresh_token'))
        return response
    except Exception as e:
        return Response({"detail": f"Logout error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    refresh_token = request.COOKIES.get(
        settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'))
    if not refresh_token:
        return Response({'detail': 'Refresh token not found'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)

        response = Response({'detail': 'Token refreshed successfully'})
        response.set_cookie(
            key=settings.SIMPLE_JWT.get('AUTH_COOKIE_ACCESS', 'access_token'),
            value=access_token,
            httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
            secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
            samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            max_age=60 * 5  # 5 minutes
        )

        return response

    except TokenError:
        return Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user(request):
    user = request.user
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        # Add other user fields as needed
    }
    return Response(data)

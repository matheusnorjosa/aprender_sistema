"""
User Profile Endpoint - /api/me/
=================================

Returns authenticated user's information including groups.
Part of RBAC system (DAT-P08-v2).

Endpoint:
    GET /api/me/ - Returns user info and groups

Response:
    {
        "username": "johndoe",
        "email": "johndoe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_staff": true,
        "is_superuser": false,
        "groups": ["controle", "dat"]
    }
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.rbac import get_user_groups


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me(request):
    """
    Returns authenticated user's profile information and groups.

    Args:
        request: DRF Request object with authenticated user

    Returns:
        Response: JSON with user info and groups

    Example:
        GET /api/me/
        {
            "username": "johndoe",
            "email": "johndoe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_staff": true,
            "is_superuser": false,
            "groups": ["controle", "dat"]
        }
    """
    user = request.user

    return Response(
        {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "groups": get_user_groups(user),
        },
        status=status.HTTP_200_OK,
    )

from rest_framework.permissions import BasePermission
from django.conf import settings

import hashlib
import hmac
import time


class IsSwstatsWeb(BasePermission):
    def has_permission(self, request, view):
        if not settings.SWSTATS_WEB_SALT:
            return False

        if 'SWStats-Web-API' not in request.headers or 'SWStats-Web-TS' not in request.headers:
            return False

        return True

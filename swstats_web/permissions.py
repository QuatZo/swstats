from rest_framework.permissions import BasePermission
from django.conf import settings

import hashlib


class IsSwstatsWeb(BasePermission):
    def has_permission(self, request, view):
        if settings.DEBUG:
            return True
        
        if not settings.SWSTATS_WEB_SALT:
            return False
        
        if 'SWStats-Web-API' not in request.headers or 'SWStats-Web-TS' not in request.headers:
            return False
        
        if request.headers['SWStats-Web-API'] == hashlib.pbkdf2_hmac('sha256', bytes(request.headers['SWStats-Web-TS']), bytes(settings.SWSTATS_WEB_SALT), 100000):
            return True
        
        return False
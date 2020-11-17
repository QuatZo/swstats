from rest_framework.permissions import BasePermission
from django.conf import settings

import hashlib
import hmac


class IsSwstatsWeb(BasePermission):
    def has_permission(self, request, view):
        if not settings.SWSTATS_WEB_SALT:
            return False

        if 'SWStats-Web-API' not in request.headers or 'SWStats-Web-TS' not in request.headers:
            return False

        referer_url = request.META.get('HTTP_REFERER', '')
        target_url = 'localhost' if settings.DEBUG else 'web.swstats.info'
        if not target_url in referer_url:
            return False

        gen_key = hmac.new(
            key=bytes(settings.SWSTATS_WEB_SALT, encoding='utf-8'),
            msg=bytes(request.headers['SWStats-Web-TS'], encoding='utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if request.headers['SWStats-Web-API'] == gen_key:
            return True

        return False

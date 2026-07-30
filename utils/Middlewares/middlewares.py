import os
from django.conf import settings
from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin

class KeyIDMiddleware(MiddlewareMixin):
    """
    Require a valid 'key_id' header on all requests except admin and swagger.
    """
    EXEMPT_PREFIXES = (
        '/backdoor/',
        '/doc/swagger/',
        '/media/', 
        '/static/',
        '/user/api/auth/paystack-points-confirm/',
        '/user/api/auth/flutterwave-points-confirm/',
       
    )

    def process_request(self, request):
        path = request.path_info
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return None
        
        received_key = request.headers.get('x-key-id', '').strip()
        expected_key = getattr(settings, 'KEY_ID', None)
        if expected_key is None:
            return JsonResponse(
                {'error': 'Server configuration missing KEY_ID'},
                status=500
            )

        if str(received_key) != str(expected_key):
            return JsonResponse(
                {'error': 'Missing or invalid key_id header'},
                status=403
            )

        return None
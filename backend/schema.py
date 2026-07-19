from drf_yasg.generators import OpenAPISchemaGenerator
from django.http import HttpResponse
import base64
import os
from datetime import datetime, timedelta

class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema



def swagger_protect(view_func):
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return unauthorized_response()

        try:
            auth_type, creds = auth_header.split(' ')
            if auth_type.lower() != 'basic':
                return unauthorized_response()

            username, password = base64.b64decode(creds).decode('utf-8').split(':')
        except Exception:
            return unauthorized_response()

        expected_username = os.environ.get("SWAGGER_PROTECT_USERNAME")
        expected_password = os.environ.get("SWAGGER_PROTECT_PASSWORD")

        if username != expected_username or password != expected_password:
            return unauthorized_response()
        
        session_key = f'swagger_auth_time_{username}'
        last_auth_time = request.session.get(session_key)
        
        if last_auth_time:
            last_auth_time = datetime.fromisoformat(last_auth_time)
            if datetime.now() - last_auth_time > timedelta(hours=1):
                del request.session[session_key]
                return unauthorized_response()
        else:
            # New session
            request.session[session_key] = datetime.now().isoformat()

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def unauthorized_response():
    # template = loader.get_template('swagger_unauthorized.html')
    # response = HttpResponse(template.render(), status=401)
    # response['WWW-Authenticate'] = 'Basic realm="Protected"'
    # return response
    
    response = HttpResponse(
        "<h2>Unauthorized</h2><p>Please provide valid Swagger credentials.</p>",
        status=401,
        content_type="text/html"
    )
    response['WWW-Authenticate'] = 'Basic realm="Swagger Docs"'
    return response

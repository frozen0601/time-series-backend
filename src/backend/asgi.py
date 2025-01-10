import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.base")
django.setup()  # noqa
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa
from django.core.asgi import get_asgi_application  # noqa


"""
ASGI config for app project.
It exposes the ASGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

django_asgi_app = get_asgi_application()
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # "websocket": TokenAuthMiddlewareStack(
        #     URLRouter(notification_routing_urlpatterns),
        # )
    }
)

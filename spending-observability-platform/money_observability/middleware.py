from django.contrib.auth import login
from django.contrib.auth.models import User


class AutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                # Create a default superuser if none exists
                user = User.objects.create_superuser(
                    username="admin", email="admin@example.com", password="admin"
                )

            # Explicitly set the backend to avoid issues with multiple backends
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)

        return self.get_response(request)

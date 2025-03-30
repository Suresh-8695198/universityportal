from django.contrib.auth.models import AnonymousUser

class CustomUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        staff_id = request.session.get('staff_id')
        if staff_id:
            # Simulate an authenticated user
            class CustomUser:
                is_authenticated = True
                email = staff_id

            request.user = CustomUser()
        else:
            request.user = AnonymousUser()
        return self.get_response(request)

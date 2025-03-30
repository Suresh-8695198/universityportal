from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    # Custom code to run on logout (e.g., logging, cleaning up data)
    print(f'{user.username} has logged out.')

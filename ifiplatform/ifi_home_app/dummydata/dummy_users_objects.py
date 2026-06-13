from django.contrib.auth import get_user_model

User = get_user_model()


def get_dummy_user():
    # Try to reuse an existing dummy user
    user, created = User.objects.get_or_create(
        username="dummy",
        defaults={
            "email": "dummy@example.com",
        },
    )
    # Optionally set a password only once
    if created:
        user.set_password("dummy-password")
        user.save()
    return user

""" Dummy data for dummyuser objects during development."""
from django.contrib.auth import get_user_model

# TODO: Consider if this file is to be removed.

User = get_user_model()

def get_dummy_user():
    """Create dummy StudentUnion entries, optionally clearing existing ones first."""
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

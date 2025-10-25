from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Set or reset the admin user's password (default: 'admin')."

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='Username to update')
        parser.add_argument('--password', default='admin', help='New password to set')

    def handle(self, *args, **opts):
        username = opts['username']
        password = opts['password']
        User = get_user_model()

        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_superuser(username=username, email='admin@example.com', password=password)
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}' with the provided password."))
            return

        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["password", "is_active", "is_staff", "is_superuser"])
        self.stdout.write(self.style.SUCCESS(f"Password updated for user '{username}'."))


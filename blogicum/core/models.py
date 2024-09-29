from django.contrib.auth.models import AbstractUser
from django.urls import reverse_lazy


class MyUser(AbstractUser):
    def get_absolute_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.username})

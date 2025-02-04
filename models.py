from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, AbstractUser, PermissionsMixin
from django.db.models.signals import post_save, post_delete, post_migrate
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from django.contrib.postgres.fields import ArrayField


class Polygon(models.Model):
    name = models.TextField(max_length=512, blank=False, null=False)
    polygon = models.PolygonField(blank=False, null=False)
    antimeridian_crossing = models.BooleanField(null=False)
    created = models.DateTimeField(auto_now_add=True)
    users = models.ManyToManyField("User", through='PolygonToUser', through_fields=("polygon_id", "user_id"))

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        indexes = [
            models.Index(fields=['-created'], name='created_idx'),
        ]


class PolygonIntersection(models.Model):
    name = models.TextField(max_length=512, blank=False, null=False)
    polygon = models.PolygonField(blank=False, null=False)
    antimeridian_crossing = models.BooleanField(null=False)
    created = models.DateTimeField(auto_now_add=True)
    edited_polygon = models.ForeignKey(
        Polygon,
        on_delete=models.CASCADE,
        null=True
    )
    intersection_polygon_ids = ArrayField(models.BigIntegerField(), null=False, blank=False)


class UserManager(BaseUserManager):
    @staticmethod
    def create_user(username, password, is_staff=False, is_superuser=False):
        user = User.objects.create(username=username, is_staff=is_staff, is_superuser=is_superuser)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password):
        user = self.create_user(username, password, True, True)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=64, unique=True, blank=False, null=False)
    last_login = None  # disable field
    polygons = models.ManyToManyField(Polygon, through='PolygonToUser', through_fields=("user_id", "polygon_id"))
    is_staff = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'

    objects = UserManager()

    def has_usable_password(self) -> bool:
        return True

    def __str__(self):
        return f"{self.username} ({self.id})"


class PolygonToUser(models.Model):
    class Meta:
        unique_together = ('polygon', 'user')

    polygon = models.ForeignKey(
        Polygon,
        related_name='rn_polygon_id',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        related_name='rn_user_id',
        on_delete=models.CASCADE
    )
    by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rn_by_user',
        null=True,
        blank=True
    )
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.polygon.name} ({self.polygon.id}) - {self.user.username} ({self.user.id})"


@receiver(post_save, sender=Polygon)
@receiver(post_delete, sender=Polygon)
@receiver(post_migrate, sender=Polygon)
def clear_cache(_, __, **___):
    cache.delete(settings.CACHE_POLYGONS_GET_KEY)


@receiver(post_save, sender=PolygonIntersection)
@receiver(post_delete, sender=PolygonIntersection)
@receiver(post_migrate, sender=PolygonIntersection)
def clear_cache2(_, __, **___):
    cache.delete(settings.CACHE_INTERSECTIONS_GET_KEY)

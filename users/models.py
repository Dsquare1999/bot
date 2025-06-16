import uuid
from django.db import models
from .managers import UserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from trading_bot.constants import USER_ROLES


class User(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, verbose_name=_("Adresse mail"), unique=True)
    first_name = models.CharField(max_length=100, verbose_name=_("Prénoms"))
    last_name = models.CharField(max_length=100, verbose_name=_("Nom"))
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name=_("Numéro de téléphone"))
    role = models.CharField(max_length=20, choices=USER_ROLES, default='translator', blank=True, null=True)
    rate = models.FloatField(default=0.0, blank=True, null=True, verbose_name=_("Note"))
    number_of_rates = models.IntegerField(default=0, blank=True, null=True, verbose_name=_("Nombre de notes"))
    
    is_superuser = models.BooleanField(default=False)
    is_verified=models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.email
    
    def tokens(self):
        token = RefreshToken.for_user(self)
        token["firstName"] = self.first_name
        token["lastName"] = self.last_name
        token["email"] = self.email
        token["role"] = self.role
        
        return {"refresh": str(token), "access": str(token.access_token)}
    

class OneTimePassword(models.Model):
    user=models.OneToOneField(User, on_delete=models.CASCADE)
    otp=models.CharField(max_length=6)


    def __str__(self):
        return f"{self.user.first_name} - otp code"
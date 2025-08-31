from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError(_("Veuillez entrer une adresse email valide"))
        
    def user_validator(self, email, first_name, last_name):
        if email:
            email = self.normalize_email(email)
            self.email_validator(email)
        else:
            raise ValueError(_("Base User Account: An email address is required"))
        if not first_name:
            raise ValueError(_("Le Prénom est requis"))
        if not last_name:
            raise ValueError(_("Le Nom est requis"))

    def create_user(self, email, first_name, last_name, password, **extra_fields):
        self.user_validator(email, first_name, last_name)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("is superuser must be true for admin user"))

        user = self.create_user(
            email, first_name, last_name, password, **extra_fields
        )
        user.save(using=self._db)
        return user

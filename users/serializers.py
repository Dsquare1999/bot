from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str, DjangoUnicodeDecodeError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.tokens import RefreshToken, TokenError



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role', 'rate', 'number_of_rates']
        read_only_fields = ['id', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password2', 'role')

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        password=attrs.get('password', '')
        password2=attrs.get('password2', '')
        if password!=password2:
            raise serializers.ValidationError(_("Les mots de passe ne correspondent pas !"))
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)

        user.is_verified = True
        user.save()
        return user
    

class ValidateUIDAndTokenSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs['uidb64']))
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, DjangoUnicodeDecodeError):
            raise serializers.ValidationError(_("Lien invalide ou expiré."))

        if not PasswordResetTokenGenerator().check_token(user, attrs['token']):
            raise serializers.ValidationError(_("Le token est invalide ou expiré."))

        attrs['user'] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Email ou mot de passe invalide.")
        if not user.is_verified:
            raise serializers.ValidationError("Votre compte n'est pas vérifié.")
        return {
            "access_token":str(user.tokens().get('access')),
            "refresh_token":str(user.tokens().get('refresh'))
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Mot de passe actuel incorrect."))
        return value

    def validate_new_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({"new_password": _("Le nouveau mot de passe doit être différent de l'ancien.")})
        return attrs


class ChangeEmailRequestSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()

    def validate(self, attrs):
        user = self.context['request'].user

        if not user.check_password(attrs['password']):
            raise serializers.ValidationError({'password': _("Mot de passe incorrect.")})

        if User.objects.filter(email=attrs['email']).exclude(id=user.id).exists():
            raise serializers.ValidationError({'email': _("Cette adresse email est déjà utilisée.")})

        return attrs


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        if not User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": _("Email introuvable.")})
        return attrs


class SetNewPasswordSerializer(ValidateUIDAndTokenSerializer):
    password = serializers.CharField(min_length=8)
    password2 = serializers.CharField(min_length=8)

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": _("Les mots de passe ne correspondent pas.")})
        
        return attrs


class LogoutUserSerializer(serializers.Serializer):
    refresh_token=serializers.CharField()
    default_error_message = {
        'bad_token': (_('Token expiré ou invalide.')),
    }
    
    def validate(self, attrs):
        self.token = attrs.get('refresh_token')
        return attrs

    def save(self, **kwargs):
        try:
            token=RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            return self.fail('bad_token')

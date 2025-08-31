from smtplib import SMTPException

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .filters import UserFilter
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, LogoutUserSerializer, ChangePasswordSerializer, ResetPasswordRequestSerializer, ValidateUIDAndTokenSerializer, SetNewPasswordSerializer, ChangeEmailRequestSerializer
from .utils import send_generated_token_to_email, send_invitation_to_join

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter

    def get_serializer_class(self):
        if self.action == 'register':
            return RegisterSerializer
        elif self.action == 'login':
            return LoginSerializer
        elif self.action == 'logout':
            return LogoutUserSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        elif self.action == 'reset_password_request':
            return ResetPasswordRequestSerializer
        elif self.action in ['reset_password_confirm', 'verify_email']:
            return ValidateUIDAndTokenSerializer
        elif self.action == 'set_new_password':
            return SetNewPasswordSerializer
        elif self.action == 'reset_email_request':
            return ChangeEmailRequestSerializer
        elif self.action == 'refresh_token':
            return TokenRefreshSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['register', 'verify_email', 'login', 'reset_password_request', 'reset_password_confirm', 'set_new_password', 'refresh_token']:
            return [AllowAny()]
        elif self.action in ['me', 'change_password', 'logout', 'reset_email_request']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        print(type(user))  
        send_invitation_to_join(user, request)
        return Response({
            'message': _('Thanks for signing up ! Login to your account after checking your mail')
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        print("Login request data:", request.data)  # Debugging line
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=200)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': _('Mot de passe changé avec succès.')}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_password_request(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            send_generated_token_to_email(serializer.validated_data['email'], reset_type="password")
        except SMTPException:
            return Response({'detail': _("Une erreur inattendue s'est produite.")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'detail': _('Un email a été envoyé avec un lien de mise à jour.')}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='reset-password-confirm/(?P<uidb64>[^/.]+)/(?P<token>[^/.]+)')
    def reset_password_confirm(self, request, uidb64, token):
        serializer = self.get_serializer(data={'uidb64': uidb64, 'token': token})
        serializer.is_valid(raise_exception=True)

        return Response({'success':True, 'message': _('credentials is valid'), 'uidb64':uidb64, 'token':token}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def set_new_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['password'])
        user.save()

        return Response({'success':True, 'message': _("Password reset is succesful")}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_email_request(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            user = request.user
            email = serializer.validated_data['email']

            user.email = email
            user.is_verified = False
            user.save()

            send_generated_token_to_email(serializer.validated_data['email'], reset_type="email")

        except SMTPException:
            return Response({'detail': _("Une erreur inattendue s'est produite.")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'detail': _('Un email a été envoyé pour authentifier votre nouvelle adresse mail.')}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='verify-email/(?P<uidb64>[^/.]+)/(?P<token>[^/.]+)')
    def verify_email(self, request, uidb64, token):
        serializer = self.get_serializer(data={'uidb64': uidb64, 'token': token})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        user.is_verified = True
        user.save()

        return Response({'success':True, 'message': _('Email is valid'), 'uidb64':uidb64, 'token':token}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='refresh-token')
    def refresh_token(self, request):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except ValidationError:
            return Response(
                {"detail": _("Token de rafraîchissement invalide ou expiré.")},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
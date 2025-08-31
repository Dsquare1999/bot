from django.core.mail import EmailMessage
import random
from django.conf import settings
from .models import User, OneTimePassword
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from smtplib import SMTPException

def send_invitation_to_join(user, request):
    subject = "Invitation to join"
    from_email=settings.DEFAULT_FROM_EMAIL
    uidb64=urlsafe_base64_encode(smart_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)

    base_url = settings.INVITATION_FRONT_URL
    abslink = f"{base_url}/{uidb64}/{token}"

    email_body=f"Hi {user.first_name} you're invited to join through this link {abslink}"

    d_email = EmailMessage(subject=subject, body=email_body, to=[user.email])
    try:
        d_email.send()
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_generated_token_to_email(email, reset_type="password"):
    subject = "Reset of password" if reset_type == "password" else "Email Verification"

    user = User.objects.get(email=email)
    uidb64=urlsafe_base64_encode(smart_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)

    base_url = settings.PASSWORD_RESET_FRONT_URL if reset_type == "password" else settings.EMAIL_VERIFICATION_FRONT_URL
    abslink = f"{base_url}/{uidb64}/{token}"

    email_body=f"Hi {user.first_name} use the link below to your reset {abslink}"
    d_email = EmailMessage(subject=subject, body=email_body, to=[email])
    try:
        d_email.send()
        print("Email sent successfully")
    except SMTPException as e:
        print(f"Error sending email: {e}")
        raise

def send_generated_otp_to_email(email, request):
    otp = random.randint(100000, 999999)
    user = User.objects.get(email=email)
    OneTimePassword.objects.create(user=user, otp=otp)
    subject = "One Time Password"
    email_body=f"Hi {user.first_name} your one time password is {otp}"
    d_email = EmailMessage(subject=subject, body=email_body, to=[email])
    try:
        d_email.send()
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")


def send_normal_email(data):
    email=EmailMessage(
        subject=data['email_subject'],
        body=data['email_body'],
        from_email=settings.EMAIL_HOST_USER,
        to=[data['to_email']]
    )
    email.send()
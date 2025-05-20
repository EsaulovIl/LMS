import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Role
from django.contrib.auth import password_validation

PHONE_RE = re.compile(r'^\+?\d{10,15}$')

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        help_text="Будет использоваться для входа и уведомлений."
    )
    phone_number = forms.CharField(
        required=True,
        label="Телефон",
        help_text="Только цифры, можно с «+» и кодом страны."
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'password1', 'password2'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        # по умолчанию – роль "student"
        user.role = Role.objects.get(name='student')
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip()
        if not PHONE_RE.match(phone):
            raise ValidationError(
                "Неверный формат номера. "
                "Допускаются 10–15 цифр, опциональный «+» в начале."
            )
        # Если нужно — можно проверять уникальность
        if User.objects.filter(phone_number=phone).exists():
            raise ValidationError("Пользователь с таким номером уже зарегистрирован.")
        return phone

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) < 3:
            raise ValidationError("Логин должен быть не короче 3 символов.")
        return username

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Логин',
            'class': 'auth-input'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Пароль',
            'class': 'auth-input'
        })


class ProfileForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Оставьте пустым, чтобы не менять",
    )
    confirm_password = forms.CharField(
        label="Подтвердите пароль",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'username']
        widgets = {
            'phone_number': forms.TextInput(attrs={'pattern': r'^\+?\d{10,15}$'}),
        }

    # 1) проверка email на уникальность
    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.exclude(pk=self.instance.pk).filter(email=email)
        if qs.exists():
            raise ValidationError("Этот email уже используется другим пользователем.")
        return email

    # 2) проверка нового пароля через Django validators
    def clean_new_password(self):
        pw = self.cleaned_data.get('new_password')
        if pw:
            # применим все правила из settings.AUTH_PASSWORD_VALIDATORS
            password_validation.validate_password(pw, self.instance)
        return pw

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('new_password')
        cpw = cleaned.get('confirm_password')
        if pw or cpw:
            if not pw:
                raise ValidationError("Введите новый пароль.")
            if not cpw:
                raise ValidationError("Подтвердите новый пароль.")
            if pw != cpw:
                raise ValidationError("Пароли не совпадают.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('new_password')
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user
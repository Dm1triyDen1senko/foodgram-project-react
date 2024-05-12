from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator


class CustomUser(AbstractUser):

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name',]

    class UserRole(models.TextChoices):
        USER = 'user'
        ADMIN = 'admin'

    email = models.EmailField(
        max_length=254,
        unique=True,
        blank=False,
        verbose_name='Эл. почта',
    )

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            UnicodeUsernameValidator(),
        ],
        verbose_name='Имя пользователя',
    )

    password = models.CharField(
        max_length=150,
        blank=False,
        null=False,
        verbose_name='Пароль',
    )

    first_name = models.CharField(
        max_length=150,
        blank=False,
        verbose_name='Имя',
    )

    last_name = models.CharField(
        max_length=150,
        blank=False,
        verbose_name='Фамилия',
    )

    role = models.CharField(
        max_length=150,
        choices=UserRole.choices,
        default=UserRole.USER,
        verbose_name='Роль пользователя',
    )

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.UserRole.ADMIN

    class Meta:
        ordering = ['id']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )

    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='author',
        verbose_name='Автор, на которого подписались',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    # def __str__(self):
    #     return f'{self.user} отслеживает {self.author}'

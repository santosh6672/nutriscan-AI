from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    name = models.CharField(max_length=150, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Height (cm)")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Weight (kg)")
    dietary_preferences = models.TextField(blank=True, help_text="e.g., Vegetarian, Vegan, Gluten-Free")
    health_issues = models.TextField(blank=True, help_text="e.g., Diabetes, High Blood Pressure")
    goals = models.TextField(blank=True, help_text="e.g., Weight loss, Muscle gain, Better heart health")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

    @property
    def bmi(self):
        """Calculates BMI from height and weight."""
        if self.height_cm and self.weight_kg:
            height_in_meters = self.height_cm / 100
            if height_in_meters > 0:
                return round(self.weight_kg / (height_in_meters ** 2), 2)
        return None

    def __str__(self):
        return self.email
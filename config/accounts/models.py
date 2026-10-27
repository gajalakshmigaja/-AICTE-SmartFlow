from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('INSTITUTION', 'Institution User'),
        ('OFFICER', 'Scrutiny Officer'),
        ('DIRECTOR', 'Regional Director'),
        ('ADMIN', 'System Administrator'),
    ]

    REGIONAL_OFFICES = [
        ('HQ', 'Headquarters - New Delhi'),
        ('NORTH', 'Northern Regional Office - Kanpur'),
        ('NORTH_WEST', 'North-Western Regional Office - Chandigarh'),
        ('SOUTH', 'Southern Regional Office - Chennai'),
        ('SOUTH_WEST', 'South-Western Regional Office - Bengaluru'),
        ('WEST', 'Western Regional Office - Mumbai'),
        ('CENTRAL', 'Central Regional Office - Bhopal'),
        ('EAST', 'Eastern Regional Office - Kolkata'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='INSTITUTION'
    )
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    regional_office = models.CharField(
        max_length=50,
        choices=REGIONAL_OFFICES,
        default='HQ'
    )
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_institution(self):
        return self.role == 'INSTITUTION'

    @property
    def is_scrutiny_officer(self):
        return self.role == 'OFFICER' or self.user.is_superuser

    @property
    def is_regional_director(self):
        return self.role == 'DIRECTOR' or self.user.is_superuser

    @property
    def is_admin_role(self):
        return self.role == 'ADMIN' or self.user.is_superuser


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'ADMIN' if instance.is_superuser else 'INSTITUTION'
        UserProfile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            role = 'ADMIN' if instance.is_superuser else 'INSTITUTION'
            UserProfile.objects.create(user=instance, role=role)

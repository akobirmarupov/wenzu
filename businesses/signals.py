"""Biznes ma'lumoti o'zgarganda ommaviy keshni eskirtirish."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache import invalidate_business_cache

from .models import Business, BusinessPhoto, Hall, Room, VenuePricing


@receiver(post_save, sender=Business)
@receiver(post_delete, sender=Business)
@receiver(post_save, sender=Room)
@receiver(post_delete, sender=Room)
@receiver(post_save, sender=Hall)
@receiver(post_delete, sender=Hall)
@receiver(post_save, sender=BusinessPhoto)
@receiver(post_delete, sender=BusinessPhoto)
@receiver(post_save, sender=VenuePricing)
@receiver(post_delete, sender=VenuePricing)
def invalidate_on_business_change(sender, instance, **kwargs):
    invalidate_business_cache()

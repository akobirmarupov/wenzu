from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import recalculate_business_rating


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_business_rating(sender, instance, **kwargs):
    """Sharh qo'shilganda yoki o'chirilganda biznes reytingini yangilaydi."""
    recalculate_business_rating(instance.business)

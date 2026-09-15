from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import recalculate_business_rating, recalculate_ranks


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_business_rating(sender, instance, **kwargs):
    """
    Sharh qo'shilganda yoki o'chirilganda biznes reytingini va butun
    turdagi O'RINLAR jadvalini yangilaydi.

    Ikkinchisi shart: bitta joyning ko'tarilishi undan yuqoridagilarni
    bir pog'ona pastga suradi. Faqat o'zini yangilash jadvalni buzardi —
    ikki joyda bir xil o'rin turib qolardi.
    """
    business = instance.business
    recalculate_business_rating(business)
    recalculate_ranks(business.business_type)

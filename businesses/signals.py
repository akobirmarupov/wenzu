"""Biznes ma'lumoti o'zgarganda ommaviy keshni eskirtirish."""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache import invalidate_business_cache

from .models import Business, BusinessPhoto, Hall, Room, VenuePricing

logger = logging.getLogger("businesses")


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


@receiver(post_delete, sender=Business)
def reset_owner_role_when_business_is_gone(sender, instance, **kwargs):
    """
    Biznes o'chirilsa, egasining roli oddiy foydalanuvchiga qaytadi.

    Nega kerak: `role='business'` bo'lgan, lekin biznesi yo'q odam
    "yarim holatda" qolib ketardi — profilida panel ko'rinmasdi, obuna
    bo'limi ham nima ko'rsatishni bilmasdi, u esa sababini tushunmasdi.

    Signal ATAYLAB: biznes bir necha yo'ldan o'chirilishi mumkin —
    admin API, Django adminkasi, `seed_demo --clear`, qo'lda skript.
    Rolni har birida qo'lda qaytarish bitta joyni unutish demakdir
    (aynan shunday bo'lgan ham).

    Boshqa biznesi qolgan bo'lsa — rol tegilmaydi.
    """
    owner = instance.owner
    if owner.role != "business":
        return
    if Business.objects.filter(owner=owner).exists():
        return

    owner.role = "user"
    owner.save(update_fields=["role"])
    logger.info(f"Owner role reset to 'user': user_id={owner.pk} (biznesi qolmadi)")

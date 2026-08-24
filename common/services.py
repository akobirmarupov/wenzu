from rest_framework.exceptions import NotFound


def get_owner_business(user):
    """
    Vazifasi: `role='business'` foydalanuvchining biznes profilini qaytaradi.

    Barcha `/api/owner/...` endpointlari shu funksiya orqali "men kimman"
    savoliga javob oladi — biznes egasi hech qachon boshqa biznesning
    ma'lumotini so'ray olmasligi uchun business_id URL'dan emas, aynan
    tokendagi foydalanuvchidan olinadi.
    """
    # `application__plan` ham olinadi: obuna ekrani "ariza qaysi tarif
    # bilan berilgan?" degan savolga javob berishi kerak va busiz har bir
    # so'rovda qo'shimcha SELECT ketardi.
    business = user.businesses.select_related("application", "application__plan").first()
    if business is None:
        raise NotFound("Sizda hali biznes profili yo'q. Avval ariza yuboring.")
    return business

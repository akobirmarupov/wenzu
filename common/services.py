from rest_framework.exceptions import NotFound


def get_owner_business(user):
    """
    Vazifasi: `role='business'` foydalanuvchining biznes profilini qaytaradi.

    Barcha `/api/owner/...` endpointlari shu funksiya orqali "men kimman"
    savoliga javob oladi — biznes egasi hech qachon boshqa biznesning
    ma'lumotini so'ray olmasligi uchun business_id URL'dan emas, aynan
    tokendagi foydalanuvchidan olinadi.
    """
    business = user.businesses.select_related("application").first()
    if business is None:
        raise NotFound("Sizda hali biznes profili yo'q. Avval ariza yuboring.")
    return business

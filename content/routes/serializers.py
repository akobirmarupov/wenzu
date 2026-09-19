"""content ilovasining BARCHA serializerlari shu faylda."""

from rest_framework import serializers

from content.models import Banner, Language, News

LANG_FIELDS = ("uz", "ru", "en")


def resolve_language(request):
    """
    Til: avval `?lang=`, keyin `Accept-Language`, oxirida o'zbekcha.

    Mijoz tomondagi til almashtirgich `?lang=` yuboradi; mobil ilova esa
    odatda sarlavha bilan keladi — ikkalasi ham qo'llab-quvvatlanadi.
    """
    if request is None:
        return Language.UZ

    requested = (request.query_params.get("lang") or "").lower()
    if requested in LANG_FIELDS:
        return requested

    header = (request.headers.get("Accept-Language") or "").lower()
    for code in LANG_FIELDS:
        if header.startswith(code):
            return code
    return Language.UZ


class LocalizedMixin:
    """Serializer'ga `tr(obj, "title")` qulayligini beradi."""

    @property
    def lang(self):
        return resolve_language(self.context.get("request"))

    def tr(self, obj, field):
        return obj.tr(field, self.lang)


class BannerSerializer(LocalizedMixin, serializers.ModelSerializer):
    """Bosh sahifadagi banner — faqat tanlangan tildagi matnlar qaytadi."""

    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    cta_label = serializers.SerializerMethodField()
    media_src = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            "id", "title", "subtitle", "body",
            "cta_label", "cta_url", "media_type", "media_src",
            "accent_color", "placement", "order",
        ]

    def get_title(self, obj) -> str:
        return self.tr(obj, "title")

    def get_subtitle(self, obj) -> str:
        return self.tr(obj, "subtitle")

    def get_body(self, obj) -> str:
        return self.tr(obj, "body")

    def get_cta_label(self, obj) -> str:
        return self.tr(obj, "cta_label")

    def get_media_src(self, obj) -> str | None:
        src = obj.media_src
        if not src:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(src) if request and src.startswith("/") else src


class BannerAdminSerializer(serializers.ModelSerializer):
    """Admin uchun — uchala tildagi maydonlar to'liq ko'rinadi."""

    class Meta:
        model = Banner
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class NewsSerializer(LocalizedMixin, serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = News
        fields = [
            "id", "title", "excerpt", "body", "category", "category_display",
            "cover", "link_url", "is_pinned", "created_at",
        ]

    def get_title(self, obj) -> str:
        return self.tr(obj, "title")

    def get_excerpt(self, obj) -> str:
        return self.tr(obj, "excerpt")

    def get_body(self, obj) -> str:
        return self.tr(obj, "body")


class NewsAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from businesses.models import Business
from common.models import BaseModel
from reservations.models import Reservation


class Review(BaseModel):
    # SENTIMENT_POSITIVE = "positive"
    # SENTIMENT_NEGATIVE = "negative"
    # SENTIMENT_NEUTRAL = "neutral"
    # SENTIMENT_CHOICES = (
    #     (SENTIMENT_POSITIVE, "Ijobiy"),
    #     (SENTIMENT_NEGATIVE, "Salbiy"),
    #     (SENTIMENT_NEUTRAL, "Neytral"),
    # )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reviews")
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    # ai_sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, blank=True)
    # ai_summary = models.CharField(max_length=255, blank=True)
    # ai_processed = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.business} — {self.rating}★"


class ReviewPhoto(BaseModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="review_photos/")
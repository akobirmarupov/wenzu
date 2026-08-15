from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from businesses.models import Business
from common.models import BaseModel
from reservations.models import Reservation


class Review(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reviews")
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.business} — {self.rating}★"


class ReviewPhoto(BaseModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="review_photos/")
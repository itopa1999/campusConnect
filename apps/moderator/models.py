from django.db import models
from apps.campus.models import Listing
from utils.base_model import BaseModel

# Create your models here.


class FlagListing(BaseModel):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    
from django.db import models
from accounts.models import User

class ProductScan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    barcode = models.CharField(max_length=50)
    product_name = models.CharField(max_length=255)
    scan_date = models.DateTimeField(auto_now_add=True)
    analysis_result = models.TextField()

    def __str__(self):
        return f"{self.product_name} ({self.barcode})"
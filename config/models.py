from django.db import models

class SiteConfig(models.Model):
    site_name = models.CharField(max_length=200, default="Restaurant")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True)

    def __str__(self):
        return self.site_name

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

from django.db import models


class DispStaging(models.Model):
    tipo = models.CharField(max_length=20)
    linha = models.IntegerField()
    raw = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ingestao_disp_staging"
        unique_together = (("tipo", "linha"),)
        app_label = "ingestao"

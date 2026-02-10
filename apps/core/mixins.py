import uuid
from django.db import models

class UUIDModel(models.Model):
    """
    Substitui o ID numérico padrão por um UUID (Identificador Único Universal).
    Segurança contra ataques de enumeração.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class TimeStampedModel(models.Model):
    """
    Adiciona carimbos de tempo de criação e atualização automaticamente.
    Crucial para auditoria.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        abstract = True
        ordering = ['-created_at'] # Padrão: mais recentes primeiro

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "registro de auditoria"


def audit(actor, action, obj, **details):
    return AuditEvent.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        action=action, object_type=obj._meta.label_lower, object_id=str(obj.pk), details=details,
    )

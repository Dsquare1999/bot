import uuid
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-updated_at"]

    def delete(self, using=None, keep_parents=False):
        """perform soft delete"""
        self.deleted_at = timezone.now()
        # self.soft_delete_related_objects()
        super(BaseModel, self).delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """restore soft deleted object"""
        self.deleted_at = None
        # self.restore_related_objects()
        self.save(update_fields=['deleted_at'])

    def is_deleted(self):
        """check if object is deleted"""
        return self.deleted_at is not None

    def real_delete(self, using=None, keep_parents=False):
        """permanently delete object"""
        super(BaseModel, self).delete(using=using, keep_parents=keep_parents)

    # def soft_delete_related_objects(self):
    #     """Soft delete related objects."""
    #     for related_object in self._meta.get_fields():
    #         if related_object.one_to_many or related_object.one_to_one or related_object.many_to_many:
    #             related_name = related_object.get_accessor_name()
    #             related_manager = getattr(self, related_name, None)
    #
    #             if related_manager:
    #                 # Handle related objects
    #                 related_queryset = related_manager.all()
    #                 for related_instance in related_queryset:
    #                     if isinstance(related_instance, BaseModel):
    #                         related_instance.delete()
    #
    # def restore_related_objects(self):
    #     """Restore related objects."""
    #     for related_object in self._meta.get_fields():
    #         if related_object.one_to_many or related_object.one_to_one or related_object.many_to_many:
    #             related_name = related_object.get_accessor_name()
    #             related_manager = getattr(self, related_name, None)
    #
    #             if related_manager:
    #                 # Handle related objects
    #                 related_queryset = related_manager.all()
    #                 for related_instance in related_queryset:
    #                     if isinstance(related_instance, BaseModel) and related_instance.is_deleted():
    #                         related_instance.restore()


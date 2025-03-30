from django.db import models

class Note(models.Model):
    title = models.CharField(max_length=100)
    file_url = models.URLField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

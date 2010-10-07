from django.db import models

class SavedPipeline(models.Model):
    name = models.CharField(max_length=200)
    encoded = models.TextField()
    
    def __unicode__(self):
        return self.name

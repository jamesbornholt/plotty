from django.db import models

class SavedPipeline(models.Model):
    name = models.CharField(max_length=200,primary_key=True)
    encoded = models.TextField()
    
    def __unicode__(self):
        return self.name

class FormatStyle(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=200,unique=True)

    def __unicode__(self):
        return self.key

class FormatStyleEntry(models.Model):
    formatstyle = models.ForeignKey(FormatStyle)
    index = models.IntegerField()
    value = models.CharField(max_length=200) 
    display = models.CharField(max_length=200) 
    group = models.CharField(max_length=200,null=True) 
    color = models.CharField(max_length=6,null=True)

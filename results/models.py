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

class GraphFormat(models.Model):
    key = models.CharField(max_length=200,unique=True)
    parent = models.ForeignKey('self',null=True)
    value = models.TextField()

    def __unicode__(self):
        return self.safeInherit(set(self.key))

    def safeInherit(self, seen):
        if self.parent == None:
            return self.value + '\n'
        if self.key in seen:
            return '# inheritance cycle detected, aborting\n'
        seen.add(self.key)
        return self.parent.safeInherit(seen) + self.value + '\n'

    def computeParentValue(self):
        return None if not self.parent else unicode(self.parent)

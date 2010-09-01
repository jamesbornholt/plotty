from django.db import models

class Result(models.Model):
    Invocation = models.IntegerField()
    Key        = models.CharField(max_length=255)
    Value      = models.FloatField()
    Scenario   = models.ForeignKey('Scenario')
    Log        = models.ForeignKey('Log')
    
    def __unicode__(self):
        return "[%d] %s = %f" % (self.Invocation, self.Key, self.Value)

class Scenario(models.Model):
    Log        = models.ForeignKey('Log')
    Columns    = models.ManyToManyField('ScenarioVar')
    
    def __unicode__(self):
        ret = ''
        for col in self.Columns.all():
            ret += "%s=%s, " % (col.Key[:4], col.Value)
        if len(ret) > 60:
            return ret[:60].rsplit(' ', 1)[0] + '...'
        else:
            return ret

class ScenarioVar(models.Model):
    Key        = models.CharField(max_length=255)
    Value      = models.CharField(max_length=255)
    Log        = models.ForeignKey('Log')
    Scenario   = models.ForeignKey('Scenario')
    
    def __unicode__(self):
        return "%s = %s" % (self.Key, self.Value)

class Log(models.Model):
    Name       = models.CharField(max_length=255)
    Date       = models.DateTimeField()    
    
    def __unicode__(self):
        return "%s at %s" % (self.Name, self.Date)
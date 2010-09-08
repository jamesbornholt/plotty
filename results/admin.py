from plotty.results.models import *
from django.contrib import admin

class ResultAdmin(admin.ModelAdmin):
    list_display = ('Log', 'Scenario', 'Key', 'Value')
    
admin.site.register(Result, ResultAdmin)
admin.site.register(Scenario)
admin.site.register(ScenarioVar)
admin.site.register(Log)

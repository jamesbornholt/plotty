from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db import transaction
from results.models import *
import json
import os

@transaction.commit_manually
def reinstall_defaults():
    """ Reinstall the defaults from results/defaults/. This will overwrite
        existing formats with the same name. """
    try:
        # Install FormatStyles first, so we can figure the foreign key relation
        # on FormatStyleEntry later
        format_styles = {}
        f = open(os.path.join(settings.APP_ROOT, "results/defaults/FormatStyle.json"), 'r').read()
        objs = json.loads(f)
        for obj in objs:
            if obj['model'] != "results.formatstyle":
                continue
            style, created = FormatStyle.objects.get_or_create(key=obj['fields']['key'])
            if not created:
                # Clean up the old format styles, we won't be needing them
                FormatStyleEntry.objects.filter(formatstyle=style).delete()
            format_styles[obj['pk']] = style
            style.save()
        
        # Install FormatStyleEntrys
        f = open(os.path.join(settings.APP_ROOT, "results/defaults/FormatStyleEntry.json"), 'r').read()
        objs = json.loads(f)
        for obj in objs:
            if obj['model'] != "results.formatstyleentry":
                continue
            if obj['fields']['formatstyle'] not in format_styles:
                continue
            entry = FormatStyleEntry(formatstyle=format_styles[obj['fields']['formatstyle']],
                                     index=obj['fields']['index'],
                                     group=obj['fields']['group'],
                                     color=obj['fields']['color'],
                                     value=obj['fields']['value'],
                                     display=obj['fields']['display'])
            entry.save()
        
        # Install GraphFormats. We make two passes to ensure the parent format
        # always exists before we try to set it as the parent.
        f = open(os.path.join(settings.APP_ROOT, "results/defaults/GraphFormat.json"), 'r').read()
        objs = json.loads(f)
        graph_formats = {}
        second_pass = []
        for obj in objs:
            if obj['model'] != "results.graphformat":
                continue
            fmt, created = GraphFormat.objects.get_or_create(key=obj['fields']['key'])
            fmt.value = obj['fields']['value']
            fmt.save()
            graph_formats[obj['pk']] = fmt
            if obj['fields']['parent']:
                second_pass.append((fmt, obj['fields']['parent']))
        for fmt, parent in second_pass:
            if parent not in graph_formats:
                continue
            fmt.parent = graph_formats[parent]
            fmt.save()
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

if __name__ == '__main__':
    reinstall_defaults()

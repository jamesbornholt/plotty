from django import template
from results.DataTypes import *
import Image, ImageDraw, StringIO, urllib

register = template.Library()

def hash_access(obj, hash):
    if hash in obj:
        return obj[hash]
    else:
        return None

def present(obj, hash):
    val = obj.get(hash, None)
    if isinstance(val, DataAggregate):
        ciDown, ciUp = val.ciPercent()
        if math.isnan(ciUp):
            return "%.3f" % val.value()
        else:
            if ciDown == ciUp:
                ci_html = "&plusm;%.2f%%" % ciDown
            else:
                ci_html = "-%.2f%%, +%.2f%%" % (ciDown, ciUp)
            
            if val.count() < 1:
                return "%.3f <span class='ci'>(%s)</span>" % (val.value(), ci_html)
            else:
                return "%.3f <span class='ci'>(%s)</span> %s" % (val.value(), ci_html, sparkline(val.values()))
    else:
        return val

# From http://bitworking.org/news/Sparklines_in_data_URIs_in_Python
def sparkline(values):
    im = Image.new("RGB", (len(values)*2 + 2, 20), 'white')
    draw = ImageDraw.Draw(im)
    min_val = float(min(values))
    max_val = float(max(values))
    if max_val == min_val:
        coords = map(lambda x: (x, 10), range(0, len(values)*2, 10))
    else:
        coords = zip(range(0, len(values)*2, 2), [15 - 10*(float(y)-min_val)/(max_val-min_val) for y in values])
    #coords = zip(range(0, len(values)*2, 2), [15 - y/10 for y in values])
    draw.line(coords, fill="#888888")
    min_pt = coords[values.index(min_val)]
    draw.rectangle([min_pt[0]-1, min_pt[1]-1, min_pt[0]+1, min_pt[1]+1], fill="#00FF00")
    max_pt = coords[values.index(max_val)]
    draw.rectangle([max_pt[0]-1, max_pt[1]-1, max_pt[0]+1, max_pt[1]+1], fill="#FF0000")
    del draw
    
    f = StringIO.StringIO()
    im.save(f, "PNG")
    return '<img src="data:image/png,%s" title="%s" />' % (urllib.quote(f.getvalue()), ", ".join(map(lambda v: str(float(v)), values)))

register.filter('present', present)
register.filter('hash', hash_access)
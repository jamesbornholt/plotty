import math

def scenario_hash(scenario, exclude=None, include=None):
    hashstr = ""
    i = 0
    for (key,val) in scenario.items():
        i += 1
        if exclude <> None and key not in exclude:
            hashstr += key + val
        elif include <> None and key in include:
            hashstr += key + val
        elif include == None and exclude == None:
            hashstr += key + val
    return hashstr

def present_value(val):
    from results.DataTypes import DataAggregate
    if isinstance(val, DataAggregate):
        output = "%.3f" % val.value()
        ciDown, ciUp = val.ciPercent()
        if not math.isnan(ciUp):
            if ciDown == ciUp:
                output += ' <span class="ci">&plusmn;%.2f%%</span>' % ciDown
            else:
                output += ' <span class="ci">-%.2f%%, +%.2f%%</span>' % (ciDown, ciUp)
        if val.count() > 0:
            output += val.sparkline()
    else:
        output = str(val)
    return output
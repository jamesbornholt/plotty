import math

def scenario_hash(scenario, exclude=None, include=None):
    """ Hashes a scenario dictionary by either including or excluding values
        based on the specified lists.
    """
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
    """ Turns a value into a state where it can be presented as HTML, including
        its confidence interval and sparkline if appropriate.
    """
    from results.DataTypes import DataAggregate  # Avoid a circular import issue in DataTypes
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
    
def present_value_csv(key, val, values_with_ci):
    """ Turns a value into a state where it can be presented in a CSV file,
        including its confidence interval if the column it appears in has
        confidence intervals somewhere in it.
    """
    from results.DataTypes import DataAggregate  # Avoid a circular import issue in DataTypes
    if key in values_with_ci:
        ciDown, ciUp = val.ci()
        if math.isnan(ciDown):
            return '%f,"",""' % val.value()
        else:
            return '%f,%f,%f' % (val.value(), ciDown, ciUp)
    else:
        return str(val)
import math

def scenario_hash(scenario, exclude=None, include=None):
    """ Hashes a scenario dictionary by either including or excluding values
        based on the specified lists.
    """
    from plotty.results.DataTypes import ScenarioValue
    hashstr = ""
    i = 0
    for (key,val) in scenario.items():
        if isinstance(val, ScenarioValue):
            val = val.value
        i += 1
        hashstr += str(i)
        if exclude <> None and key not in exclude:
            hashstr += str(key) + str(val)
        elif include <> None and key in include:
            hashstr += str(key) + str(val)
        elif include == None and exclude == None:
            hashstr += str(key) + str(val)
    return hashstr

def present_scenario(val):
    from plotty.results.DataTypes import ScenarioValue
    if isinstance(val, ScenarioValue):
        if val.value != val.display:
            return '<span title="' + val.value + '">' + val.display + '</span>'
        else:
            return val.value
    return str(val)

def present_scenario_csv(val):
    from plotty.results.DataTypes import ScenarioValue
    if isinstance(val, ScenarioValue):
        return val.display
    return str(val)

def present_value(val):
    """ Turns a value into a state where it can be presented as HTML, including
        its confidence interval and sparkline if appropriate.
    """
    from plotty.results.DataTypes import DataAggregate  # Avoid a circular import issue in DataTypes
    if isinstance(val, DataAggregate):
        output = "%.3f" % val.value()
        ciDown, ciUp = val.ciPercent()
        if not math.isnan(ciUp):
            if ciDown == ciUp:
                output += ' <span class="ci">&plusmn;%.2f%%</span>' % ciDown
            else:
                output += ' <span class="ci">-%.2f%%, +%.2f%%</span>' % (ciDown, ciUp)
    else:
        output = str(val)
    return output
    
def present_value_csv(key, val, values_with_ci):
    """ Turns a value into a state where it can be presented in a CSV file,
        including its confidence interval if the column it appears in has
        confidence intervals somewhere in it.
    """
    from plotty.results.DataTypes import DataAggregate  # Avoid a circular import issue in DataTypes
    if key in values_with_ci:
        ciDown, ciUp = val.ci()
        if math.isnan(ciDown):
            return '%f,%f,%f' % (val.value(), val.value(), val.value())
        else:
            return '%f,%f,%f' % (val.value(), ciDown, ciUp)
    else:
        return str(val)

def present_value_csv_graph(val, useCI):
    """ Prints a value for CSV """
    from plotty.results.DataTypes import DataAggregate
    if useCI:
        if isinstance(val, DataAggregate):
            ciDown, ciUp = val.ci()
            if math.isnan(ciDown):
                return '%f,%f,%f' % (val.value(), val.value(), val.value())
            else:
                return '%f,%f,%f' % (val.value(), ciDown, ciUp)
        else:
            return '%f,%f,%f' % (val, val, val)
    else:
        return str(val)

def length_cmp(a, b):
    """ Used to sort a list of strings by their length in descending order """
    if len(a) == len(b):
        return 0
    elif len(a) < len(b):
        return 1
    else:
        return -1

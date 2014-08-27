import csv
import gzip
import os
import sys

from Utilities import scenario_hash
from Exceptions import PipelineError

# a "Result" is a single iteration of a benchmark invocation
class Result(object):
    def __init__(self, scenario, value):
        self.scenario = scenario
        self.value = value

def parse_csv(csv_path):
    """ We support two different types of CSV. Each uses a column for each
    scenario variables, but the value variables can come in two formats:
    1. Long-format data has two columns 'key' and 'value'. The 'key' column
       contains the name of each value variable, and the 'value' column the
       corresponding value. Each invocation has multiple rows in a long-format
       CSV, one row for each value variable.
    2. Wide-format data has one column for each value variable. Each invocation
       has a single row in a wide-format CSV. To distinguish scenario variables 
       from value variables, we assume value variables are prefixed with 
       'value.' (e.g. 'value.bmtime').
    """

    filename = str(os.path.basename(csv_path))
    if csv_path[-3:] == '.gz':
        f = gzip.open(csv_path, 'r')
    else:
        f = open(csv_path, 'rU')
    r = csv.DictReader(f)

    # Work out which type we're working with
    headers = set(r.fieldnames)
    if 'key' in headers and 'value' in headers:
        for h in headers:
            if h.startswith('value.'):
                raise PipelineError("Couldn't detect the format of the CSV "
                    "file `%s`, because it has both 'key' and 'value' "
                    "headers and headers that start with 'value.'." % filename, "log file %s" % filename)
        rows = _load_from_long_csv(r)
    else:
        for h in headers:
            if h.startswith('value.'):
                break
        else:
            raise PipelineError("Couldn't detect the format of the CSV "
                "file '%s', because it does not have 'key' and 'value' columns "
                "or any columns that start with 'value.'. You "
                "probably need to add 'value.' as a prefix to the file's "
                "value variable columns, like 'value.bmtime'." % filename, "log file %s" % filename)
        rows = _load_from_wide_csv(r)

    f.close()
    return rows

def _load_from_long_csv(reader):
    headers = set(reader.fieldnames) - set(['key', 'value'])

    scenarios = {}
    values = {}
    for row in reader:
        key = row.pop('key')
        val = row.pop('value')
        sc = scenario_hash(row)
        if sc not in scenarios:
            scenarios[sc] = row
            values[sc] = []
        values[sc].append((key, val))

    rows = []
    for sc in scenarios:
        row = Result(scenarios[sc], values[sc])
        rows.append(row)
    return rows

def _load_from_wide_csv(reader):
    value_columns = set([h for h in reader.fieldnames if h.startswith('value.')])
    scenario_columns = set(reader.fieldnames) - set(value_columns)

    def isFloat(x):
        try:
            float(x)
            return True
        except ValueError:
            return False

    rows = []
    for row in reader:
        scenario = dict((k, row[k]) for k in scenario_columns)
        value = [(k[6:], float(row[k])) for k in value_columns if k in row and isFloat(row[k])]
        dr = Result(scenario, value)
        rows.append(dr)
    return rows

from collections import namedtuple
import csv
import gzip
import os
import sys

from Utilities import scenario_hash
from Exceptions import PipelineError

# a "Result" is a single iteration of a benchmark invocation
Result = namedtuple('Result', ['scenario', 'value'])

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

    # We're going to open the file here just to figure out its headers
    if csv_path[-3:] == '.gz':
        f = gzip.open(csv_path, 'r')
    else:
        f = open(csv_path, 'rU')
    r = csv.DictReader(f)
    headers = set(r.fieldnames)
    f.seek(0) # let the workers decide how to work with the file

    if 'key' in headers and 'value' in headers:
        for h in headers:
            if h.startswith('value.'):
                raise PipelineError("Couldn't detect the format of the CSV "
                    "file `%s`, because it has both 'key' and 'value' "
                    "headers and headers that start with 'value.'." % filename, "log file %s" % filename)
        rows = _load_from_long_csv(f)
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
        rows = _load_from_wide_csv(f)

    f.close()
    return rows

def _load_from_long_csv(f):
    reader = csv.reader(f)

    # the test to call _load_from_long_csv guarantees these values exist
    headers = reader.next()
    key_idx = headers.index("key")
    headers.pop(key_idx)
    val_idx = headers.index("value")
    headers.pop(val_idx)

    scenarios = {}
    values = {}
    for row in reader:
        if len(row) != len(headers)+2:
            continue
        key = row.pop(key_idx)
        val = row.pop(val_idx)
        sc = _scenario_hash_fast(row)
        if sc not in scenarios:
            scenarios[sc] = dict(zip(headers, row))
            values[sc] = []
        values[sc].append((key, val))

    rows = []
    for sc in scenarios:
        row = Result(scenarios[sc], values[sc])
        rows.append(row)
    return rows

def _load_from_wide_csv(f):
    reader = csv.DictReader(f)

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

def _scenario_hash_fast(row):
    return hash(tuple(row))

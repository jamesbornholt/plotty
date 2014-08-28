from django.core.cache import cache
import logging, sys, csv, os, math, re, string, subprocess, time, stat
from plotty import settings
from plotty.results.Utilities import present_value, present_value_csv, scenario_hash, length_cmp, t_quantile
from plotty.results.Exceptions import LogTabulateStarted, PipelineError
from plotty.results.CSVParser import parse_csv
import tempfile
import StringIO, urllib

class Messages(object):

  def __init__(self):
    self.info_messages = list()
    self.warn_messages = list()

  def extend(self, other):
    self.info_messages.extend(other.info_messages)
    self.warn_messages.extend(other.warn_messages)

  def info(self, text, extra=""):
    self.info_messages.append((text, extra))

  def warn(self, text, extra=""):
    self.warn_messages.append((text, extra))

  def empty(self):
    return (len(self.info_messages) + len(self.warn_messages)) == 0

  def infos(self):
    return self.info_messages

  def warnings(self):
    return self.warn_messages


class DataTable:
    """ The core data structure. DataTable has one property, DataTable.rows.
        This is an array of DataRow objects, one per scenario in the file(s)
        being used. 
        
        A DataTable is constructed by parsing the given list of CSV files. 
        Django's caching settings are used to try to cache the parsed CSV
        data.
    """
    
    def __init__(self, logs, wait=True):
        """ Creates a new DataTable by reading each CSV file provided, or
            loading them from cache if they are present. This routine will
            also check whether the log files specified have been modified
            since they were cached (based on last modified date), and if so,
            will expire the cache.
            
            logs: an array of paths to CSV files, relative to 
                  settings.BM_LOG_DIR.
            wait: if True, we will wait for the logs to be tabulated. if not,
                  depending on the size of the logs, we will spawn a subprocess
                  and wait.
        """
        self.rows = []
        self.scenarioColumns = set()
        self.valueColumns = set()
        self.messages = Messages()
        self.lastModified = 0
        for i, log in enumerate(logs):
            dir_path = os.path.join(settings.BM_LOG_DIR, log)
            cached_vals = cache.get("LOGFILE-" + log)
            file_last_modified = os.path.getmtime(dir_path)
            if cached_vals is None or cached_vals['last_modified'] < file_last_modified:
                # cache is invalid, we need to reload
                messages = Messages()
                try:
                    rows, lastModified, scenarioColumns, valueColumns = self.loadLog(log, wait, messages)
                except LogTabulateStarted as e:
                    e.index = i
                    e.length = len(logs)
                    raise e

                # store the results in the cache
                ret = cache.set("LOGFILE-" + log, {
                    'last_modified': lastModified, 
                    'rows': rows,
                    'scenarioColumns': scenarioColumns,
                    'valueColumns': valueColumns,
                    'messages': messages})
                
                logging.debug('For log %s: cache empty or expired, stored %d rows to cache.' % (log, len(rows)))
            else:
                lastModified = cached_vals['last_modified']
                rows = cached_vals['rows']
                scenarioColumns = cached_vals['scenarioColumns']
                valueColumns = cached_vals['valueColumns']
                messages = cached_vals['messages']
                logging.debug('For log %s: loaded %d rows from cache (dir last modified: %d, cache last modified: %d)' % (log, len(rows), file_last_modified, cached_vals['last_modified']))
            self.rows.extend(rows)
            self.scenarioColumns |= scenarioColumns
            self.valueColumns |= valueColumns
            self.messages.extend(messages)
            if self.lastModified < lastModified: 
                self.lastModified = lastModified
        self.valueColumnsDisplay = dict([(x,x) for x in self.valueColumns])

    def __iter__(self):
        """ Lets us do `for row in datatable` instead of 
            `for row in datatable.rows`.
        """
        return iter(self.rows)

    def loadLog(self, log, wait, messages):
        """ Load a log file directly (services the cache)
            
            log: a relative path to the log file to be parsed.
            wait: should we wait for the parser (true), or return immediately
                  while it runs in the background (false)
        """
        # is this a log directory, or a plain csv file?
        log_path = os.path.join(settings.BM_LOG_DIR, log)
        lastModified = os.path.getmtime(log_path)
        if os.path.isdir(log_path):
            rows = self.loadLogDirectory(log, wait)
        else:
            rows = parse_csv(log_path)

        # make column names safe
        num_unnamed_columns = 0
        safe_chars = frozenset('_.')
        def make_column_name_safe(k, tag):
            if any(c.isalnum() or c in safe_chars for c in k):
                newk = ''.join(c if c.isalnum() or c in safe_chars else '.' for c in k)
                if newk[0].isdigit():
                    newk = "_" + newk
            else:
                newk = tag + num_unnamed_columns
                num_unnamed_columns += 1
            return newk

        clean_rows = []
        scenario_column_names = {'logfile': 'logfile'}
        value_column_names = {}
        duplicate_value_columns = set()
        nonnumeric_value_columns = set()
        
        for row in rows:
            # validate scenario keys
            for k in row.scenario.keys():
                # sanitise the column name
                if k not in scenario_column_names:
                    scenario_column_names[k] = make_column_name_safe(k, "scenario_")
                newk = scenario_column_names[k]
                # rename the column in the row if necessary
                if k != newk:
                    row.scenario[newk] = row.scenario[k]
                    del row.scenario[k]
            # add the log's name to its scenario columns; force cast from unicode
            row.scenario['logfile'] = str(log)

            # validate value keys
            value = {}
            for k, v in row.value:
                # if the value isn't numeric, we're not going to use it, so
                # need to do nothing for this (k, v)
                try:
                    v = float(v)
                except ValueError:
                    if k not in nonnumeric_value_columns:
                        messages.warn("Non-numeric values for value column '%s'." % k,
                            "For example, scenario %s has %s value '%s'." % (
                                row.scenario, k, v))
                        nonnumeric_value_columns.add(k)
                    continue
                # sanitise the column name
                if k not in value_column_names:
                    value_column_names[k] = make_column_name_safe(k, "value_")
                newk = value_column_names[k]
                # check for duplicates that are distinct (we let repeated values
                # through silently)
                if newk in value and v != value[newk]:
                    # only output a warning once per column
                    if newk not in duplicate_value_columns:
                        messages.warn("Duplicate values for value column '%s'." % k,
                            "For example, scenario %s has %s values %s and %s." % (
                                row.scenario, k, value[newk], v))
                        duplicate_value_columns.add(newk)
                # write the value into this row; we do this regardless of
                # duplicates, so the last value always wins
                value[newk] = v

            # add the row
            clean_rows.append(DataRow(row.scenario, value))

        # summarise what we've done
        logging.debug('Parsed %d results from log %s' % (len(clean_rows), log))
        scenario_columns = set(scenario_column_names.values())
        value_columns = set(value_column_names.values())
        return clean_rows, lastModified, scenario_columns, value_columns

    def loadLogDirectory(self, log, wait):
        """ Tabulate a log directory into the CSV cache """
        # path to the log directory
        log_path = os.path.join(settings.BM_LOG_DIR, log)

        # the tabulation script will output a csv file into the csv directory
        csv_dir = os.path.join(settings.CACHE_ROOT, "csv")
        if not os.path.exists(csv_dir):
            os.mkdir(csv_dir)
        csv_file = os.path.join(csv_dir, log + ".csv.gz")

        # we need to re-parse the log file if the csv doesn't yet exist or the
        # log directory has changed since the csv was written
        lastModified = os.path.getmtime(log_path)
        if not os.path.exists(csv_file) or os.path.getmtime(csv_file) < lastModified:
            logging.debug("Retabulating CSV for " + log_path + " since CSV was out of date or non-existent")
            
            if not wait:
                # we're not going to wait for the parser; run it in the background
                pid = subprocess.Popen(["python", settings.TABULATE_EXECUTABLE, log_path, csv_file, settings.CACHE_ROOT]).pid
                raise LogTabulateStarted(log, pid)
            else:
                # call the parser directly
                if settings.USE_NEW_LOGPARSER:
                    from plotty.results.LogParser import tabulate_log_folder
                    tabulate_log_folder(log_path, csv_file)
                else:
                    from plotty.results.Tabulate import extract_csv
                    extract_csv(log_path, csv_file)
        else:
            logging.debug("Valid CSV already exists for " + log_path + ", skipping retabulation.")

        # parse the resulting CSV
        rows = parse_csv(csv_file)
        return rows

    def headers(self):
        """ Returns the headers that would be used to output a table of
            this data as two lists - scenario headers and value headers.
        """
        scenarios = set()
        values = set()
        values_with_ci = set()
        
        # XXX TODO: Why do we need to loop here? Can't we just use
        # self.valueColumns and self.scenarioColumns, assuming they're being
        # kept up to date?
        for row in self.rows:
            for key in row.scenario.iterkeys():
                if key not in scenarios:
                    scenarios.add(key)
            for key,val in row.values.items():
                if key not in values:
                    values.add(key)
                if isinstance(val, DataAggregate):
                    values_with_ci.add(key)
        
        s_list = list(scenarios)
        s_list.sort()
        v_list = list(values)
        v_list.sort()
        vci_list = list(values_with_ci)
        vci_list.sort()

        return s_list, v_list, vci_list
    
    def selectValueColumns(self, vals, derivedVals):
        """ Selects the specified set of value columns and throws away all
            others from each row in the table.
            
            vals: a list of value columns to keep.
        """

        vals = set(map(lambda x: str(x), vals))
        derivedVals = set(map(lambda x: str(x), derivedVals))
        
        derived_vals = []
        subst_variable = lambda i: "s%02i" % i
        value_columns_lower = dict([(str.lower(s), s) for s in self.valueColumns])
        # Super hack: this avoids e.g. 'time.gc' being interpreted as referring
        # to the 'time' column, thereby creating an invalid expression. So, we
        # sort the possible keys by length, so 'time.gc' is always tested before
        # 'time'.
        value_columns_keys = value_columns_lower.keys()
        value_columns_keys.sort(length_cmp)
        for expr in derivedVals:
            # Try to compile the derived columns
            val = str.lower(str(expr))
                
            # Replace the value column tokens in the expression with a simple
            # substitution key. We'll also prepare a simple exemplar row to make
            # sure the expression evaluates cleanly at this point.
            statement = val
            subst_key = {}
            exemplar_row = {}
            for i,valid_val in enumerate(value_columns_keys):
                if statement.find(valid_val) > -1:
                    var = subst_variable(i)
                    statement = statement.replace(valid_val, var)
                    subst_key[var] = value_columns_lower[valid_val]
                    exemplar_row[var] = 1.0
            
            # It's a clean and reasonable expression, prepare it properly.
            # This is a hack that lets us be more flexible with value column
            # names. A number of column names (particularly stats outputs
            # from MMTk) are invalid python identifiers.
            try:
                # This is safe - compile won't evaluate the code, just parse it
                compiled = compile(statement, statement, 'eval')
            except SyntaxError:
                raise PipelineError("The expression '%s' is not a valid Python expression" % expr)
            except ValueError:
                raise PipelineError("The expression '%s' is not a valid Python expression" % expr)
            
            # Now try evaluating it, without access to the standard library
            try:
                v = eval(compiled, {'__builtins__': None}, exemplar_row)
            except:
                raise PipelineError("The expression '%s' is not a valid Python expression" % expr)
        
            derived_vals.append((expr, compiled, subst_key.copy()))
            # From now on, the derived value cols should be treated exactly like
            # any other value column
            vals.add(expr)

        for row in self.rows:
            # Calculate derived cols first, since they might not be selected
            # in their own right.
            for name,code,subst in derived_vals:
                # Calculate the substitution dictionary
                evaled_subst = {}
                invalid = False
                for token,key in subst.items():
                    if key not in row.values:
                        invalid = True
                        break
                    else:
                        evaled_subst[token] = row.values[key]
                if invalid:
                    continue
                
                # Evaluate the code with none of the builtin functions available.
                # This means none of the python builtin methods, which include the
                # import statement, are available to the code. This is pretty good
                # security, but does restrict us somewhat in mathematics.
                try:
                    row.values[name] = eval(code, {'__builtins__': None}, evaled_subst)
                except:
                    continue
            
            # Now select the value columns we're after
            for (key,val) in row.values.items():
                if key not in vals:
                    del row.values[key]

        self.valueColumns = vals
        self.valueColumnsDisplay = dict([(x,x if x not in self.valueColumnsDisplay else self.valueColumnsDisplay[x]) for x in vals])

    def selectScenarioColumns(self, cols):
        """ Selects the specified set of scenario columns and throws away all
            others from each row in the table.
            
            cols: a list of scenario columns to keep.
        """
        for row in self.rows:
            for (key,val) in row.scenario.items():
                if key not in cols:
                    del row.scenario[key]
        self.scenarioColumns = set(cols)

    def getScenarioValues(self):
        scenarioValues = {}
        for row in self.rows:
            for col in row.scenario:
                if col not in scenarioValues:
                    scenarioValues[col] = set()
                scenarioValues[col].add(row.scenario[col])
        for k in scenarioValues.iterkeys():
            valuesList = list(scenarioValues[k])
            formattedValues = []
            otherValues = []
            for v in valuesList:
                if isinstance(v, ScenarioValue):
                    formattedValues.append(v)
                else:
                    otherValues.append(v)
            formattedValues.sort(key=lambda fv: fv.index)
            otherValues.sort()
            formattedValues.extend(otherValues)
            scenarioValues[k] = formattedValues

        return scenarioValues

    def renderToTable(self):
        """ Renders the values in this data table into a HTML table. """
        scenarios, values, _ = self.headers()
        output = '<table class="results"><thead>'
        for name in scenarios:
            output += '<th class="scenario-header">' + name + '</th>'
        for name in values:
            output += '<th class="value-header">' + name + '</th>'
        output += '</thead><tbody>'
        
        for row in self.rows:
            s = '<tr>'
            for key in scenarios:
                if key in row.scenario:
                    if isinstance(row.scenario[key], ScenarioValue):
                        s+= '<td title="' + row.scenario[key].value + '">' + row.scenario[key].display + '</td>'
                    else:
                        s+= '<td>' + str(row.scenario[key]) + '</td>'
                else:
                    s+= '<td>*</td>'
            for key in values:
                if key in row.values:
                    s += '<td>' + present_value(row.values[key]) + '</td>'
                else:
                    s += '<td>*</td>'
            s += '</tr>'
            output += s
        output += '</tbody></table>'
        return output
    
    def renderToCSV(self):
        scenarios, values, values_with_ci = self.headers()
        scenarios.sort(key=str.lower)
        values.sort(key=str.lower)
        output = ''
        for name in scenarios:
            output += '"' + name + '",'
        for name in values:
            output += '"' + name + '",'
            if name in values_with_ci:
                output += '"' + name + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.lowerBound",'
                output += '"' + name + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.upperBound",'
        if len(output)>0 and output[-1] == ',':
            output = output[:-1]
        output += "\r\n"
        
        for row in self.rows:
            for key in scenarios:
                if key in row.scenario:
                    output += '"' + str(row.scenario[key]) + '",'
                else:
                    output += '"",'
            for key in values:
                if key in row.values:
                    output += present_value_csv(key, row.values[key], values_with_ci) + ','
                else:
                    if key in values_with_ci:
                        output += '"","",""'
                    else:
                        output += '"",'
            if output[-1] == ',':
                output = output[:-1]
            output += "\r\n"
                    
        return output

class DataRow:
    """ A simple object that holds a row of data. The data is stored in two
        dictionaries - DataRow.scenario for the scenario columns, and
        DataRow.values for the value columns. 
    """
    def __init__(self, scenario=None, values=None):
        if scenario is None:
            scenario = {}
        if values is None:
            values = {}
        self.values = values
        self.scenario = scenario
        
    def __repr__(self):
        return '(DataRow scenario=%s values=%s)' % (self.scenario, self.values)

class ScenarioValue:

    def __init__(self, indexOrOther, value=None, display=None, group = None, color = None):
        if not value is None:
            self.index = indexOrOther
            self.value = value
            self.display = display
            self.group = group
            self.color = color
        elif isinstance(indexOrOther, ScenarioValue):
            self.index = indexOrOther.index
            self.value = indexOrOther.value
            self.display = indexOrOther.display
            self.group = indexOrOther.group
            self.color = indexOrOther.color
        else:
            self.index = None
            self.value = str(indexOrOther)
            self.display = str(indexOrOther)
            self.group = None
            self.color = None

    def isFormatted():
        return not self.index is None

    def __str__(self):
        return str(self.display)

    def __float__(self):
        raise PipelineError("ScenarioValue shouldn't treated as a float")

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if isinstance(other, ScenarioValue):
            return self.value == other.value
        return self.value == other

    def __cmp__(self, other):
        raise PipelineError("ScenarioValues shouldn't be compared directly")

    def __hash__(self):
        return hash(self.value)

class DataAggregate:
    """ Holds an aggregate of values that were mutliple rows but have been
        condensed into one as part of an Aggregate block. This object can
        report the mean or geomean of those values, as well as their minimum
        and maximum, and standard deviation and a confidence interval (with
        confidence decided by settings.CONFIDENCE_LEVEL). It is also
        possible to divide two DataAggregates (generally for normalisation),
        in which case relevant statistical techniques are used to determine
        the new confidence interval and standard deviation.
    """
    def __init__(self, newType):
        """ Create a new DataAggregate of the specified type.
        
            newType: either 'mean' or 'geomean', the type of aggregate
                     reported by this object.
        """
        self.type = newType
        self._isValid = False
        self._values = []

    # Private methods
    
    def _calculate(self):
        """ Calculates the summary statistics for data in self._values. This
            method only does calculations for a single variable - calculations
            for a compound variable (A + B, A / B, etc, where A and B are
            DataAggregates) should be handled by the appropriate operator
            overload below.
        """
        valMin = float('+inf')
        valMax = float('-inf')
        valMean = 0.0
        valM2 = 0.0
        valLogSum = 0.0
        n = 0

        allow_cis = len(self._values) > 1

        for val in self._values:
            # We can also aggregate sets of DataAggregates
            if isinstance(val, DataAggregate):
                val = val.value()
                allow_cis = False
            n += 1
            if val < valMin:
                valMin = val
            if val > valMax:
                valMax = val
            if self.type == 'geomean':
                if valLogSum is None:
                    continue
                # If any value is zero, the geomean is also zero
                if val == 0:
                    valLogSum = None
                    continue
                valLogSum += math.log(val)
            else:
                delta = val - valMean
                valMean += delta/n
                valM2 += delta * (val - valMean)

        self._min = valMin
        self._max = valMax
        if self.type == 'geomean':
            if valLogSum is not None:
                self._value = math.exp(valLogSum / n)
            else:
                self._value = 0.0
            self._stdev = 0
            self._ciUp = self._ciDown = float('nan')
        elif self.type == 'mean':
            self._value = valMean
        
            if allow_cis:
                self._stdev = math.sqrt(valM2 / (n - 1))
    
                ciDelta = t_quantile(1 - settings.CONFIDENCE_LEVEL, n-1) * self._stdev / math.sqrt(n)
                self._ciUp = self._value + ciDelta
                self._ciDown = self._value - ciDelta
            else:
                self._stdev = 0
                self._ciUp = self._ciDown = float('nan')
        
        self._isValid = True

    # Mutators
    
    def append(self, value):
        """ Push a new value into this aggregate. """
        self._values.append(value)
        self._isValid = False
    
    def map(self, func):
        """ Apply a function to every value in this aggregate. """
        self._isValid = False
        self._values = map(func, self._values)
    
    def setType(self, newType):
        """ Change the type of this aggregate.
        
            newType : either 'mean' or 'geomean'.
        """
        self.type = newType
        self._isValid = False
    
    def manual(self, value, ciUp, ciDown, newMin, newMax):
        """ Set the values of this DataAggregate manually. Used by operator
            overloads. 
        """
        self._value = value
        self._ciUp = ciUp
        self._ciDown = ciDown
        self._min = newMin
        self._max = newMax
        self._isValid = True
        
    # Getters
    
    def value(self):
        if not self._isValid:
            self._calculate()
        return self._value
    
    def values(self):
        return self._values
    
    def stdev(self):
        if not self._isValid:
            self._calculate()
        return self._stdev
    
    def count(self):
        if not self._isValid:
            self._calculate()
        return len(self._values)
    
    def sem(self):
        if not self._isValid:
            self._calculate()
        return self._stdev / math.sqrt(len(self._values))
    
    def min(self):
        if not self._isValid:
            self._calculate()
        return self._min
    
    def max(self):
        if not self._isValid:
            self._calculate()
        return self._max

    def ci(self):
        if not self._isValid:
            self._calculate()
        return self._ciDown, self._ciUp

    def ciPercent(self):
        if not self._isValid:
            self._calculate()
        if math.isnan(self._ciUp):
            return self._ciDown, self._ciUp
        ciDown = (self._value - self._ciDown) * 100 / self._value
        ciUp = (self._ciUp - self._value) * 100 / self._value
        return ciDown, ciUp

    # Overloads

    def __repr__(self):
        if not self._isValid:
            self._calculate()
        if math.isnan(self._ciUp):
            return "%.3f" % self._value
        else:
            return "%.3f CI(%.3f, %.3f) min=%.3f max=%.3f vals=%s" % (self._value, self._ciDown, self._ciUp, self._min, self._max, self._values)
    
    def __str__(self):
        return self.__repr__()

    def __float__(self):
        return self.value()
    
    def __cmp__(self, other):
        if float(self) > float(other):
            return 1
        elif float(self) < float(other):
            return -1
        else:
            return 0
    
    def __div__(self, other):
        """ Divides this DataAggregate by some other value. If the other value
            is a DataAggregate, statistical techniques are used to compute the
            new value and standard error. If not, we just divide every value
            in this DataAggregate by the other value, and force the summary
            data to be regenerated.
        """
        if isinstance(other, DataAggregate):
            #logging.debug(other)
            res = DataAggregate(self.type)
            if other.value() <> 0:
                val = self.value() / other.value()
            else:
                val = math.copysign(float('inf'), self.value())
            
            # Motulsky, 'Intuitive Biostatistics', pp285-6
            if self.value() <> 0 and other.value() <> 0:
                tinv = t_quantile(1 - settings.CONFIDENCE_LEVEL, self.count() + other.count() - 2)
                g = (tinv * (other.sem() / other.value()))**2
                if g >= 1.0:
                    ciUp = ciDown = float('nan')
                else:
                    sem = ( val / (1-g) ) * math.sqrt((1-g) * (self.sem() / self.value())**2 + (other.sem() / other.value()) ** 2)
                    ciUp = ( val / (1-g) ) + tinv*sem
                    ciDown = ( val / (1-g) ) - tinv*sem
            else:
                ciUp = ciDown = float('nan')
            
            if other.max() <> 0 and other.min() <> 0:
                valMin = self.min() / other.max()
                valMax = self.max() / other.min()
            else:
                valMin = math.copysign(float('inf'), self.min())
                valMax = math.copysign(float('inf'), self.max())
            
            res.manual(value=val, ciUp=ciUp, ciDown=ciDown, newMin=valMin, newMax=valMax)
            return res
        else:
            res = copy.copy(self)
            res.map(lambda d: d / float(other))
            return res

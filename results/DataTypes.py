from django.core.cache import cache
import logging, sys, csv, os, math, re, string, subprocess, time, stat
from plotty import settings
from plotty.results.Utilities import present_value, present_value_csv, scenario_hash, length_cmp
from plotty.results.Tabulate import extract_csv
from plotty.results.Exceptions import LogTabulateStarted, PipelineError
import tempfile
from scipy import stats
import Image, ImageDraw, StringIO, urllib

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
        for i,log in enumerate(logs):
            dir_path = os.path.join(settings.BM_LOG_DIR, log)
            cached_vals = cache.get(log)
            file_last_modified = os.path.getmtime(dir_path)
            if cached_vals == None or cached_vals['last_modified'] < file_last_modified:
                try:
                    rows, lastModified, scenarioColumns, valueColumns, messages = self.loadCSV(log, wait)
                except LogTabulateStarted as e:
                    e.index = i
                    e.length = len(logs)
                    raise e
                ret = cache.set(log, {'last_modified': lastModified, 'rows': rows, 'scenarioColumns': scenarioColumns, 'valueColumns': valueColumns, 'messages': messages})
                # Hack! Hack! Hack!
                # Alternative: find the user owning this instance, chown to them,
                # and set a+rx u+rxw?
                cache_file = cache._key_to_file(log)
                # Cache files are three directories deep, so chmod all 3 levels
                # (file, inner, outer dir, 'cache/log'). 
                for i in xrange(4):
                    os.chmod(cache_file, 0777)
                    cache_file, _ = os.path.split(cache_file)
                
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

    def __iter__(self):
        """ Lets us do `for row in datatable` instead of 
            `for row in datatable.rows`.
        """
        return iter(self.rows)

    def loadCSV(self, log, wait):
        """ Parses the CSV file at log into an array of DataRow objects.
            
            log: a relative path to the log file to be parsed.
        """
        scenarios = {}
        value_cols = set()
        messages = Messages()

        dir_path = os.path.join(settings.BM_LOG_DIR, log)
        csv_dir = os.path.join(settings.CACHE_ROOT, "csv")
        csv_file = os.path.join(csv_dir, log + ".csv.gz")
        if not os.path.exists(csv_dir):
            os.mkdir(csv_dir)
            os.chmod(csv_dir, 0777)


        # Store the log's last modified date
        lastModified = os.path.getmtime(dir_path)
        
        invalid_chars = frozenset("+-/*|&^")
        
        # Only retabulate if the logs have been modified since the csv was
        # generated.
        if not os.path.exists(csv_file) or os.path.getmtime(csv_file) < lastModified:
            logging.debug("Retabulating CSV for " + dir_path + " since CSV was out of date or non-existent")
            if not wait:
                # We don't want to wait - throw an exception and tell the client
                # to come back later.
                pid = subprocess.Popen(["python", settings.TABULATE_EXECUTABLE, dir_path, csv_file, settings.CACHE_ROOT]).pid
                raise LogTabulateStarted(log, pid)
            else:
                extract_csv(dir_path, csv_file)
        else:
            logging.debug("Valid CSV already exists for " + dir_path + ", skipping retabulation.")

        gunzip_process = subprocess.Popen(["gunzip", "-c", csv_file], stdout=subprocess.PIPE)
        reader = csv.DictReader(gunzip_process.stdout)
        reader.fieldnames = map(str.lower, reader.fieldnames)
        for line in reader:
            key = line.pop('key')
            if key == None or key == '':
                continue
            key_clean = ''.join(('.' if c in invalid_chars else c) for c in key)
            if key_clean == '':
                continue
            value = line.pop('value')
            if value == '' or value == None:
                continue
            if key_clean not in value_cols:
                value_cols.add(key_clean)
            line['logfile'] = str(log)
            schash = scenario_hash(line)
            if schash not in scenarios:
                scenarios[schash] = DataRow(line)
            if key_clean in scenarios[schash].values:
              raise PipelineError("Invalid log file, multiple values for key %s with scenario %s" % (key_clean, line))
            try:
              scenarios[schash].values[key_clean] = float(value)
            except:
              messages.warn("'%s' not numeric" % value, str(line))
        
        logging.debug('Parsed %d rows from CSV' % len(scenarios))
        scenario_cols = reader.fieldnames
        scenario_cols.remove('key')
        scenario_cols.remove('value')
        return scenarios.values(), lastModified, set(scenario_cols), value_cols, messages

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
                    s+= '<td>' + row.scenario[key] + '</td>'
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
        if output[-1] == ',':
            output = output[:-1]
        output += "\r\n"
        
        for row in self.rows:
            for key in scenarios:
                if key in row.scenario:
                    output += '"' + row.scenario[key] + '",'
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
    def __init__(self, scenario=None):
        """ Creates a new DataRow, optionally using a specified scenario
            dictionary.
            
            scenario: (optional) the initial scenario dictionary for this row.
        """
        if scenario == None:
            scenario = {}
        self.values = {}
        self.scenario = scenario
        
    def __repr__(self):
        return '(DataRow scenario=%s values=%s)' % (self.scenario, self.values)


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
        valSum = 0.0
        valProduct = 1.0
        valSquareSum = 0.0
        valMin = float('+inf')
        valMax = float('-inf')
        
        for val in self._values:
            # We can also aggregate sets of DataAggregates
            if isinstance(val, DataAggregate):
                val = val.value()
            valSum += val
            valProduct *= val
            valSquareSum += val**2
            if val < valMin:
                valMin = val
            if val > valMax:
                valMax = val

        self._min = valMin
        self._max = valMax
        if self.type == 'geomean':
            self._value = math.pow(valProduct, 1.0/len(self._values))
        elif self.type == 'mean':
            self._value = valSum / len(self._values)
        
        # Confidence intervals/stdev/etc only make sense for more than one value
        if len(self._values) > 1:
            # http://en.wikipedia.org/wiki/Computational_formula_for_the_variance
            # s^2 = (n/n-1)( (1/n)(sum[x_i^2]) - x_bar^2 )
            #     = (1/n-1)(sum[x_i^2]) - (n/n-1)(x_bar^2 )
            #     = (1/n-1)( sum[x_i^2] - n(sum[x]/n)^2 )
            #     = (1/n-1)( sum[x_i^2] - (sum[x]^2 / n) )
            #     = (1/n-1)( valSquareSum - (valSum * valSum / n) )
            n = len(self._values)
            self._stdev = math.sqrt( (1.0/(n-1)) * ( valSquareSum - (valSum * valSum / n) ) )

            ciDelta = stats.t.isf((1 - settings.CONFIDENCE_LEVEL) / 2, n-1) * self._stdev / math.sqrt(n)
            self._ciUp = self._value + ciDelta
            self._ciDown = self._value - ciDelta
        else:
            self._stdev = 0
            self._ciUp = self._ciDown = self._value
        
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
                tinv = stats.t.isf((1 - settings.CONFIDENCE_LEVEL) / 2, self.count() + other.count() - 2)
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

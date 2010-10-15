from django.core.cache import cache
import logging, sys, csv, os, math
from plotty import settings
from results.Utilities import present_value, present_value_csv, scenario_hash
from scipy import stats
import Image, ImageDraw, StringIO, urllib


class DataTable:
    """ The core data structure. DataTable has one property, DataTable.rows.
        This is an array of DataRow objects, one per scenario in the file(s)
        being used. 
        
        A DataTable is constructed by parsing the given list of CSV files. 
        Django's caching settings are used to try to cache the parsed CSV
        data.
    """
    
    def __init__(self, logs):
        """ Creates a new DataTable by reading each CSV file provided, or
            loading them from cache if they are present. This routine will
            also check whether the log files specified have been modified
            since they were cached (based on last modified date), and if so,
            will expire the cache.
            
            logs: an array of paths to CSV files, relative to 
                  settings.BM_LOG_DIR.
        """
        self.rows = []
        self.scenarioColumns = set()
        self.valueColumns = set()
        for log in logs:
            file_path = os.path.join(settings.BM_LOG_DIR, log)
            logging.debug('Attempting to load log %s from cache' % log)
            cached_vals = cache.get(log)
            file_last_modified = os.path.getmtime(file_path)
            if cached_vals == None or cached_vals['last_modified'] < file_last_modified:
                logging.debug('Cache empty or expired, reloading %s from file' % log)
                rows, lastModified, scenarioColumns, valueColumns = self.loadCSV(file_path)
                ret = cache.set(log, {'last_modified': lastModified, 'rows': rows, 'scenarioColumns': scenarioColumns, 'valueColumns': valueColumns})
                logging.debug('Storing %d rows to cache for log %s' % (len(rows), log))
            else:
                rows = cached_vals['rows']
                scenarioColumns = cached_vals['scenarioColumns']
                valueColumns = cached_vals['valueColumns']
                logging.debug('Loaded %d rows from cache' % len(rows))
            self.rows.extend(rows)
            self.scenarioColumns |= scenarioColumns
            self.valueColumns |= valueColumns

    def __iter__(self):
        """ Lets us do `for row in datatable` instead of 
            `for row in datatable.rows`.
        """
        return iter(self.rows)

    def loadCSV(self, log_path):
        """ Parses the CSV file at log_path into an array of DataRow objects.
            
            log_path: an absolute path to the log file to be parsed.
        """
        scenarios = {}
        value_cols = set()

        # Store the log's last modified date
        lastModified = os.path.getmtime(log_path)
        base_name = os.path.basename(log_path)
        
        reader = csv.DictReader(open(log_path, 'rb'))
        reader.fieldnames = map(str.lower, reader.fieldnames)
        for line in reader:
            key = line.pop('key')
            value = line.pop('value')
            if key not in value_cols:
                value_cols.add(key)
            line['logfile'] = str(base_name)
            schash = scenario_hash(line)
            if schash not in scenarios:
                scenarios[schash] = DataRow(line)
            scenarios[schash].values[key] = float(value)
        
        logging.debug('Parsed %d rows from CSV' % len(scenarios))
        scenario_cols = reader.fieldnames
        scenario_cols.remove('key')
        scenario_cols.remove('value')
        return scenarios.values(), lastModified, set(scenario_cols), value_cols

    def headers(self):
        """ Returns the headers that would be used to output a table of
            this data as two lists - scenario headers and value headers.
        """
        scenarios = list()
        values = list()
        values_with_ci = list()
        
        for row in self.rows:
            for key in row.scenario.iterkeys():
                if key not in scenarios:
                    scenarios.append(key)
            for key,val in row.values.items():
                if key not in values:
                    values.append(key)
                if isinstance(val, DataAggregate):
                    values_with_ci.append(key)

        return scenarios, values, values_with_ci
    
    def selectValueColumns(self, vals):
        """ Selects the specified set of value columns and throws away all
            others from each row in the table.
            
            vals: a list of value columns to keep.
        """
        for row in self.rows:
            for (key,val) in row.values.items():
                if key not in vals:
                    del row.values[key]
        self.valueColumns = set(vals)

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
            output += '<tr>'
            for key in scenarios:
                if key in row.scenario:
                    output += '<td>' + row.scenario[key] + '</td>'
                else:
                    output += '<td>*</td>'
            for key in values:
                if key in row.values:
                    output += '<td>' + present_value(row.values[key]) + '</td>'
                else:
                    output += '<td>*</td>'
            output += '</tr>'
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
        return 'Scenario: %s, Values = %s' % (self.scenario, self.values)


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
            n = len(self._values)
            self._stdev = math.sqrt( (1.0/(n-1)) * ( valSquareSum - (valSum * valSum / n) ) )

            ciDelta = stats.t.isf((1 - settings.CONFIDENCE_LEVEL) / 2, n) * self._stdev / math.sqrt(n)
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

    # Utility
    
    def sparkline(self):
        """ Creates a HTML IMG tag that contains a sparkline for this
            DataAggregate's values.
            
            From http://bitworking.org/news/Sparklines_in_data_URIs_in_Python
        """
        if not self._isValid:
            self._calculate()
        im = Image.new("RGB", (len(self._values)*2 + 2, 20), 'white')
        draw = ImageDraw.Draw(im)
        min_val = float(self._min)
        max_val = float(self._max)
        
        # Generate the set of coordinates
        if max_val == min_val:
            coords = map(lambda x: (x, 10), range(0, len(self._values)*2, 10))
        else:
            coords = zip(range(0, len(self._values)*2, 2), [15 - 10*(float(y)-min_val)/(max_val-min_val) for y in self._values])
        draw.line(coords, fill="#888888")
        
        # Draw the min and max points
        min_pt = coords[self._values.index(min_val)]
        draw.rectangle([min_pt[0]-1, min_pt[1]-1, min_pt[0]+1, min_pt[1]+1], fill="#00FF00")
        max_pt = coords[self._values.index(max_val)]
        draw.rectangle([max_pt[0]-1, max_pt[1]-1, max_pt[0]+1, max_pt[1]+1], fill="#FF0000")
        del draw

        # Write out as a data: URI
        f = StringIO.StringIO()
        im.save(f, "PNG")
        return '<img class="sparkline" src="data:image/png,%s" title="%s" />' % (urllib.quote(f.getvalue()), ", ".join(map(lambda v: str(float(v)), self._values)))
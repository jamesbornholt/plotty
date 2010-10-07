from django.core.cache import cache
import logging, sys, csv, os, math
from plotty import settings
from results.Utilities import present_value, scenario_hash
from scipy import stats
import Image, ImageDraw, StringIO, urllib


class DataTable:
    def __init__(self, logs):
        self.rows = []
        for log in logs:
            file_path = os.path.join(settings.BM_LOG_DIR, log)
            logging.debug('Attempting to load log %s from cache' % log)
            cached_vals = cache.get(log)
            file_last_modified = os.path.getmtime(file_path)
            if cached_vals == None or cached_vals['last_modified'] < file_last_modified:
                logging.debug('Cache empty or expired, reloading %s from file' % log)
                rows, lastModified = self.loadCSV(file_path)
                ret = cache.set(log, {'last_modified': lastModified, 'rows': rows})
                logging.debug('Storing %d rows to cache for log %s' % (len(rows), log))
            else:
                rows = cached_vals['rows']
                logging.debug('Loaded %d rows from cache' % len(rows))
            self.rows.extend(rows)

    def __iter__(self):
        return iter(self.rows)

    def loadCSV(self, log_path):
        scenarios = {}

        # Store the log's last modified date
        lastModified = os.path.getmtime(log_path)
        base_name = os.path.basename(log_path)
        
        reader = csv.DictReader(open(log_path, 'rb'))
        for line in reader:
            key = line.pop('key')
            value = line.pop('value')
            line['logfile'] = str(base_name) # Unicode!!
            schash = scenario_hash(line)
            if schash not in scenarios:
                scenarios[schash] = DataRow(line)
            scenarios[schash].values[key] = float(value)
        
        logging.debug('Parsed %d rows from CSV' % len(scenarios))
        return scenarios.values(), lastModified

    def headers(self):
        scenarios = list()
        values = list()
        for row in self.rows:
            for key in row.scenario.iterkeys():
                if key not in scenarios:
                    scenarios.append(key)
            for val in row.values.iterkeys():
                if val not in values:
                    values.append(val)
        return scenarios, values
    
    def selectValueColumns(self, vals):
        for row in self.rows:
            for (key,val) in row.values.items():
                if key not in vals:
                    del row.values[key]
    def selectScenarioColumns(self, cols):
        for row in self.rows:
            for (key,val) in row.scenario.items():
                if key not in cols:
                    del row.scenario[key]

    def renderToTable(self):
        scenarios, values = self.headers()
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

class DataRow:
    def __init__(self, scenario=None):
        if scenario == None:
            scenario = {}
        self.values = {}
        self.scenario = scenario


class DataAggregate:
    def __init__(self, newType):
        self.type = newType
        self._isValid = False
        self._values = []

    # Private methods
    
    def _calculate(self):
        # Calculates data for a single variable - compounds (A + B, A / B, etc)
        # are calculated by the appropriate operator overload (__add__, __div__)
        valSum = 0.0
        valProduct = 1.0
        valSquareSum = 0.0
        valMin = float('+inf')
        valMax = float('-inf')
        for val in self._values:
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
        if len(self._values) > 1:
            # http://en.wikipedia.org/wiki/Computational_formula_for_the_variance
            # Note x-bar = sum(x) / n
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
        self._values.append(value)
        self._isValid = False
    
    def map(self, func):
        self._isValid = False
        self._values = map(func, self._values)
    
    def setType(self, newType):
        self.type = newType
        self._isValid = False
    
    def manual(self, value, ciUp, ciDown, newMin, newMax):
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

    def __unicode__(self):
        if not self._isValid:
            self._calculate()
        if math.isnan(self._ciUp):
            return "%.3f" % self._value
        else:
            return "%.3f (%.3f, %.3f)" % (self._value, self._ciDown, self._ciUp)

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
        if isinstance(other, DataAggregate):
            res = DataAggregate(self.type)
            val = self.value() / other.value()
            # Motulsky, 'Intuitive Biostatistics', pp285-6
            tinv = stats.t.isf((1 - settings.CONFIDENCE_LEVEL) / 2, self.count() + other.count() - 2)
            g = (tinv * (other.sem() / other.value()))**2
            if g >= 1.0:
                ciUp = ciDown = float('nan')
            else:
                sem = ( val / (1-g) ) * math.sqrt((1-g) * (self.sem() / self.value())**2 + (other.sem() / other.value()) ** 2)
                ciUp = ( val / (1-g) ) + tinv*sem
                ciDown = ( val / (1-g) ) - tinv*sem
            valMin = self.min() / other.max()
            valMax = self.max() / other.min()
            
            res.manual(value=val, ciUp=ciUp, ciDown=ciDown, newMin=valMin, newMax=valMax)
            return res
        else:
            # This is a special case that probably doesn't need to be covered
            res = copy.copy(self)
            res.map(lambda d: d / other)
            return res

    # Sparkline
    
    def sparkline(self):
        """ From http://bitworking.org/news/Sparklines_in_data_URIs_in_Python """
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
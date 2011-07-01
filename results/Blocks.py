"""
This module defines the blocks available to a pipeline, and their functionality.
Every block is a subclass of the Block class, which defines two basic methods
which it describes.
"""

import math, copy, os
from plotty.results.DataTypes import DataRow, DataAggregate
from plotty.results.Utilities import present_value, present_value_csv_graph, scenario_hash
from plotty.results.Exceptions import PipelineAmbiguityException, PipelineError, PipelineBlockException
import plotty.results.PipelineEncoder as PipelineEncoder
from plotty import settings
import logging


class Block(object):
    """ The base object for blocks. Defines methods all blocks should implement.
    """
    def decode(self, param_string):
        """ Decodes a paramater string and stores the configuration in local
            fields. """
        pass
    
    def apply(self, data_table):
        """ Apply this block to the data_table. data_table is passed by reference,
            so this method does not return.

            Can throw PipelineAmbiguityException or PipelineBlockException. """
        pass


class FilterBlock(Block):
    """ Filters the datatable by including or excluding particular rows based
        on criteria. The rows that do not match every filter are thrown out 
        (that is, the list of filters is ANDed together). """

    TYPE = {
        'IS': '1',
        'IS_NOT': '2'
    }

    def __init__(self):
        """ Define the single instance variable of a FilterBlock.
        
        filters:  An array of dictionaries describing the filters to be applied.
        Each filter has three properties:
         * column -- the scenario column to be checked (string)
         * value  -- the value the specified scenario column should
                     take
         * is     -- if true, each row must have the specified scenario
                     column set to the specified value. If false, each
                     row must *not* have the specified column set to
                     the specified value.
        """
        super(FilterBlock, self).__init__()

        self.filters = []


    def decode(self, param_string):
        """ Decode a filter block from an encoded pipeline string.
            Filter blocks are encoded in the form:
            filter1scenario^filter1is^filter1value&filter2scenario^...
        """
        filts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        for filt_str in filts:
            parts = filt_str.split(PipelineEncoder.PARAM_SEPARATOR)
            self.filters.append({
                'scenario': parts[0],
                'is':       (parts[1] == FilterBlock.TYPE['IS']),
                'value':    parts[2]
            })

    def apply(self, data_table):
        """ Apply this block to the given data table.
        """
        new_rows = []
        removed_scenario_cols = set()
        for filt in self.filters:
            if filt['is']:
                removed_scenario_cols.add(filt['scenario'])

        for row in data_table:
            add = True
            for filt in self.filters:
                if filt['is']:
                    if filt['scenario'] not in row.scenario or row.scenario[filt['scenario']] != filt['value']:
                        add = False
                        break
                else:
                    if filt['scenario'] in row.scenario and row.scenario[filt['scenario']] == filt['value']:
                        add = False
                        break
            if add:
                # Delete the scenario columns
                for col in removed_scenario_cols:
                    if col in row.scenario:
                        del row.scenario[col]
                new_rows.append(row)

        # We do it this way because calling .remove(x) on a set raises a key
        # value error if it wasn't in the set
        removed_scenario_cols = set()
        for filt in self.filters:
            if filt['is']:
                removed_scenario_cols.add(filt['scenario'])
        
        data_table.scenarioColumns -= removed_scenario_cols
        data_table.rows = new_rows


class AggregateBlock(Block):
    """ Aggregates the rows in the DataTable by grouping them based on a
        specified column. Every row that has the same scenario except for
        the value in the specified column is grouped together and turned into
        a DataAggregate object. That is, every row whose scenario differs only
        in the specified column is grouped together.
        
        datatable: the DataTable object to be aggregated, passed by reference.
        Keyword arguments:
        * column -- the column on which the aggregate is performed (i.e. the
                    column which is ignored when regrouping rows).
        * type   -- the type of aggregate to generate, either 'mean' or 'geomean'
    """

    TYPE = {
        '1': 'mean',
        '2': 'geomean'
    }

    def __init__(self):
        super(AggregateBlock, self).__init__()
        self.column = None
        self.type = None

    def decode(self, param_string):
        """ Decode an aggregate block from an encoded pipeline string.
            Aggregate blocks are encoded in the form:
            1&column
            where the number is the TYPE chosen, and column is the scenario
            column.
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        self.type = parts[0]
        self.column = parts[1]

    def apply(self, data_table):
        """ Apply this block to the given data table.
        """
        groups = {}
        basescenarios = set()
        scenarios = {}
        ignored_rows = 0
        # Group the rows based on their scenarios except for the specified column
        for row in data_table:
            if self.column not in row.scenario:
                ignored_rows += 1
                continue
            schash = scenario_hash(scenario=row.scenario)
            if schash in basescenarios:
              raise PipelineAmbiguityException("Base scenario not unique %s" % row.scenario)
            else:
              basescenarios.add(schash)
            schash = scenario_hash(scenario=row.scenario, exclude=[self.column])
            if schash not in scenarios:
                groups[schash] = []
                scenarios[schash] = copy.copy(row.scenario)
                del scenarios[schash][self.column]
            groups[schash].append(row.values)
        
        # Create the DataAggregate objects for each group
        new_rows = []
        for (scenario, rows) in groups.items():
            aggregates = {}
            for row in rows:
                for (key, val) in row.items():
                    if key not in aggregates:
                        aggregates[key] = DataAggregate(AggregateBlock.TYPE[self.type])
                    aggregates[key].append(val)
            new_row = DataRow()
            new_row.scenario = scenarios[scenario]
            new_row.values = aggregates
            new_rows.append(new_row)
        
        data_table.rows = new_rows
        data_table.scenarioColumns -= set([self.column])
        if ignored_rows > 0:
            logging.info('Aggregate block (%s over %s) ignored %d rows.', self.type, self.column, ignored_rows)



class NormaliseBlock(Block):
    """ Normalises the rows in the DataTable to a specified value. The
        normalisation can be performed in two ways - either by specifying a
        normaliser to be used, or by finding the best value in a group and
        normalising to that. Before normalising, values are grouped based on
        the equivalence of their scenarios. The columns compared in doing this
        grouping can be specified.
        
        datatable: the DataTable to be normalised, passed by reference.
        Keyword arguments:
        * normaliser -- the type of normalisation to perform.
          [other arguments determined by this value - see methods below]
    """

    TYPE = {
        'SELECT': '1',
        'BEST': '2'
    }

    def __init__(self):
        super(NormaliseBlock, self).__init__()

        self.group = []
        self.type = None
        self.normaliser = []

    def decode(self, param_string):
        """ Decode a normalise block from an encoded pipeline string.
            Normalise blocks are encoded in the form:
            0&scenario^value&scenario^value&groupscenario&groupscenario
            We distinguish between selected normalisers and group scenarios
            by the presence of the ^ character.
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        self.type = parts[0]
        if self.type == NormaliseBlock.TYPE['SELECT']:
            for part in parts[1:]:
                if PipelineEncoder.PARAM_SEPARATOR in part:
                    vals = part.split(PipelineEncoder.PARAM_SEPARATOR)
                    self.normaliser.append({
                        'scenario': vals[0],
                        'value':    vals[1]
                    })
                elif part != '':
                    self.group.append(part)
        else:
            self.group = [s for s in parts[1:] if s != '']
    
    def apply(self, data_table):
        """ Apply this block to the given data table.
        """

        ignored_rows = []
        no_normaliser_rows = []

        groups = {}

        # Group the rows up as needed
        for row in data_table:
            # Check if all the group columns are defined
            skip = False
            for key in self.group:
                if key not in row.scenario:
                    skip = True
                    break
            if skip:
                ignored_rows.append(row)
                continue
            
            # Hash the scenario and insert it into its group
            sc_hash = scenario_hash(scenario=row.scenario, include=self.group)
            if sc_hash not in groups:
                groups[sc_hash] = []
            groups[sc_hash].append(row)

        # Get a set of normalisers
        normalisers = {}
        if self.type == NormaliseBlock.TYPE['SELECT']:
            normalisers = self.processSelectNormaliser(groups)
        elif self.type == NormaliseBlock.TYPE['BEST']:
            normalisers = self.processBestNormaliser(groups)

        # Perform the normalisation
        new_rows = []
        for (scenario, rows) in groups.iteritems():
            if scenario not in normalisers:
                no_normaliser_rows.extend(rows)
                continue
            for row in rows:
                for key in row.values.keys():
                    if key in normalisers[scenario]:
                        row.values[key] = row.values[key] / normalisers[scenario][key]
                    else:
                        del row.values[key]
            new_rows.extend(rows)
        
        # Wrap it all up
        data_table.rows = new_rows

        if len(ignored_rows) > 0:
            logging.info("Normaliser block ignored %d rows because they were missing a scenario column from the selected grouping", len(ignored_rows))
        if len(no_normaliser_rows) > 0:
            logging.info("Normaliser block ignored %d rows because no normaliser existed for them", len(no_normaliser_rows))

    def processSelectNormaliser(self, groups):
        """ Normalises the rows to a specified normaliser. The normaliser is
            specified by a column and value in the scenario of each row. Rows
            in the table are first grouped by every column except the one chosen
            for normalisation. Then in each group, a normaliser is found with
            the normaliser column equal to the specified value. Each group is
            then normalised to the chosen normaliser. Groups for which no
            normaliser exists are thrown away.
            
            datatable: the DataTable to be normalised, passed by reference.
            Keyword arguments:
            * column -- the column from which the normaliser will be decided.
            * value  -- the value which the specified column should be equal to
                        in order to select that row as a normaliser.
        """
        
        normalisers = {}

        select_ignored_rows = []

        for (scenario, rows) in groups.iteritems():
            for (i, row) in enumerate(rows):
                match = True
                for selection in self.normaliser:
                    if selection['scenario'] not in row.scenario:
                        select_ignored_rows.append(row)
                        del rows[i]
                        match = False
                        break
                    elif row.scenario[selection['scenario']] != selection['value']:
                        match = False
                        break
                if match:
                    if scenario not in normalisers:
                        normalisers[scenario] = copy.copy(row.values)
                    else:
                        raise PipelineAmbiguityException('More than one normaliser was found for the scenario %s. Both <pre>%s</pre> and <pre>%s</pre> were valid normalisers. Did you forget to set the right grouping for normalisation?' % (row.scenario, normalisers[scenario], row.values))
        
        if len(select_ignored_rows) > 0:
            logging.info("Normaliser block ignored %d rows because they were missing a scenario column from the selected normaliser", len(select_ignored_rows))

        return normalisers
  
    def processBestNormaliser(self, groups):
        """ Normalises the rows to the best normaliser available. The rows in the
            table are firstly grouped by comparing their scenarios only on the
            specified columns. Then the best value in each group is found and
            used to normalise the other rows in that group.
            
            datatable: the DataTable to be normalised, passed by reference.
            Keyword arguments:
            * group -- a list of scenario columns which should be used for
                       grouping the rows before normalisation.
        """

        normalisers = {}

        for (scenario, rows) in groups.iteritems():
            normaliser = {}
            for row in rows:
                for (key, val) in row.values.items():
                    if float(val) != 0 and float(val) < normaliser.get(key, float('inf')):
                        normaliser[key] = val
            normalisers[scenario] = normaliser

        return normalisers


class GraphBlock(Block):
    """ Generate graphs based on the data in the DataTable. """
    
    TYPE = {
        'HISTOGRAM': '1',
        'XY': '2',
        'SCATTER': '3'
    }

    def __init__(self):
        self.type = None
        self.column = None
        self.row = None
        self.value = None
        self.x = None
        self.y = None

    def decode(self, param_string):
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        self.type = parts[0]
        if self.type == GraphBlock.TYPE['HISTOGRAM']:
            self.column = parts[1]
            self.row = parts[2]
            self.value = parts[3]
        elif self.type == GraphBlock.TYPE['XY']:
            self.column = parts[1]
            self.row = parts[2]
            self.value = parts[3]
        elif self.type == GraphBlock.TYPE['SCATTER']:
            self.x = parts[1]
            self.y = parts[2]

    def pivot(self, rows):
        """ Pivot a set of rows based on the settings in this block. """
        pivot_rows = {}
        column_keys = set()
        # We aggregate by column - every column has a min, max, mean, geomean,
        # and count
        mins = {}
        maxs = {}
        sums = {}
        products = {}
        counts = {}

        for row in rows:
            # Check if we've got any pivoted results for this row
            if row.scenario[self.row] not in pivot_rows:
                pivot_rows[row.scenario[self.row]] = {}
            # Check if this is a column we haven't seen before
            if row.scenario[self.column] not in column_keys:
                column_keys.add(row.scenario[self.column])
                mins[row.scenario[self.column]] = float('+inf')
                maxs[row.scenario[self.column]] = float('-inf')
                sums[row.scenario[self.column]] = 0
                products[row.scenario[self.column]] = 1
                counts[row.scenario[self.column]] = 0
            
            # If there's already a value in this cell, we have am ambiguity
            if row.scenario[self.column] in pivot_rows[row.scenario[self.row]]:
                raise PipelineAmbiguityException('More than one value exists for the graph cell (%s=%s, %s=%s)' % (self.row, row.scenario[self.row], self.column, row.scenario[self.column]))
            # Populate this cell
            pivot_rows[row.scenario[self.row]][row.scenario[self.column]] = row.values[self.value]
            
            # Check for new min/max and update the aggregates
            if float(row.values[self.value]) < mins[row.scenario[self.column]]:
                mins[row.scenario[self.column]] = float(row.values[self.value])
            if float(row.values[self.value]) > maxs[row.scenario[self.column]]:
                maxs[row.scenario[self.column]] = float(row.values[self.value])
            sums[row.scenario[self.column]] += float(row.values[self.value])
            products[row.scenario[self.column]] *= float(row.values[self.value])
            counts[row.scenario[self.column]] += 1
        
        aggregates = {
            'min': mins,
            'max': maxs,
            'mean': {},
            'geomean': {}
        }
        for key in column_keys:
            if counts[key] > 0:
                aggregates['mean'][key] = sums[key] / counts[key]
                aggregates['geomean'][key] = math.pow(products[key], 1.0/counts[key])
            else:
                aggregates['mean'][key] = 0
                aggregates['geomean'][key] = 1
        
        return pivot_rows, aggregates, column_keys

    def group(self, data_table):
        """ Split the rows in the datatable into groups based on the
            cross-product of their scenario columns (apart from those used as
            column or row) """
        
        sets = {}
        scenario_keys = {}
        for row in data_table:
            if self.column in row.scenario and self.row in row.scenario and self.value in row.values:
                schash = scenario_hash(row.scenario, exclude=[self.column, self.row])
                if schash not in scenario_keys:
                    scenario = copy.copy(row.scenario)
                    del scenario[self.column]
                    del scenario[self.row]
                    scenario_keys[schash] = scenario
                if schash not in sets:
                    sets[schash] = []
                sets[schash].append(row)
        
        return sets, scenario_keys

    def renderCSV(self, pivot_table, column_keys, row_keys, aggregates=None, for_gnuplot=False):
        # Look for DataAggregates. We can't just check the first one because it
        # may not exist.
        has_cis = for_gnuplot
        for row in pivot_table.itervalues():
            if has_cis:
                break
            for key in column_keys:
                if key in row and isinstance(row[key], DataAggregate):
                    has_cis = True
                    break
        
        # Build the header row
        output = '"' + self.row + '",'
        for key in column_keys:
            output += '"' + key + '",'
            if has_cis:
                output += '"' + key + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.lowerBound",'
                output += '"' + key + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.upperBound",'
        # Truncate the last comma to be clear
        if output[-1] == ',':
            output = output[:-1]
        output += "\r\n"
        
        # Build the rows
        for row_name in row_keys:
            output += '"' + row_name + '",'
            for key in column_keys:
                if key in pivot_table[row_name]:
                    val = pivot_table[row_name][key]
                    if has_cis:
                        if isinstance(val, DataAggregate):
                            ciDown, ciUp = val.ci()
                            if math.isnan(ciDown):
                                output += '%f,%f,%f,' % ((val.value(),)*3)
                            else:
                                output += '%f,%f,%f,' % (val.value(), ciDown, ciUp)
                        else:
                            output += '%f,%f,%f,' % ((val,)*3)
                    else :
                        output += '%f,' % (val.value())
                else:
                    if has_cis:
                        output += '"","","",'
                    else:
                        output += '"",'
            
            # Truncate the last comma to be clear
            if output[-1] == ',':
                output = output[:-1]
            output += "\r\n"

        if aggregates != None:
            for agg in ['min', 'max', 'mean', 'geomean']:
                output += '"' + agg + '",'
                for key in column_keys:
                    if key in aggregates[agg]:
                        if has_cis:
                            # gnuplot expects non-empty data, with error cols containing the absolute val
                            # of the error (e.g. a val of 1.3 with CI of 1.25-1.35 needs to report
                            # 1.3,1.25,1.35 to gnuplot)
                            if for_gnuplot:
                                output += '%f,%f,%f,' % (aggregates[agg][key], aggregates[agg][key], aggregates[agg][key])
                            else:
                                output += '%f,,,' % aggregates[agg][key]
                        else:
                            output += '%f,' % aggregates[agg][key]
                    else:
                        if has_cis:
                            output += '0,0,0,'
                        else:
                            output += '0,'
                # Truncate the last comma to be clear
                if output[-1] == ',':
                    output = output[:-1]
                output += "\r\n"            
        
        return output

    def renderHTML(self, pivot_table, column_keys, row_keys, graph_hash, aggregates=None):
        #output  = '<img src="graph/' + graph_hash + '.svg" />'
        output  = '<object width=100% data="graph/' + graph_hash + '.svg" type="image/svg+xml"></object>'
        output += '<p>Download: '
        output += '<a href="graph/' + graph_hash + '.csv">csv</a> '
        output += '<a href="graph/' + graph_hash + '.gpt">gpt</a> '
        output += '<a href="graph/' + graph_hash + '.svg">svg</a> '
        output += '<a href="graph/' + graph_hash + '.pdf">pdf</a> '
        output += '<a href="graph/' + graph_hash + '.wide.pdf">wide pdf</a>'
        output += '</p>'
        output += '<table><thead><tr><th>' + self.row + '</th>'
        for key in column_keys:
            output += '<th>' + self.column + '=' + key + '</th>'
        output += '</tr></thead><tbody>'
        for row_name in row_keys:
            output += '<tr><td>' + row_name + '</td>'
            for key in column_keys:
                if key in pivot_table[row_name]:
                    output += '<td>' + present_value(pivot_table[row_name][key]) + '</td>'
                else:
                    output += '<td>*</td>'
            output += '</tr>'
        output += '<tr><td>&nbsp;</td></tr>'
        if aggregates != None:
            for agg in ['min', 'max', 'mean', 'geomean']:
                output += '<tr><td><i>' + agg + '</i></td>'
                for key in column_keys:
                    if key in aggregates[agg]:
                        output += '<td>%.3f</td>' % aggregates[agg][key]
                    else:
                        output += '<td>*</td>'
                output += '</tr>'
        output += '</tbody></table>'

        return output

    def apply(self, data_table):
        """ Render the graph to HTML, including images """
        if self.type == GraphBlock.TYPE['HISTOGRAM'] or self.type == GraphBlock.TYPE['XY']:
            sets, scenario_keys = self.group(data_table)
            graphs = {}
            for (scenario, rows) in sets.iteritems():
                # Pivot the data
                pivot_table, aggregates, column_keys = self.pivot(rows)
                
                # Sort the column and keys so they show nicely in the graph
                column_keys = list(column_keys)
                row_keys = pivot_table.keys()
                try:
                    row_keys.sort(key=float)
                except ValueError:
                    row_keys.sort(key=str.lower)
                
                try:
                    column_keys.sort(key=float)
                except ValueError:
                    column_keys.sort(key=str.lower)
                
                # Generate a hash for this graph
                graph_hash = str(abs(hash(str(id(self)) + scenario)))
                graph_path = os.path.join(settings.GRAPH_CACHE_DIR, graph_hash)
                
                # If the csv doesn't exist or is out of date (the data_table has
                # logs newer than it), replot the data
                csv_last_modified = 0 
                if os.path.exists(graph_path + '.csv'):
                    csv_last_modified = os.path.getmtime(graph_path + '.csv')
                if csv_last_modified <= data_table.lastModified:
                    # Render the CSV
                    csv = self.renderCSV(pivot_table, column_keys, row_keys, aggregates, for_gnuplot=True)
                    csv_file = open(graph_path + '.csv', "w")
                    csv_file.write(csv)
                    csv_file.close()
    
                    # Plot the graph
                    if self.type == GraphBlock.TYPE['HISTOGRAM']:
                        self.plotHistogram(graph_path, len(column_keys))
                    elif self.type == GraphBlock.TYPE['XY']:
                        self.plotXYGraph(graph_path, len(column_keys))
                
                # Render the HTML!
                html = self.renderHTML(pivot_table, column_keys, row_keys, graph_hash, aggregates)
                
                title = "Graph"
                if len(scenario_keys[scenario]) > 0:
                    title = ', '.join([k + ' = ' + scenario_keys[scenario][k] for k in scenario_keys[scenario].keys()])
                
                graphs[title] = html
            
            return graphs
        elif self.type == GraphBlock.TYPE['SCATTER']:
            # XXX TODO: this cache key doesn't work; we should implement a
            # cache key method on DataTable
            graph_hash = str(abs(hash(str(id(self)) + self.x + self.y)))
            graph_path = os.path.join(settings.GRAPH_CACHE_DIR, graph_hash)

            csv_last_modified = 0
            if os.path.exists(graph_path + '.csv'):
                csv_last_modified = os.path.getmtime(graph_path + '.csv')
            if csv_last_modified <= data_table.lastModified:
                # Render the CSV. We assume the data has confidence intervals
                # - if not, we just emit the same value three times,
                # so in gnuplot we can always use the same code.
                csv = ['"' + self.x + '","' + self.x + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.lowerBound","' + \
                       self.x + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.upperBound",' + \
                       '"' + self.y + '","' + self.y + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.lowerBound","' + \
                       self.y + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.upperBound"']
                for row in data_table:
                    if self.x in row.values and self.y in row.values:
                        csv.append(present_value_csv_graph(row.values[self.x], True) + ',' + present_value_csv_graph(row.values[self.y], True))
                csv_text = "\n".join(csv)

                csv_file = open(graph_path + '.csv', 'w')
                csv_file.write(csv_text)
                csv_file.close()

                # Plot the graph
                self.plotScatterGraph(graph_path)
            
            html = ['<object width=100% data="graph/' + graph_hash + '.svg" type="image/svg+xml"></object>' + \
                    '<p>Download: ' + \
                    '<a href="graph/' + graph_hash + '.csv">csv</a> ' + \
                    '<a href="graph/' + graph_hash + '.gpt">gpt</a> ' + \
                    '<a href="graph/' + graph_hash + '.svg">svg</a> ' + \
                    '<a href="graph/' + graph_hash + '.pdf">pdf</a> ' + \
                    '<a href="graph/' + graph_hash + '.wide.pdf">wide pdf</a>' + \
                    '</p>' + \
                    '<table><thead><tr><th>' + self.x + '</th><th>' + self.y + '</th></tr></thead><tbody>']
            for row in data_table:
                if self.x in row.values and self.y in row.values:
                    html.append('<tr><td>' + present_value(row.values[self.x]) + '</td><td>' + present_value(row.values[self.y]) + '</td></tr>')
            html.append('</tbody></table>')
            html_text = "\n".join(html)

            return {'Scatter graph': html_text}

    
    def plotXYGraph(self, graph_path, num_cols):
        """ Plot a histogram csv file with gnuplot.
        
        csv_filename: the csv file where the graph data has been temporarily
                      stored.
        num_cols:     the number of columns of data (not including error bars)
        """
        num_cols = num_cols * 3 - 1
        gnuplot = """
set terminal svg fname "Arial" fsize 10 size 960,420
set output '{graph_path}.svg'
set datafile separator ","
set ylabel "{yaxis_title}"
set xtics out
set ytics out
set xtics nomirror
set ytics nomirror
set key bottom left outside horizontal

set nobox
set auto x
set style data linespoints
#set style linespoints errorbars gap 1 lw 0.25
set bars .5
set style fill solid 1.0 border -1
set boxwidth 1
set xtic rotate by -30
set key reverse Left spacing 1.35

set style line 20 lt 1 pt 0 lc rgb '#000000' lw 0.25
set grid linestyle 20
set grid noxtics
set style line 1 lt 1 pt 0 lc rgb '#82CAFA' lw 1
set style line 2 lt 1 pt 0 lc rgb '#4CC417' lw 1
set style line 3 lt 1 pt 0 lc rgb '#ADDFFF' lw 1

plot for [COL=2:{num_cols}:3] "{graph_path}.csv" u 1:COL:xtic(1) title col(COL) w lines, for [COL=2:{num_cols}:3] "" u 1:COL:COL+1:COL+2 notitle w yerr

set terminal postscript eps solid color "Helvetica" 18 size 5, 2.5
set output '{graph_path}.eps'
replot

set terminal postscript eps solid color "Helvetica" 18 size 10, 2.2
set output '{graph_path}.wide.eps'
replot
"""
        gp_file = open(graph_path + ".gpt", "w")
        gp_file.write(gnuplot.format(graph_path=graph_path, num_cols=num_cols, yaxis_title=self.value, font_path=settings.GRAPH_FONT_PATH))
        gp_file.close()
        os.system(settings.GNUPLOT_EXECUTABLE + ' ' + gp_file.name)
        os.system("ps2pdf -dEPSCrop " + graph_path + ".wide.eps " + graph_path + ".wide.pdf")
        os.system("ps2pdf -dEPSCrop " + graph_path + ".eps " + graph_path + ".pdf")


    def plotHistogram(self, graph_path, num_cols):
        """ Plot a histogram csv file with gnuplot.
        
        csv_filename: the csv file where the graph data has been temporarily
                      stored.
        num_cols:     the number of columns of data (not including error bars)
        """
        num_cols = num_cols * 3 - 1
        gnuplot = """
set terminal svg fname "Arial" fsize 10 size 960,420
set output '{graph_path}.svg'
set datafile separator ","
set ylabel "{yaxis_title}"
set xtics out
set ytics out
set xtics nomirror
set ytics nomirror
set key bottom left outside horizontal

set nobox
set auto x
set style data histogram
set style histogram errorbars gap 1 lw 0.25
set bars .5
set style fill solid 1.0 border -1
set boxwidth 1
set xtic rotate by -30
set key reverse Left spacing 1.35

set style line 20 lt 1 pt 0 lc rgb '#000000' lw 0.25
set grid linestyle 20
set grid noxtics
set style line 1 lt 1 pt 0 lc rgb '#82CAFA' lw 1
set style line 2 lt 1 pt 0 lc rgb '#4CC417' lw 1
set style line 3 lt 1 pt 0 lc rgb '#ADDFFF' lw 1

plot for [COL=2:{num_cols}:3] "{graph_path}.csv" u COL:COL+1:COL+2:xtic(1) title col(COL)

set terminal postscript eps solid color "Helvetica" 18 size 5, 2.5
set output '{graph_path}.eps'
replot

set terminal postscript eps solid color "Helvetica" 18 size 10, 2.2
set output '{graph_path}.wide.eps'
replot
"""
        gp_file = open(graph_path + ".gpt", "w")
        gp_file.write(gnuplot.format(graph_path=graph_path, num_cols=num_cols, yaxis_title=self.value, font_path=settings.GRAPH_FONT_PATH))
        gp_file.close()
        os.system(settings.GNUPLOT_EXECUTABLE + ' ' + gp_file.name)
        os.system("ps2pdf -dEPSCrop " + graph_path + ".wide.eps " + graph_path + ".wide.pdf")
        os.system("ps2pdf -dEPSCrop " + graph_path + ".eps " + graph_path + ".pdf")
    
    def plotScatterGraph(self, graph_path):
        """ Plot a scatter plot csv file with gnuplot.

        graph_path: the path to the graph (append with .csv to get the csv file)
        """
        gnuplot = """
set terminal svg fname "Arial" fsize 10 size 960,420
set output '{graph_path}.svg'
set datafile separator ","
set xlabel "{xaxis_title}"
set ylabel "{yaxis_title}"
set xtics out
set ytics out
set xtics nomirror
set ytics nomirror
set nokey

set nobox
set auto x
set style data dots

#set style line 20 lt 1 pt 0 lc rgb '#000000' lw 0.25
#set grid linestyle 20
#set grid noxtics
#set style line 1 lt 1 pt 0 lc rgb '#82CAFA' lw 1
#set style line 2 lt 1 pt 0 lc rgb '#4CC417' lw 1
#set style line 3 lt 1 pt 0 lc rgb '#ADDFFF' lw 1

plot "{graph_path}.csv" u 1:4 title "Scatter plot" with points

set terminal postscript eps solid color "Helvetica" 18 size 5, 2.5
set output '{graph_path}.eps'
replot

set terminal postscript eps solid color "Helvetica" 18 size 10, 2.2
set output '{graph_path}.wide.eps'
replot
"""
        gp_file = open(graph_path + '.gpt', 'w')
        gp_file.write(gnuplot.format(graph_path=graph_path, xaxis_title=self.x, yaxis_title=self.y, font_path=settings.GRAPH_FONT_PATH))
        gp_file.close()
        os.system(settings.GNUPLOT_EXECUTABLE + ' ' + gp_file.name)
        os.system("ps2pdf -dEPSCrop " + graph_path + ".wide.eps " + graph_path + ".wide.pdf")
        os.system("ps2pdf -dEPSCrop " + graph_path + ".eps " + graph_path + ".pdf")

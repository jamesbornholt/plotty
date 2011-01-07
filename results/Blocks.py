import math, copy, tempfile
from results.DataTypes import *
from results.Utilities import present_value, scenario_hash
from plotty import settings
import logging

class PipelineAmbiguityException(Exception):
    def __init__(self, msg, block=-1):
        self.block = block
        self.msg = msg

class FilterBlock:
    """ Filters the datatable by including or excluding particular rows based
        on criteria. The rows that do not match every filter are thrown out 
        (that is, the list of filters is ANDed together).
        
        datatable: the DataTable object to be filtered, passed by reference.
        filters:   an array of dictionaries describing the filters to be applied.
                   Each filter has three properties:
                    * column -- the scenario column to be checked (string)
                    * value  -- the value the specified scenario column should
                                take
                    * is     -- if true, each row must have the specified scenario
                                column set to the specified value. If false, each
                                row must *not* have the specified column set to
                                the specified value.
    """
    def process(self, datatable, filters):
        newRows = []
        for row in datatable:
            add = True
            for filt in filters:
                if filt['is']:
                    if filt['column'] not in row.scenario or row.scenario[filt['column']] <> filt['value']:
                        add = False
                        break
                else:
                    if filt['column'] in row.scenario and row.scenario[filt['column']] == filt['value']:
                        add = False
                        break
            if add:
                # Delete each of the `is` columns from the datatable, as they are
                # now redundant (since every row will have the same value).
                removeScenarioColumns = set()
                for filt in filters:
                    if filt['is']:
                        del row.scenario[filt['column']]
                        removeScenarioColumns.add(filt['column'])
                datatable.scenarioColumns -= removeScenarioColumns
                newRows.append(row)

        datatable.rows = newRows


class AggregateBlock:
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
    def process(self, datatable, **kwargs):
        groups = {}
        scenarios = {}
        ignored_rows = 0
        # Group the rows based on their scenarios except for the specified column
        for row in datatable:
            if kwargs['column'] not in row.scenario:
                ignored_rows += 1
                continue
            schash = scenario_hash(scenario=row.scenario, exclude=[kwargs['column']])
            if schash not in scenarios:
                groups[schash] = []
                scenarios[schash] = copy.copy(row.scenario)
                del scenarios[schash][kwargs['column']]
            groups[schash].append(row.values)
        
        # Create the DataAggregate objects for each group
        newRows = []
        for (sc, rows) in groups.items():
            aggregates = {}
            for row in rows:
                for (key,val) in row.items():
                    if key not in aggregates:
                        aggregates[key] = DataAggregate(kwargs['type'])
                    aggregates[key].append(val)
            newRow = DataRow()
            newRow.scenario = scenarios[sc]
            newRow.values = aggregates
            newRows.append(newRow)
        
        datatable.rows = newRows
        datatable.scenarioColumns -= set([kwargs['column']])
        if ignored_rows > 0:
            logging.info('Aggregate block (%s over %s) ignored %d rows.' % (kwargs['type'], kwargs['column'], ignored_rows))


class NormaliseBlock:
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
    def process(self, datatable, **kwargs):
        if kwargs['normaliser'] == 'select':
            self.processSelectNormaliser(datatable, **kwargs)
        elif kwargs['normaliser'] == 'best':
            self.processBestNormaliser(datatable, **kwargs)
        
    def processSelectNormaliser(self, datatable, **kwargs):
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
        # Handle a parsing bug when constructing the dictionary
        if kwargs['group'] == ['']:
            kwargs['group'] = []
        
        # Build the groups for normalisation and find a normaliser for each one
        scenarios = {}
        normalisers = {}
        ignored_rows = 0

        for row in datatable:
            throw = False
            for selection in kwargs['selection']:
                if selection['column'] not in row.scenario:
                    ignored_rows += 1
                    throw = True
                    break
            if throw:
                continue
            
            schash = scenario_hash(scenario=row.scenario, include=kwargs['group'])
            if schash not in scenarios:
                scenarios[schash] = []
            scenarios[schash].append(row)
            match = True
            for selection in kwargs['selection']:
                if row.scenario[selection['column']] <> selection['value']:
                    match = False
                    break
            if match:
                if schash not in normalisers:
                    normalisers[schash] = copy.copy(row.values)
                else:
                    raise PipelineAmbiguityException('More than one normaliser was found for the scenario %s.' % row.scenario)
        
        newRows = []
        
        # Normalise each group based on the found normaliser and collect the new
        # rows.
        no_normaliser_rows = 0
        for (sc, rows) in scenarios.items():
            # Throw away groups which do not have a normaliser
            if sc not in normalisers:
                no_normaliser_rows += len(rows)
                for row in rows:
                    row.values = {}
                trashed_rows.extend(rows)
                continue
            # Normalise each value in each row
            for row in rows:
                for (key,val) in row.values.items():
                    if key not in normalisers[sc]:
                        del row.values[key]
                        continue
                    row.values[key] = row.values[key] / normalisers[sc][key]
            newRows.extend(rows)
        
        datatable.rows = newRows
        if ignored_rows > 0:
            logging.info('Normalise block (to normaliser %s) ignored %d rows because they did not have a value for some column in the normaliser.' % (kwargs['selection'], ignored_rows))
        if no_normaliser_rows > 0:
            logging.info('Normalise block (to normaliser %s) ignored %d rows because no normaliser existed for them.' % (kwargs['selection'], no_normaliser_rows))
    
    def processBestNormaliser(self, datatable, **kwargs):
        """ Normalises the rows to the best normaliser available. The rows in the
            table are firstly grouped by comparing their scenarios only on the
            specified columns. Then the best value in each group is found and
            used to normalise the other rows in that group.
            
            datatable: the DataTable to be normalised, passed by reference.
            Keyword arguments:
            * group -- a list of scenario columns which should be used for
                       grouping the rows before normalisation.
        """
        scenarios = {}
        normalisers = {}
        ignored_rows = 0
        
        # Handle a parsing bug when constructing the dictionary
        if kwargs['group'] == ['']:
            kwargs['group'] = []
        
        # Build the groups to be used and find a normaliser for each one
        for row in datatable:
            # If the row does not have values for each scenario column to be used
            # for grouping, it is discarded
            throw = False
            for key in kwargs['group']:
                if key not in row.scenario:
                    throw = True
                    break
            if throw:
                ignored_rows += 1
                continue
            
            schash = scenario_hash(scenario=row.scenario, include=kwargs['group'])
            if schash not in scenarios:
                scenarios[schash] = []
                normalisers[schash] = {}
            # Add the row to its group
            scenarios[schash].append(row)
            # Check if it is the best normaliser
            for (key,val) in row.values.items():
                if float(val) <> 0 and val < normalisers[schash].get(key, float('inf')):
                    normalisers[schash][key] = val
        
        newRows = []
        
        # Normalise each group based on the found normaliser and collect the new
        # rows.
        no_normaliser_rows = 0
        for (sc, rows) in scenarios.items():
            # Throw away groups which do not have a normaliser
            if sc not in normalisers:
                no_normaliser_rows += len(rows)
                continue
            # Normalise each value in each row
            for row in rows:
                for (key,val) in row.values.items():
                    if key not in normalisers[sc]:
                        del row.values[key]
                        continue
                    row.values[key] = row.values[key] / normalisers[sc][key]
                newRows.append(row)                
        
        datatable.rows = newRows
        if ignored_rows > 0:
            logging.info('Normalise block (to best value, grouping by %s) ignored %d rows because they did not have a value for %s.' % (kwargs['group'], ignored_rows, kwargs['column']))
        if no_normaliser_rows > 0:
            logging.info('Normalise block (to best value, grouping by %s) ignored %d rows because no normaliser existed for them.' % (kwargs['group'], no_normaliser_rows))


class GraphBlock:
    """ Generate graphs based on the data in the DataTable. """
    
    def process(self, datatable, **kwargs):
        if kwargs['graph-type'] == 'histogram':
            return self.processHistogram(datatable, **kwargs)
    
    def processHistogram(self, datatable, renderCSV=False, csvIndex=-1, pipeline_hash='', **kwargs):
        """ Pivots the datatable into a histogram-style row vs column table and
            returns the resulting HTML. We return a list of HTML strings, one per
            table, to provide the possibility that a graph generates more than
            one table.
            
            isCSV: whether the resulting table should be rendered as a CSV file
            Keyword arguments:
            * row    -- the scenario column to be used as the row discriminator
            * column -- the scenario column to be used as the column discriminator
            * value  -- the value to be plotted
        """
        if renderCSV:
            method = self.renderCSV
        else:
            method = self.renderTable
        outputs = {}
        scenario_keys = {}
        graph_sets = {}
        for row in datatable:
            if kwargs['column'] in row.scenario and kwargs['row'] in row.scenario and kwargs['value'] in row.values:
                schash = scenario_hash(row.scenario, exclude=[kwargs['column'], kwargs['row']])
                if schash not in scenario_keys:
                    scenario = copy.copy(row.scenario)
                    del scenario[kwargs['column']]
                    del scenario[kwargs['row']]
                    scenario_keys[schash] = scenario
                if schash not in graph_sets:
                    graph_sets[schash] = []
                graph_sets[schash].append(row)
        
        logging.debug(graph_sets)
        logging.debug(scenario_keys)
        
        for sc, rows in graph_sets.items():
            graph_rows = {}
            column_keys = []
            for row in rows:
                if row.scenario[kwargs['row']] not in graph_rows:
                    graph_rows[row.scenario[kwargs['row']]] = {}
                if row.scenario[kwargs['column']] in graph_rows[row.scenario[kwargs['row']]]:
                    raise PipelineAmbiguityException('More than one value exists for the graph cell (%s=%s, %s=%s)' % (kwargs['row'], row.scenario[kwargs['row']], kwargs['column'], row.scenario[kwargs['column']]))
                graph_rows[row.scenario[kwargs['row']]][row.scenario[kwargs['column']]] = row.values[kwargs['value']]
                if row.scenario[kwargs['column']] not in column_keys:
                    column_keys.append(row.scenario[kwargs['column']])
                
            row_keys = graph_rows.keys()
            # Try to sort keys numerically first, if they're not numbers, sort as lowercase strings
            try:
                row_keys.sort(key=float)
            except ValueError:
                row_keys.sort(key=str.lower)
            
            try:
                column_keys.sort(key=float)
            except ValueError:
                column_keys.sort(key=str.lower)
            
            key = ', '.join([k + ' = ' + scenario_keys[sc][k] for k in scenario_keys[sc].keys()])
            outputs[key] = method(graph_rows, row_keys, column_keys, kwargs['row'], kwargs['column'], key, pipeline_hash)
            
        #for row in datatable:
        #    if kwargs['column'] in row.scenario and kwargs['row'] in row.scenario and kwargs['value'] in row.values:
        #        if row.scenario[kwargs['row']] not in graph_rows:
        #            graph_rows[row.scenario[kwargs['row']]] = {}
        #        if row.scenario[kwargs['column']] in graph_rows[row.scenario[kwargs['row']]]:
        #            raise PipelineAmbiguityException('More than one value exists for the graph cell (%s=%s, %s=%s)' % (kwargs['row'], row.scenario[kwargs['row']], kwargs['column'], row.scenario[kwargs['column']]))
        #        graph_rows[row.scenario[kwargs['row']]][row.scenario[kwargs['column']]] = row.values[kwargs['value']]
        #        if row.scenario[kwargs['column']] not in column_keys:
        #            column_keys.append(row.scenario[kwargs['column']])                    
        #
        #row_keys = graph_rows.keys()
        ## Try to sort keys numerically first, if they're not numbers, sort as lowercase strings
        #try:
        #    row_keys.sort(key=float)
        #except ValueError:
        #    row_keys.sort(key=str.lower)
        #
        #try:
        #    column_keys.sort(key=float)
        #except ValueError:
        #    column_keys.sort(key=str.lower)
        #
        #return [method(graph_rows, row_keys, column_keys, kwargs['row'], kwargs['column'])]
        logging.debug(outputs)
        return outputs
    
    def renderTable(self, rows, row_keys, column_keys, row_title, column_title, graph_key, pipeline_hash):
        """ Renders a pivoted table (e.g. generated by processHistogram) 
            into HTML. 
            
            rows:         the set of rows, a dictionary which maps a row value
                          to a dictionary of column values
            row_keys:     the keys which appear in the rows dictionary, used as
                          the first value in each row
            column_keys:  the keys which appear in each dictionary in the row
                          set, used as the headers for each column
            row_title:    the title of the scenario column used as a row
                          discriminator
            column_title: the title of the scenario column used as a column
                          discriminator
        """
        graph_hash = str(abs(hash(pipeline_hash + graph_key)))
        # Here we might check if it already exists in the graph cache...
        csv = self.renderCSV(rows, row_keys, column_keys, row_title, column_title, graph_key, pipeline_hash, force_cis=True)
        csv_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        csv_file.write(csv)
        csv_file.close()
        graph_path = os.path.join(settings.GRAPH_CACHE_DIR, graph_hash + '.png')
        self.plotHistogram(csv_file.name, len(column_keys), graph_path)
        os.remove(csv_file.name)
        output = '<img src="/results/graph/' + graph_hash + '.png" />'
        output += '<table><thead><tr><th>' + row_title + '</th>'
        for key in column_keys:
            output += '<th>' + column_title + '=' + key + '</th>'
        output += '</tr></thead><tbody>'
        for row in row_keys:
            output += '<tr><td>' + row + '</td>'
            for key in column_keys:
                if key in rows[row]:
                    output += '<td>' + present_value(rows[row][key]) + '</td>'
                else:
                    output += '<td>*</td>'
            output += '</tr>'
        output += '</tbody></table>'
        
        return output
        
    def renderCSV(self, rows, row_keys, column_keys, row_title, column_title, graph_key, pipeline_hash, force_cis=False):
        # Look for DataAggregates. We can't just check the first one because it
        # may not exist.
        has_cis = force_cis
        for row in row_keys:
            for key in column_keys:
                if key in rows[row] and isinstance(rows[row][key], DataAggregate):
                    has_cis = True
                    break
            if has_cis:
                break
        
        output = '"' + row_title + '",'
        for key in column_keys:
            output += '"' + key + '",'
            if has_cis:
                output += '"' + key + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.lowerBound",'
                output += '"' + key + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.upperBound",'
        if output[-1] == ',':
            output = output[:-1]
        output += "\r\n"
        for row in row_keys:
            output += '"' + row + '",'
            for key in column_keys:
                if key in rows[row]:
                    output += present_value_csv('graph', rows[row][key], ['graph'] if has_cis else []) + ','
                else:
                    if has_cis:
                        output += '"","","",'
                    else:
                        output += '"",'
            if output[-1] == ',':
                output = output[:-1]
            output += "\r\n"
        
        return output
    
    def plotHistogram(self, csv_filename, num_cols, graph_path):
        """ Plot a histogram csv file with gnuplot.
        
        csv_filename: the csv file where the graph data has been temporarily
                      stored.
        num_cols:     the number of columns of data (not including error bars)
        """
        
        num_cols = 3*num_cols - 1
        
        gnuplot = """
set terminal png truecolor notransparent enhanced font "{font_path}" 10 size 960,360 xFFFFFF
set output '{graph_path}'
set datafile separator ","
set ylabel "Result"
set xtics out
set ytics out
set xtics nomirror
set ytics nomirror

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

plot for [COL=2:{num_cols}:3] "{csv_filename}" u COL:COL+1:COL+2:xtic(1) title col(COL)
"""
        gp_file = tempfile.NamedTemporaryFile(suffix='.gp', delete=False)
        gp_file.write(gnuplot.format(graph_path=graph_path, num_cols=num_cols, csv_filename=csv_filename, font_path=settings.GRAPH_FONT_PATH))
        gp_file.close()
        os.system("gnuplot " + gp_file.name)
        os.remove(gp_file.name)
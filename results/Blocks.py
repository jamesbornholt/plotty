"""
This module defines the blocks available to a pipeline, and their functionality.
Every block is a subclass of the Block class, which defines two basic methods
which it describes.
"""

import math, copy, os, time
import subprocess
from plotty.results.DataTypes import DataRow, DataAggregate, ScenarioValue
from plotty.results.Utilities import present_scenario, present_scenario_csv, present_value, present_value_csv_graph, scenario_hash
from plotty.results.Exceptions import PipelineAmbiguityException, PipelineError, PipelineBlockException
import plotty.results.PipelineEncoder as PipelineEncoder
from plotty.results.models import *
from plotty import settings
import logging
import re


class Block(object):
    """ The base object for blocks. Defines methods all blocks should implement.
    """
    def __init__(self):
        self.flags = 0
    
    def decode(self, param_string, cache_key):
        """ Decodes a paramater string and stores the configuration in local
            fields. 
            cache_key is actually the encoded pipeline up to and including this
            block, but this should not be relied upon. It is intended for use as
            a unique identifier for the context of this block, to be used for
            caching results or calculations for reuse. """
        pass
    
    def apply(self, data_table, messages):
        """ Apply this block to the data_table. data_table is passed by reference,
            so this method does not return.

            Can throw PipelineAmbiguityException or PipelineBlockException. """
        pass
    
    def getFlag(self, flag):
        """ Get a flag's value """
        return bool(self.flags & flag)

class FormatBlock(Block):
    """ Adds configured formatting information to the table for a specified column. """

    def __init__(self):
        super(FormatBlock, self).__init__()
        self.column = None
        self.key = None

    def decode(self, param_string, cache_key):
        """ Decode a format block from an encoded pipeline string.
            Format blocks are encoded in the form:
            column&key
            where column is the scenario column and key specifies the format.
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # Exactly two parts - flagword and settings
        if len(parts) != 2:
            raise PipelineError("Format block invalid: incorrect number of parts")

        self.flags = int(parts[0])

        settings = parts[1].split(PipelineEncoder.PARAM_SEPARATOR)
        # Exactly two settings - type and column
        if len(settings) != 2:
            raise PipelineError("Format block invalid: incorrect number of settings")

        self.column = settings[0]
        self.key = settings[1]

    def apply(self, data_table, messages):
        """ Apply this block to the given data table.
        """
        isValues = self.column == '<VALUES>'
        if not (isValues or self.column in data_table.scenarioColumns):
            raise PipelineError("Invalid column specified for block")

        styles = {}

        try:
            style = FormatStyle.objects.get(key=self.key);
            for dbe in FormatStyleEntry.objects.filter(formatstyle=style).order_by('index').all():
                styles[dbe.value] = ScenarioValue(dbe.index, dbe.value, dbe.display, dbe.group, dbe.color)
        except:
            raise PipelineError("Error loading style")

        missing = set()
        if isValues:
            for valCol in data_table.valueColumns:
                if valCol not in styles:
                    missing.add(valCol)
                else:
                    data_table.valueColumnsDisplay[valCol] = styles[valCol];
        else:
            for row in data_table:
                val = row.scenario[self.column]
                if val not in styles:
                    missing.add(val)
                else:
                    row.scenario[self.column] = styles[val]

        for m in missing:
            messages.warn("Format missing entry for %s value %s" % (self.column, m))

class CompositeScenarioBlock(Block):
    """ Allows the introduction of new, logical scenario columns based on existing columns. """

    def __init__(self):
        """ Define the single instance variable of a CompositeScenarioBlock.
        
        columns:  An array of column names describing the columns to combine 
        """
        super(CompositeScenarioBlock, self).__init__()

        self.columns = []


    def decode(self, param_string, cache_key):
        """ Decode a block from an encoded pipeline string.
            scenario1&scenario2...
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # There must be at least two - a flagword and one filter
        if len(parts) < 2:
            raise PipelineError("Filter block invalid: not enough parts")
        
        self.flags = int(parts[0])

        # Everything past the first part is a filter
        for filt_str in parts[1:]:
            settings = filt_str.split(PipelineEncoder.PARAM_SEPARATOR)
            # Must be exactly three parts - scenario, is, value
            if len(settings) != 1:
                logging.debug("CompositeScenarioBlock invalid: incorrect number of parts in %s" % filt_str)
                continue
            self.columns.append(settings[0])

    def apply(self, data_table, messages):
        """ Apply this block to the given data table.
        """
        for col in self.columns:
            if not col in data_table.scenarioColumns:
                raise PipelineError("Invalid columns specified for block")
            data_table.scenarioColumns.remove(col)

        composite_col = '-'.join(self.columns)
        for row in data_table:
            row.scenario[composite_col] = ScenarioValue('-'.join(ScenarioValue(row.scenario[x]).value for x in self.columns))
            for col in self.columns:
                del row.scenario[col]

        data_table.scenarioColumns.add(composite_col) 

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


    def decode(self, param_string, cache_key):
        """ Decode a filter block from an encoded pipeline string.
            Filter blocks are encoded in the form:
            filter1scenario^filter1is^filter1value&filter2scenario^...
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # There must be at least two - a flagword and one filter
        if len(parts) < 2:
            raise PipelineError("Filter block invalid: not enough parts")
        
        self.flags = int(parts[0])

        # Everything past the first part is a filter
        for filt_str in parts[1:]:
            settings = filt_str.split(PipelineEncoder.PARAM_SEPARATOR)
            # Must be exactly three parts - scenario, is, value
            if len(settings) != 3:
                logging.debug("Filter invalid: not enough parts in %s" % filt_str)
                continue
            self.filters.append({
                'scenario': settings[0],
                'is':       (settings[1] == FilterBlock.TYPE['IS']),
                'value':    settings[2]
            })

    def apply(self, data_table, messages):
        """ Apply this block to the given data table.
        """
        for f in self.filters:
            if not f['scenario'] in data_table.scenarioColumns:
                raise PipelineError("Invalid columns specified for block")

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

class ValueFilterBlock(Block):
    """ Filters the datatable by including or excluding particular rows based
        on value criteria. The rows that do not match every filter are thrown out 
        (that is, the list of filters is ANDed together). """

    TYPE = {
        'IS': '1',
        'IS_NOT': '2'
    }

    def __init__(self):
        """ Define the single instance variable of a ValueFilterBlock.
        
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
        super(ValueFilterBlock, self).__init__()

        self.filters = []


    def decode(self, param_string, cache_key):
        """ Decode a value filter block from an encoded pipeline string.
            ValueFilter blocks are encoded in the form:
            filter1column^filter1is^filter1lowerbound^filter1upperbound&filter2column^...
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # There must be at least two - a flagword and one filter
        if len(parts) < 2:
            raise PipelineError("ValueFilter block invalid: not enough parts")
        
        self.flags = int(parts[0])

        # Everything past the first part is a filter
        for filt_str in parts[1:]:
            settings = filt_str.split(PipelineEncoder.PARAM_SEPARATOR)
            # Must be exactly four parts - value column, is, lower bound, upper bound
            if len(settings) != 4:
                logging.debug("ValueFilter invalid: not enough parts in %s" % filt_str)
                continue
            try:
                lowerbound = float(settings[2])
                upperbound = float(settings[3])
            except ValueError:
                raise PipelineError("Invalid lower (%s) or upper (%s) bound for ValueFilter - bounds must be valid Python floats (including +inf and -inf)" % (settings[2], settings[3]))
            self.filters.append({
                'column':       settings[0],
                'is':           (settings[1] == ValueFilterBlock.TYPE['IS']),
                'lowerbound':   lowerbound,
                'upperbound':   upperbound
            })

    def apply(self, data_table, messages):
        """ Apply this block to the given data table.
        """
        for f in self.filters:
            if not f['column'] in data_table.valueColumns:
                raise PipelineError("Invalid columns specified for block")
        new_rows = []
        for row in data_table:
            add = True
            for filt in self.filters:
              if add:
                in_data = filt['column'] in row.values
                in_bounds = in_data and (row.values[filt['column']] >= filt['lowerbound'] and row.values[filt['column']] <= filt['upperbound'])
                add = in_data and (bool(in_bounds) == bool(filt['is']))
            if add:
                new_rows.append(row)
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

    FLAGS = {
        'ADD_SEPARATE_COLUMN': 1 << 0
    }

    def __init__(self):
        super(AggregateBlock, self).__init__()
        self.column = None
        self.type = None

    def decode(self, param_string, cache_key):
        """ Decode an aggregate block from an encoded pipeline string.
            Aggregate blocks are encoded in the form:
            1&column
            where the number is the TYPE chosen, and column is the scenario
            column.
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # Exactly two parts - flagword and settings
        if len(parts) != 2:
            raise PipelineError("Aggregate block invalid: incorrect number of parts")
        
        self.flags = int(parts[0])

        settings = parts[1].split(PipelineEncoder.PARAM_SEPARATOR)
        # Exactly two settings - type and column
        if len(settings) != 2:
            raise PipelineError("Aggregate block invalid: incorrect number of settings")

        self.type = settings[0]
        self.column = settings[1]

    def apply(self, data_table, messages):
        """ Apply this block to the given data table.
        """
        if not self.column in data_table.scenarioColumns:
            raise PipelineError("Invalid columns specified for block")

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
                if not self.getFlag(AggregateBlock.FLAGS['ADD_SEPARATE_COLUMN']):
                    del scenarios[schash][self.column]
            groups[schash].append(row.values)
        
        # Create the DataAggregate objects for each group
        aggregates = {}
        for sc,rows in groups.items():
            vals = {}
            for row in rows:
                for key,val in row.items():
                    if key not in vals:
                        vals[key] = DataAggregate(AggregateBlock.TYPE[self.type])
                    vals[key].append(val)
            aggregates[sc] = vals

        # Update the rows
        if self.getFlag(AggregateBlock.FLAGS['ADD_SEPARATE_COLUMN']):
            for row in data_table:
                schash = scenario_hash(scenario=row.scenario, exclude=[self.column])
                if schash in aggregates:
                    for key,agg in aggregates[schash].items():
                        row.values[key + "." + self.TYPE[self.type]] = agg
        else:
            new_rows = []
            for sc,rows in groups.items():
                new_row = DataRow()
                new_row.scenario = scenarios[sc]
                new_row.values = aggregates[sc]
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

    FLAGS = {
        'NORMALISE_TO_SPECIFIC_VALUE': 1 << 0,
        'INVERT_RESULT': 1 << 1 
    }

    def __init__(self):
        super(NormaliseBlock, self).__init__()

        self.group = []
        self.type = None
        self.normaliser = []
        self.normaliserValue = None

    def decode(self, param_string, cache_key):
        """ Decode a normalise block from an encoded pipeline string.
            Normalise blocks are encoded in the form:
            0&scenario^value&scenario^value&groupscenario&groupscenario
            We distinguish between selected normalisers and group scenarios
            by the presence of the ^ character.
        """
        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # At least three parts - flagword, type, groups (possibly empty)
        if len(parts) < 3:
            raise PipelineError("Normalise block invalid: incorrect number of parts")
        
        self.flags = int(parts[0])
        self.type = parts[1]

        # Part 3 is the groupings
        groupings = parts[2].split(PipelineEncoder.PARAM_SEPARATOR)
        for grp in groupings:
            s = grp.strip()
            if len(s) > 0:
                self.group.append(s)
        
        # If this is a select normaliser, part 4 is the pairs
        if self.type == NormaliseBlock.TYPE['SELECT']:
            if len(parts) < 4 or len(parts[3].strip()) == 0:
                raise PipelineError("Normalise block invalid: no pairings for select normaliser")
            pairs = parts[3].split(PipelineEncoder.PARAM_SEPARATOR)
            for pair in pairs:
                elements = pair.split(PipelineEncoder.TUPLE_SEPARATOR)
                if len(elements) != 2:
                    logging.debug("Normalise block: Not a valid pairing: ", pair)
                self.normaliser.append({
                    'scenario': elements[0],
                    'value':    elements[1]
                })
        
        # If normalising with a specific column, the next part is that column
        if self.getFlag(NormaliseBlock.FLAGS['NORMALISE_TO_SPECIFIC_VALUE']):
            nextIdx = 4 if self.type == NormaliseBlock.TYPE['SELECT'] else 3
            if len(parts) <= nextIdx or len(parts[nextIdx].strip()) == 0:
                raise PipelineError("Normalise block invalid: no column for normalise value")
            self.normaliserValue = parts[nextIdx].strip()
    
    def apply(self, data_table, messages):
        """ Apply this block to the given data table.
        """
        ignored_rows = []
        no_normaliser_rows = []

        groups = {}

        for col in self.group:
            if not col in data_table.scenarioColumns:
                raise PipelineError("Invalid columns specified for block")
        if self.type == NormaliseBlock.TYPE['SELECT']:
            for n in self.normaliser:
                if not n['scenario'] in data_table.scenarioColumns:
                    raise PipelineError("Invalid columns specified for block")
        if self.getFlag(NormaliseBlock.FLAGS['NORMALISE_TO_SPECIFIC_VALUE']):
            if not self.normaliserValue in data_table.valueColumns:
                raise PipelineError("Invalid columns specified for block")

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
                    if self.getFlag(NormaliseBlock.FLAGS['NORMALISE_TO_SPECIFIC_VALUE']):
                        normaliserValueKey = self.normaliserValue
                    else:
                        normaliserValueKey = key
                    if normaliserValueKey in normalisers[scenario]:
                        if self.getFlag(NormaliseBlock.FLAGS['INVERT_RESULT']):
                            row.values[key] = normalisers[scenario][normaliserValueKey] / row.values[key]
                        else:
                            row.values[key] = row.values[key] / normalisers[scenario][normaliserValueKey]
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

    FLAGS = {
        'DO_NOT_GROUP_BY_UNBOUND_SCENARIO_COLUMNS': 1 << 0
    }

    
    def __init__(self):
        super(GraphBlock, self).__init__()
        self.cache_key_base = None
        self.format_key = None
        self.series_key = None
        self.pivot_key = None
        self.value_keys = []

    def decode(self, param_string, cache_key):
        self.cache_key_base = cache_key

        parts = param_string.split(PipelineEncoder.GROUP_SEPARATOR)
        # Exactly 3 parts: flagword, type, settings for that type
        if len(parts) != 3:
            raise PipelineError("Graph block invalid: incorrect number of parts %s" % len(parts))
        
        self.flags = int(parts[0])

        settings = parts[1].split(PipelineEncoder.PARAM_SEPARATOR)

        if len(settings) != 3:
            raise PipelineError("Graph block invalid: incorrect number of global settings")

        self.format_key = str(settings[0])
        if settings[1] != '':
            self.series_key = settings[1]
        if settings[2] != '':
            self.pivot_key = settings[2]

        if parts[2] != '':
            self.value_keys = parts[2].split(PipelineEncoder.PARAM_SEPARATOR)

    def pivot(self, rows, row_key, column_key, value_key):
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
            if row.scenario[row_key] not in pivot_rows:
                pivot_rows[row.scenario[row_key]] = {}
            # Check if this is a column we haven't seen before
            if row.scenario[column_key] not in column_keys:
                column_keys.add(row.scenario[column_key])
                mins[row.scenario[column_key]] = float('+inf')
                maxs[row.scenario[column_key]] = float('-inf')
                sums[row.scenario[column_key]] = 0
                products[row.scenario[column_key]] = 1
                counts[row.scenario[column_key]] = 0
            
            # If there's already a value in this cell, we have am ambiguity
            if row.scenario[column_key] in pivot_rows[row.scenario[row_key]]:
                raise PipelineAmbiguityException('More than one value exists for the graph cell (%s=%s, %s=%s)' % (row_key, present_scenario(row.scenario[row_key]), column_key, present_scenario(row.scenario[column_key])))

            # Populate this cell
            pivot_rows[row.scenario[row_key]][row.scenario[column_key]] = row.values[value_key]
        
        incomplete_rows = []
        for row_key in pivot_rows.keys():
            row = pivot_rows[row_key]
            full_row = True
            for key in column_keys:
                if full_row and not key in row:
                    incomplete_rows.append(row_key)
                    full_row = False
            if full_row:
                for key in column_keys:
                    val = float(row[key])
                    # Check for new min/max and update the aggregates
                    if val < mins[key]:
                        mins[key] = val
                    if val > maxs[key]:
                        maxs[key] = val 
                    sums[key] += val
                    products[key] *= val
                    counts[key] += 1

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

        return pivot_rows, aggregates, column_keys, incomplete_rows

    def group(self, table, bound_scenario, bound_value):
        """ Split the rows in the datatable into groups based on the
            cross-product of their scenario columns (apart from those already bound) """
        
        sets = {}
        scenario_keys = {}
        
        for row in table:
            if all([v in row.values for v in bound_value]):
                if all([s in row.scenario for s in bound_scenario]) and all([v in row.values for v in bound_value]):
                    schash = scenario_hash(row.scenario, exclude=bound_scenario)
                    if schash not in sets:
                        sets[schash] = []
                        scenario = copy.copy(row.scenario)
                        for s in bound_scenario:
                            if s in scenario:
                                del scenario[s]
                        scenario_keys[schash] = scenario
                    sets[schash].append(row)
        
        return sets, scenario_keys

    def renderPivotCSV(self, table, column_keys, row_keys, aggregates, incomplete_rows):
        output = []
        # Build the header row
        line = '"type","","",'
        for key in column_keys:
            line += '"' + present_scenario_csv(key) + '",'
            line += '"' + present_scenario_csv(key) + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.lowerBound",'
            line += '"' + present_scenario_csv(key) + '.' + str(settings.CONFIDENCE_LEVEL * 100) + '%-CI.upperBound",'
        # Truncate the last comma to be clear
        output.append(line[:-1])
        
        # Build the rows
        for row in row_keys:
            mark_incomplete = 'miss' if row in incomplete_rows else 'full' 
            line = '"data","' + mark_incomplete + '","' + present_scenario_csv(row) + '",'
            for col in column_keys:
                if col in table[row]:
                    val = table[row][col]
                    if isinstance(val, DataAggregate):
                        ciDown, ciUp = val.ci()
                        if math.isnan(ciDown):
                            line += '%f,%f,%f,' % ((val.value(),)*3)
                        else:
                            line += '%f,%f,%f,' % (val.value(), ciDown, ciUp)
                    else:
                        line += '%f,%f,%f,' % ((val,)*3)
                else:
                    line += ',,,'
            
            # Truncate the last comma to be clear
            output.append(line[:-1])

        if aggregates:
            for agg in ['min', 'max', 'mean', 'geomean']:
                line = '"agg","full","' + agg + '",'
                for col in column_keys:
                    if col in aggregates[agg]:
                        # gnuplot expects non-empty data, with error cols containing the absolute val
                        # of the error (e.g. a val of 1.3 with CI of 1.25-1.35 needs to report
                        # 1.3,1.25,1.35 to gnuplot)
                        line += '%f,%f,%f,' % (aggregates[agg][col], aggregates[agg][col], aggregates[agg][col])
                    else:
                        line += '0,0,0,'
                # Truncate the last comma to be clear
                output.append(line[:-1])
        
        return "\n".join(output)

    def renderPivotHTML(self, pivot_table, column_keys, row_keys, graph_hash, aggregates, incomplete_rows):
        #output  = '<object width=100% data="graph/' + graph_hash + '.svg" type="image/svg+xml"></object>'
        #output += '<p>Download: '
        #output += '<a href="graph/' + graph_hash + '.csv">csv</a> '
        #output += '<a href="graph/' + graph_hash + '.gpt">gpt</a> '
        #output += '<a href="graph/' + graph_hash + '.svg">svg</a> '
        #output += '<a href="graph/' + graph_hash + '.pdf">pdf</a> '
        #output += '<a href="graph/' + graph_hash + '.wide.pdf">wide pdf</a>'
        #output += '</p>'
        #output += ('<pre>' + plot_output + '</pre>' if not str.strip(plot_output) == '' else '')
        #output += '<div class="foldable"><h1>Traceback<button class="foldable-toggle-show pipeline-button">Show</button></h1><div class="foldable-content hidden">'
        output = '<table><thead><tr><th></th>'
        for key in column_keys:
            output += '<th>' + present_scenario(key) + '</th>'
        output += '</tr></thead><tbody>'
        for row_name in row_keys:
            output += '<tr><td>' + present_scenario(row_name) + '</td>'
            for key in column_keys:
                if key in pivot_table[row_name]:
                    output += '<td class="value">' + present_value(pivot_table[row_name][key]) + '</td>'
                else:
                    output += '<td class="value">*</td>'
            output += '</tr>'
        output += '<tr><td>&nbsp;</td></tr>'
        if aggregates != None:
            for agg in ['min', 'max', 'mean', 'geomean']:
                output += '<tr><td><i>' + agg + '</i></td>'
                for key in column_keys:
                    if key in aggregates[agg]:
                        output += '<td class="value">%.3f</td>' % aggregates[agg][key]
                    else:
                        output += '<td class="value">*</td>'
                output += '</tr>'
        output += '</tbody></table>'
        #output += '</div></div>'

        return output

    def apply(self, data_table, messages):
        """ Render the graph to HTML, including images """

        def sort_keys(l):
            # alphabetic, numeric, formatted
            is_numeric = True
            for v in l:
              try:
                n = float(v)
              except ValueError:
                is_numeric = False
                break
            if is_numeric:
              return l.sort(key=float)
            l.sort(key=lambda x: None if isinstance(x, ScenarioValue) else str(x))
            l.sort(key=lambda x: None if isinstance(x, ScenarioValue) or isinstance(x, basestring) else float(x))
            l.sort(key=lambda x: x.index if isinstance(x, ScenarioValue) else 'inf')

        # Clean up graph directory.
        one_week_ago = time.time() - settings.CACHE_TIMEOUT
        for graph_entry in os.listdir(settings.GRAPH_CACHE_DIR):
            graph_file = os.path.join(settings.GRAPH_CACHE_DIR, graph_entry)
            if os.path.getmtime(graph_file) < one_week_ago:
                os.unlink(graph_file)

        bound_value = self.value_keys

        if len(bound_value) == 0:
            bound_value = data_table.valueColumns

        # code
        code = None
        try:
            dbformat = GraphFormat.objects.get(key=self.format_key)
            code = str(dbformat)
        except GraphFormat.DoesNotExist:
            raise PipelineError("Requested graph format does not exist")
            

        if self.pivot_key:
            # this is a pivot table
            graphs = []
            for value_key in bound_value: 
                if self.getFlag(GraphBlock.FLAGS['DO_NOT_GROUP_BY_UNBOUND_SCENARIO_COLUMNS']):
                    sets = {'all': data_table.rows}
                    scenario_keys = {'all': []}
                else:
                    sets, scenario_keys = self.group(data_table, [self.series_key, self.pivot_key], [value_key])

                for (scenario, rows) in sets.iteritems():
                    # Pivot the data
                    pivot_table, aggregates, column_keys, incomplete_rows = self.pivot(rows, self.pivot_key, self.series_key, value_key)


                    # Sort the column and keys so they show nicely in the graph
                    row_keys = pivot_table.keys()
                    sort_keys(row_keys)
                    column_keys = list(column_keys)
                    sort_keys(column_keys)
                
                    # Generate a hash for this graph
                    graph_hash = str(abs(hash(self.cache_key_base + value_key + scenario)))
                    graph_path = os.path.join(settings.GRAPH_CACHE_DIR, graph_hash)

                    for e in os.listdir(settings.GRAPH_CACHE_DIR):
                        if e.startswith(graph_hash):
                            graph_file = os.path.join(settings.GRAPH_CACHE_DIR, e)
                            os.unlink(graph_file)
                
                    # If the csv doesn't exist or is out of date (the data_table has
                    # logs newer than it), replot the data
                    logging.debug("Regenerating graph %s" % graph_path)

                    # Render the CSV
                    csv = self.renderPivotCSV(pivot_table, column_keys, row_keys, aggregates, incomplete_rows)
                    csv_file = open(graph_path + '.csv', "w")
                    csv_file.write(csv)
                    csv_file.close()
   
                    (plot_output, suffixes) = self.produceGraph(graph_hash, graph_path, code, column_keys)
                
                    # Render the HTML!
                    table_html = self.renderPivotHTML(pivot_table, column_keys, row_keys, graph_hash, aggregates, incomplete_rows)
                
                    title = data_table.valueColumnsDisplay[value_key]
                    if len(scenario_keys[scenario]) > 0:
                        title += " [" + ', '.join([present_scenario(k) + ' = ' + present_scenario(scenario_keys[scenario][k]) for k in scenario_keys[scenario].keys()]) + "]"
                
                    graphs.append({'title': title, 'hash': graph_hash, 'table': table_html, 'output': plot_output, 'suffixes': suffixes})
            
            return graphs
        else:
            graphs = []
            bound_scenario = [self.series_key] if self.series_key else []
            # this is straight copy, single scenario, multiple values, each row must have all requested values
            if self.getFlag(GraphBlock.FLAGS['DO_NOT_GROUP_BY_UNBOUND_SCENARIO_COLUMNS']):
                sets = {'all': data_table.rows}
                scenario_keys = {'all': []}
            else:
                sets, scenario_keys = self.group(data_table, bound_scenario, bound_value)

            for (scenario, rows) in sets.iteritems():
                # get the subset of rows we want
                
                # Generate a hash for this graph
                graph_hash = str(abs(hash(self.cache_key_base + scenario)))
                graph_path = os.path.join(settings.GRAPH_CACHE_DIR, graph_hash)

                for e in os.listdir(settings.GRAPH_CACHE_DIR):
                    if e.startswith(graph_hash):
                        graph_file = os.path.join(settings.GRAPH_CACHE_DIR, e)
                        os.unlink(graph_file)
                
                grouping = self.series_key != None
                group_values = set() if grouping else set(["all"])
                series_title = self.series_key if grouping else "series"

                logging.debug("Regenerating graph %s" % graph_path)

                def d(v):
                    return present_scenario_csv(data_table.valueColumnsDisplay[v])

                csv = ['"type","","' + series_title + '",' + ",".join(['"%(v)s","%(v)s.%(ci)d%%-CI.lowerBound","%(v)s.%(ci)d%%-CI.upperBound"' % {'v': d(v), 'ci': settings.CONFIDENCE_LEVEL * 100} for v in bound_value])]

                data = {}
                if not grouping:
                    data['all'] = rows
                else:
                    for row in rows:
                        if self.series_key in row.scenario:
                            if row.scenario[self.series_key] in data:
                                data[row.scenario[self.series_key]].append(row)
                            else:
                                data[row.scenario[self.series_key]] = [row]

                data_keys = list(data.keys())
                sort_keys(data_keys)
                
                for key in data_keys:
                    for row in data[key]:
                        values = ",".join([present_value_csv_graph(row.values[v], True) for v in bound_value])
                        if grouping:
                            if self.series_key in row.scenario:
                                csv.append('"data","","' + (present_scenario_csv(row.scenario[self.series_key])) + '",' + values)
                                group_values.add(row.scenario[self.series_key])
                        else:
                            csv.append('"data","","all",' + values)

                csv_text = "\n".join(csv)

                csv_file = open(graph_path + '.csv', 'w')
                csv_file.write(csv_text)
                csv_file.close()

                # Plot the graph
                display_value = [data_table.valueColumnsDisplay[x] for x in bound_value]
                (plot_output, suffixes) = self.produceGraph(graph_hash, graph_path, code, display_value, group_values)
            
                html = ['<table><thead><tr>' + ('<th>' + series_title + '</th>' if grouping else '') + ''.join(['<th>' + d(v) + '</th>' for v in bound_value]) + '</tr></thead><tbody>']


                for key in data_keys:
                    for row in data[key]:
                        values = "".join(['<td class="value">' + present_value(row.values[v]) + '</td>' for v in bound_value])
                        if grouping:
                            if self.series_key in row.scenario:
                                html.append('<tr><td>' + (present_scenario(row.scenario[self.series_key])) + '</td>' + values + '</tr>')
                        else:
                            html.append('<tr>' + values + '</tr>')

                html.append('</tbody></table>')
                table_html = "\n".join(html)
                
                if len(scenario_keys[scenario]) == 0:
                    title = 'all'
                else:
                    title = ', '.join([present_scenario(k) + ' = ' + present_scenario(scenario_keys[scenario][k]) for k in scenario_keys[scenario].keys()])
                
                graphs.append({'title': title, 'hash': graph_hash, 'table': table_html, 'output': plot_output, 'suffixes': suffixes})

            return graphs
    
    def sanitizeCode(self, code):
        evil = re.compile('((\'")\s*(\\||<|>)|\\.\\.|`|eval)')

        for line in code.split('\n'):
            if (evil.search(line)):
                return False

        return True

    def produceGraph(self, graph_hash, graph_path, code, column_keys, series_values=[]):

        if not self.sanitizeCode(code):
            raise PipelineError("Plotting code failed security check")

        line_colors = self.generateStyles(column_keys)
        columns = [present_scenario_csv(c) for c in column_keys]
        series = " ".join([present_scenario_csv(s) for s in series_values])

        gp_file = open(graph_path + ".gpt", "w")
        try:
            formatted_code = code.format(graph_hash=graph_hash, line_colors=line_colors, num_cols=len(columns), col=columns, series=series, font_path=settings.GRAPH_FONT_PATH)
        except IndexError as ie:
            raise PipelineError("Error formatting gnuplot: index out of range (maybe not enough columns)")
        except KeyError as ke:
            raise PipelineError("Error formatting gnuplot: could not find " + str(ke) + " (maybe invalid gnuplot text)")
        gp_file.write(formatted_code)
        gp_file.close()
        process = subprocess.Popen([settings.GNUPLOT_EXECUTABLE, gp_file.name], cwd=settings.GRAPH_CACHE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = process.communicate()

        suffixes = set()
        for s in [e.replace(graph_hash + '.','') for e in os.listdir(settings.GRAPH_CACHE_DIR) if e.startswith(graph_hash)]:
            if s.endswith('eps'):
                pdf = s.replace('eps','pdf')
                suffixes.add(pdf)
                os.system("ps2pdf -dEPSCrop -dPDFSETTINGS=/prepress " + graph_path + "." + s + " " + graph_path + "." + pdf)
            else:
                suffixes.add(s)
            
        suffixes = list(suffixes)
        suffixes.sort()

        return (stdout + stderr, suffixes)
    
    def generateStyles(self, columns):
        styles = []
        index = 1

        def halve(color):
            r, g, b = [int(p, 16) for p in (color[1:3], color[3:5], color[5:7])]
            r, g, b = [c + ((256 - c) / 2) for c in (r,g,b)]
            return '#%02x%02x%02x' % (r,g,b)

        for c in columns:
            if isinstance(c, ScenarioValue) and c.color:
                styles.append("set style line " + str(index) + " linecolor rgb '" + c.color + "'\n")
                styles.append("set style line " + str(index + 100) + " linecolor rgb '" + halve(c.color) + "'\n")
            index += 1
        return "".join(styles)


import plotty.results.PipelineEncoder
from plotty.results.DataTypes import DataTable, DataRow, DataAggregate
from plotty.results.Blocks import *
from plotty.results.Exceptions import *
import plotty.results.PipelineEncoder as PipelineEncoder
import sys, traceback, logging, copy

BLOCK_MAPPINGS = {
    '1': FilterBlock,
    '2': AggregateBlock,
    '3': NormaliseBlock,
    '4': GraphBlock
}

class Pipeline(object):
    """ A Pipeline consists of selected log files, selected scenario columns and
        value columns, and a set of blocks.

        This is distinct from DataTypes.DataTable. We wish to preserve the
        distinction between the Pipeline as a set of actions, and the DataTable
        which results from applying a Pipeline to a set of data. """
    
    logs = []
    scenarioCols = set()
    valueCols = set()
    blocks = []
    dataTable = None

    def decode(self, encoded):
        """ Decodes an entire paramater string. """
        parts = encoded.split(PipelineEncoder.BLOCK_SEPARATOR)
        self.logs = parts[0].split(PipelineEncoder.GROUP_SEPARATOR)
        self.scenarioCols = set(parts[1].split(PipelineEncoder.GROUP_SEPARATOR))
        self.valueCols = set(parts[2].split(PipelineEncoder.GROUP_SEPARATOR))

        for params in parts[3:]:
            block = BLOCK_MAPPINGS[params[0]]()
            block.decode(params[1:])
            self.blocks.append(block)
    
    def apply(self):
        if len(self.logs) == 0:
            print "No logs."
            return
        
        self.dataTable = DataTable(logs=self.logs)
        self.dataTable.selectScenarioColumns(self.scenarioCols)
        self.dataTable.selectValueColumns(self.valueCols)

        for i,block in enumerate(self.blocks):
            block.apply(self.dataTable)


def execute_pipeline(encoded_string, csv_graphs=False):
    decoded = plotty.results.PipelineEncoder.decode_pipeline(encoded_string)
    try:
        dt = DataTable(logs=decoded['logs'])
        dt.selectValueColumns(decoded['value_columns'])
        dt.selectScenarioColumns(decoded['scenario_columns'])
        logging.debug('Initial: %s' % dt.scenarioColumns)
    except:
        raise PipelineLoadException(*sys.exc_info())
    
    graph_outputs = []
    for i, block in enumerate(decoded['blocks']):
        old_dt = copy.deepcopy(dt)
        try:
            if block['type'] == 'aggregate':
                AggregateBlock().process(dt, **block['params'])
            elif block['type'] == 'filter':
                FilterBlock().process(dt, block['filters'])
            elif block['type'] == 'normalise':
                NormaliseBlock().process(dt, **block['params'])
            elif block['type'] == 'graph':
                graph_outputs.append(GraphBlock().process(dt, pipeline_hash=encoded_string, renderCSV=csv_graphs, **block['params']))
            logging.debug('After block %d (%s): %s' % (i, block['type'], dt.scenarioColumns))
        except PipelineAmbiguityException as e:
            e.block = i
            e.datatable = old_dt
            e.graph_outputs = graph_outputs
            raise e
        except:
            raise PipelineBlockException(i, *sys.exc_info())
    
    return dt, graph_outputs
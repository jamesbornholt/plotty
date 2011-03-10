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

    def __init__(self, web_client=False):
        self.logs = []
        self.scenarioCols = set()
        self.valueCols = set()
        self.blocks = []
        self.dataTable = None
        self.webClient = web_client

    def decode(self, encoded):
        """ Decodes an entire paramater string. """
        try:
            parts = encoded.split(PipelineEncoder.BLOCK_SEPARATOR)
            self.logs = parts[0].split(PipelineEncoder.GROUP_SEPARATOR)
            self.scenarioCols = set(parts[1].split(PipelineEncoder.GROUP_SEPARATOR))
            self.valueCols = set(parts[2].split(PipelineEncoder.GROUP_SEPARATOR))
    
            for params in parts[3:]:
                block = BLOCK_MAPPINGS[params[0]]()
                block.decode(params[1:])
                self.blocks.append(block)
        except:
            raise PipelineLoadException(*sys.exc_info())
        
    def apply(self):
        if len(self.logs) == 0:
            raise PipelineError("No log files are selected.", 'selected log files')
        
        try:
            self.dataTable = DataTable(logs=self.logs, wait=not self.webClient)
            self.dataTable.selectScenarioColumns(self.scenarioCols)
            self.dataTable.selectValueColumns(self.valueCols)
        except LogTabulateStarted:
            raise
        except PipelineAmbiguityException as e:
            e.block = 'selected data'
            raise e
        except PipelineError:
            raise
        except:
            raise PipelineLoadException(*sys.exc_info())

        graph_outputs = []

        for i,block in enumerate(self.blocks):
            try:
                ret = block.apply(self.dataTable)
            except PipelineAmbiguityException as e:
                e.block = i
                # Remove this block + the rest of the pipeline, and try again
                # This is safe - if we've gotten to this point, everything
                # before this block has already worked
                del self.blocks[i:]
                graph_outputs = self.apply()
                e.dataTable = self.dataTable
                e.graph_outputs = graph_outputs
                raise e
            except PipelineError:
                raise
            except:
                raise PipelineBlockException(i, *sys.exc_info())
            
            if isinstance(block, GraphBlock):
                graph_outputs.append(ret)
        
        return graph_outputs


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
import results.PipelineEncoder
from results.DataTypes import *
from results.Blocks import *
import sys, traceback

class PipelineLoadException(Exception):
    def __init__(self, excClass, excArgs, excTraceback):
        self.msg = "%s: %s" % (excClass.__name__, excArgs)
        self.traceback = ''.join(traceback.format_exception(excClass, excArgs, excTraceback))

class PipelineBlockException(Exception):
    def __init__(self, block, excClass, excArgs, excTraceback):
        self.msg = "%s: %s" % (excClass.__name__, excArgs)
        self.traceback = ''.join(traceback.format_exception(excClass, excArgs, excTraceback))
        self.block = block


def execute_pipeline(encoded_string):
    decoded = results.PipelineEncoder.decode_pipeline(encoded_string)
    try:
        dt = DataTable(logs=decoded['logs'])
        dt.selectValueColumns(decoded['value_columns'])
        dt.selectScenarioColumns(decoded['scenario_columns'])
    except:
        raise PipelineLoadException(sys.exc_info())
    
    graph_outputs = []
    for i, block in enumerate(decoded['blocks']):
        try:
            if block['type'] == 'aggregate':
                AggregateBlock().process(dt, **block['params'])
            elif block['type'] == 'filter':
                FilterBlock().process(dt, block['filters'])
            elif block['type'] == 'normalise':
                NormaliseBlock().process(dt, **block['params'])
            elif block['type'] == 'graph':
                graph_outputs.extend(GraphBlock().process(dt, **block['params']))
        except:
            raise PipelineBlockException(i, *sys.exc_info())
    
    return dt, graph_outputs
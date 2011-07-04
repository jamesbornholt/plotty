import plotty.results.PipelineEncoder
from plotty.results.DataTypes import DataTable, DataRow, DataAggregate, Messages
from plotty.results.Blocks import *
from plotty.results.Exceptions import *
import plotty.results.PipelineEncoder as PipelineEncoder
import sys, traceback, logging, copy

BLOCK_MAPPINGS = {
    '1': FilterBlock,
    '2': AggregateBlock,
    '3': NormaliseBlock,
    '4': GraphBlock,
    '5': ValueFilterBlock
}

class Pipeline(object):
    """ A Pipeline consists of selected log files, selected scenario columns and
        value columns, and a set of blocks.

        This is distinct from DataTypes.DataTable. We wish to preserve the
        distinction between the Pipeline as a set of actions, and the DataTable
        which results from applying a Pipeline to a set of data. """

    FLAG_NOTHING = 0

    def __init__(self, web_client=False):
        self.flags = 0
        self.logs = []
        self.scenarioCols = set()
        self.valueCols = set()
        self.derivedValueCols = set()
        self.blocks = []
        self.dataTable = None
        self.messages = None
        self.webClient = web_client

    def decode(self, encoded):
        """ Decodes an entire paramater string. """
        try:
            parts = encoded.split(PipelineEncoder.BLOCK_SEPARATOR)
            # Flagword and pipeline-config are required
            if len(parts) < 2:
                raise PipelineError("Decode invalid because not enough parts")
            
            self.flags = int(parts[0])

            pipelineConfig = parts[1].split(PipelineEncoder.GROUP_SEPARATOR)
            # All four parts required - logs, scenarios, values, derivedVals (may be empty)
            if len(pipelineConfig) != 4:
                raise PipelineError("Decode invalid because not enough pipeline-config parts")
            
            self.logs = pipelineConfig[0].split(PipelineEncoder.PARAM_SEPARATOR)
            self.scenarioCols = set(pipelineConfig[1].split(PipelineEncoder.PARAM_SEPARATOR))
            self.valueCols = set(pipelineConfig[2].split(PipelineEncoder.PARAM_SEPARATOR))
            # Filter whitespace-only values
            self.derivedValueCols = set(filter(lambda x: x != '', pipelineConfig[3].split(PipelineEncoder.PARAM_SEPARATOR)))

            # Put the first two parts back into a string, to be used as a 
            # cache key
            # XXX TODO: we don't do anything sensible about sorting/order in
            # the paramater lists, that would make two different encoded strings
            # represent the same pipeline
            encoded_cumulative = PipelineEncoder.BLOCK_SEPARATOR.join(parts[0:2])

            # Index 2 onwards are blocks
            for params in parts[2:]:
                if len(params.strip()) == 0:
                    continue
                encoded_cumulative += PipelineEncoder.BLOCK_SEPARATOR + params
                # Chomp the first character, the block ID
                block = BLOCK_MAPPINGS[params[0]]()
                block.decode(params[1:], encoded_cumulative)
                self.blocks.append(block)
        except:
            raise PipelineLoadException(*sys.exc_info())
        
    def apply(self):
        if len(self.logs) == 0:
            raise PipelineError("No log files are selected.", 'selected log files')
        
        try:
            self.dataTable = DataTable(logs=self.logs, wait=not self.webClient)
            self.messages = self.dataTable.messages
            self.dataTable.selectScenarioColumns(self.scenarioCols)
            self.dataTable.selectValueColumns(self.valueCols, self.derivedValueCols)
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
                ret = block.apply(self.dataTable, self.messages)
            except PipelineAmbiguityException as e:
                e.block = i
                # Remove this block + the rest of the pipeline, and try again
                # This is safe - if we've gotten to this point, everything
                # before this block has already worked
                del self.blocks[i:]
                graph_outputs = self.apply()
                e.dataTable = self.dataTable
                e.messages = self.messages
                e.graph_outputs = graph_outputs
                raise e
            except PipelineError:
                raise
            except:
                raise PipelineBlockException(i, *sys.exc_info())
            
            if isinstance(block, GraphBlock):
                graph_outputs.append(ret)

        return graph_outputs

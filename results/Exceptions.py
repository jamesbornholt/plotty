import traceback

class PipelineAmbiguityException(Exception):
    def __init__(self, msg, block=-1):
        self.block = block
        self.msg = msg

class PipelineLoadException(Exception):
    def __init__(self, excClass, excArgs, excTraceback):
        self.msg = "%s: %s" % (excClass.__name__, excArgs)
        self.traceback = ''.join(traceback.format_exception(excClass, excArgs, excTraceback))

class PipelineBlockException(Exception):
    def __init__(self, block, excClass, excArgs, excTraceback):
        self.msg = "%s: %s" % (excClass.__name__, excArgs)
        self.traceback = ''.join(traceback.format_exception(excClass, excArgs, excTraceback))
        self.block = block

class PipelineError(Exception):
    """ Non-Python errors - that is, semantic errors in the pipeline rather than
        actual runtime errors """
    def __init__(self, msg, block=-1):
        self.block = block
        self.msg = msg
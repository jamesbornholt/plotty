""" Encodes and decodes pipelines into string representations which are
    easily portable. """

import string

BLOCK_SEPARATOR = '|'
GROUP_SEPARATOR = '&'
PARAM_SEPARATOR = '^'
TUPLE_SEPARATOR = ';'

AGGREGATE_TYPES = { 0: 'mean',
                    1: 'geomean', }

FILTER_PARAM_SEPARATOR = '^'

NORMALISE_PARAM_SEPARATOR = '^'

BLOCK_IDS = { 0: 'filter',
              1: 'aggregate',
              2: 'normalise',
              3: 'graph' }

#
# Misc
#

def reverse_dict_lookup(haystack, lookup):
    return dict((value, key) for key,value in haystack.iteritems()).get(lookup)

#
# Decoding routines
#

def decode_pipeline(data):
    chunks = data.split(BLOCK_SEPARATOR)
    selected_logs = chunks[0].split(GROUP_SEPARATOR)
    scenario_columns = chunks[1].split(GROUP_SEPARATOR)
    value_columns = chunks[2].split(GROUP_SEPARATOR)
    return {'logs': selected_logs, 'scenario_columns': scenario_columns, 'value_columns': value_columns, 'blocks': map(decode_pipeline_block, chunks[3:])}
    
def decode_pipeline_block(data):
    return BLOCK_DECODES[int(data[0])](data[1:])

def decode_filter_block(data):
    filter_strings = data.split(GROUP_SEPARATOR)
    filters = []
    for filter_string in filter_strings:
        split = filter_string.split(FILTER_PARAM_SEPARATOR)
        filter_dict = {'column': split[0], 'value': split[2]}
        if split[1] == '0':
            filter_dict['is'] = False
        else:
            filter_dict['is'] = True
        filters.append(filter_dict)
    return {'type': 'filter', 'filters': filters}

def decode_aggregate_block(data):
    params_string = data.split(GROUP_SEPARATOR)
    return {'type': 'aggregate', 'params': {'column': params_string[0], 'type': AGGREGATE_TYPES[int(params_string[1])]}}
     
def decode_normalise_block(data):
    params_string = data.split(GROUP_SEPARATOR)
    if params_string[0] == '0':
        del params_string[0]
        selection = []
        group = []
        for part in params_string:
            if NORMALISE_PARAM_SEPARATOR in part:
                parts = part.split(NORMALISE_PARAM_SEPARATOR)
                selection.append({'column': parts[0], 'value': parts[1]})
            else:
                group.append(part)
        return {'type': 'normalise', 'params': {'normaliser': 'select', 'selection': selection, 'group': group}}
    elif params_string[0] == '1':
        return {'type': 'normalise', 'params': {'normaliser': 'best', 'group': params_string[1:]}}
    
def decode_graph_block(data):
    params_string = data.split(GROUP_SEPARATOR)
    if params_string[0] == '0':
        return {'type': 'graph', 'params': {'graph-type': 'histogram', 'column': params_string[1], 'row': params_string[2], 'value': params_string[3]}}
    if params_string[0] == '1':
        return {'type': 'graph', 'params': {'graph-type': 'xy', 'column': params_string[1], 'row': params_string[2], 'value': params_string[3]}}
    

BLOCK_DECODES = { 0: decode_filter_block,
                  1: decode_aggregate_block,
                  2: decode_normalise_block,
                  3: decode_graph_block, }

#
# Encoding routines
#

def encode_pipeline(data):
    start = [GROUP_SEPARATOR.join(data['logs']), GROUP_SEPARATOR.join(data['scenario_columns']), GROUP_SEPARATOR.join(data['value_columns'])]
    start.extend(map(encode_pipeline_block, data['blocks']))
    return BLOCK_SEPARATOR.join(start)
    
def encode_pipeline_block(data):
    return '%d%s' % (reverse_dict_lookup(BLOCK_IDS, data['type']), BLOCK_ENCODES[data['type']](data))

def encode_filter_block(data):
    filter_strings = []
    for filter_dict in data['filters']:
        if filter_dict['is']:
            is_type = '1'
        else:
            is_type = '0'
        filter_strings.append(FILTER_PARAM_SEPARATOR.join([filter_dict['column'], is_type, filter_dict['value']]))
    return GROUP_SEPARATOR.join(filter_strings)

def encode_aggregate_block(data):
    return GROUP_SEPARATOR.join([data['params']['column'], str(reverse_dict_lookup(AGGREGATE_TYPES, data['params']['type']))])

def encode_normalise_block(data):
    if data['params']['normaliser'] == 'select':
        head = ['0'].extend(map(lambda a: a['column'] + NORMALISE_PARAM_SEPARATOR + a['value'], data['params']['selection']))
    elif data['params']['normaliser'] == 'best':
        head = ['1']
    return GROUP_SEPARATOR.join(head.extend(data['params']['group']))

def encode_graph_block(data):
    if data['params']['graph-type'] == 'histogram':
        return GROUP_SEPARATOR.join(['0', data['params']['column'], data['params']['row'], data['params']['value']])
    if data['params']['graph-type'] == 'xy':
        return GROUP_SEPARATOR.join(['1', data['params']['column'], data['params']['row'], data['params']['value']])

 
BLOCK_ENCODES = { 'filter': encode_filter_block,
                  'aggregate': encode_aggregate_block,
                  'normalise': encode_normalise_block,
                  'graph': encode_graph_block}

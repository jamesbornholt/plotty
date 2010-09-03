var PipelineEncoder = {
    /*
     * Constants
     */
    
    BLOCK_SEPARATOR: '|',
    GROUP_SEPARATOR: '&',
    
    AGGREGATE_TYPES: { 0: 'mean',
                       1: 'geomean' },
    
    FILTER_PARAM_SEPARATOR: '^',
    
    BLOCK_IDS: { 0: 'filter',
                 1: 'aggregate',
                 2: 'normalise',
                 3: 'graph' },
    
    
    /*
     * Init
     */
    hasInited: false,
    
    init: function() {
        this.BLOCK_DECODES = { 0: this.decode_filter_block,
                               1: this.decode_aggregate_block,
                               2: this.decode_normalise_block,
                               3: this.decode_graph_block };
        this.BLOCK_ENCODES = { 'filter': this.encode_filter_block,
                               'aggregate': this.encode_aggregate_block,
                               'normalise': this.encode_normalise_block,
                               'graph': this.encode_graph_block };
        this.hasInited = true;
    },
    
    /*
     * Misc
     */
    reverse_dict_lookup: function(dict, lookup) {
        for ( i in dict )
            if ( dict[i] == lookup )
                return i;
        return null;
    },
    
    /*
     * Decoding routines
     */
    decode_pipeline: function(data) {
        if ( !this.hasInited )
            this.init();
        chunks = data.split(this.BLOCK_SEPARATOR);
        selected_columns = chunks[1].split(this.GROUP_SEPARATOR);
        selected_logs = chunks[0].split(this.GROUP_SEPARATOR).map(function(i) {return parseInt(i)});
        return {'logs': selected_logs, 'columns': selected_columns, 'blocks': chunks.slice(2).map(this.decode_pipeline_block, this)};
    },
    
    decode_pipeline_block: function(data) {
        type = parseInt(data[0]);
        return this.BLOCK_DECODES[type].call(this, data.substr(1));
    },
    
    decode_filter_block: function(data) {
        filter_strings = data.split(this.GROUP_SEPARATOR);
        filters = [];
        for ( i in filter_strings ) {
            split = filter_strings[i].split(this.FILTER_PARAM_SEPARATOR);
            filter_dict = {'column': split[0], 'value': split[2]};
            if ( split[1] == '0' )
                filter_dict['is'] = false;
            else
                filter_dict['is'] = true;
            filters.push(filter_dict);
        }
        return {'type': 'filter', 'filters': filters};
    },
    
    decode_aggregate_block: function(data) {
        params_string = data.split(this.GROUP_SEPARATOR);
        return {'type': 'aggregate', 'params': {'column': params_string[0], 'type': this.AGGREGATE_TYPES[parseInt(params_string[1])]}};
    },
    
    decode_normalise_block: function(data) {
        params_string = data.split(this.GROUP_SEPARATOR);
        return {'type': 'normalise', 'params': {'column': params_string[0], 'value': params_string[1]}}
    },
    
    decode_graph_block: function(data) {
        return {'type': 'graph'};
    },

    
    /*
     * Encoding routines
     */
    encode_pipeline: function(data) {
        if ( !this.hasInited )
            this.init();
        return [data['logs'].join(this.GROUP_SEPARATOR), data['columns'].join(this.GROUP_SEPARATOR)].concat(data['blocks'].map(this.encode_pipeline_block, this)).join(this.BLOCK_SEPARATOR);
    },
    
    encode_pipeline_block: function(data) {
        return this.reverse_dict_lookup(this.BLOCK_IDS, data['type']) + this.BLOCK_ENCODES[data['type']].call(this, data);
    },
    
    encode_filter_block: function(data) {
        filter_strings = [];
        for ( i in data['filters'] ) {
            if ( data['filters'][i]['is'] )
                is_type = '1';
            else
                is_type = '0';
            filter_strings.push([data['filters'][i]['column'], is_type, data['filters'][i]['value']].join(this.FILTER_PARAM_SEPARATOR));
        }
        return filter_strings.join(this.GROUP_SEPARATOR);
    },
    
    encode_aggregate_block: function(data) {
        return [data['params']['column'], this.reverse_dict_lookup(this.AGGREGATE_TYPES, data['params']['type'])].join(this.GROUP_SEPARATOR);
    },
    
    encode_normalise_block: function(data) {
        return [data['params']['column'], data['params']['value']].join(this.GROUP_SEPARATOR);
    },
    
    encode_graph_block: function(data) {
        return '';
    },
}

function addBlock(type) {
	newBlock = $('#pipeline-' + type + '-template').clone();
	newBlock.attr('id', '');
	
	// do some replaces on the contents...
	
	newBlock.insertBefore('#pipeline-add');
}

function updateAddRemoveButtons(table) {
    rows = $('tr', table);
    if ( rows.length > 1 ) {
        /*rows.each(function(i) {
            $('.remove-row', this).attr('disabled', '');
            $('.add-row', this).css('display', 'none');
        });*/
        $('.remove-row', rows).attr('disabled', '');
        $('.add-row', rows).css('display', 'none');
    }
    else {
        $('.remove-row', rows).attr('disabled', 'disabled');
    }
    $('tr:last-child .add-row', table).css('display', 'block');
}

function addBlockTableRow(button) {
    table = $(button).parents('table');
    newRow = $('tr:first-child', table).clone();
    
    $('select', newRow).each(function() {
        this.selectedIndex = 0;
    });
    
    $(table).append(newRow);
    
    updateAddRemoveButtons(table);
}

function removeBlockTableRow(button) {
    table = $(button).parents('table');
    $(button).parents('tr').remove();
    updateAddRemoveButtons(table);
}

function updateAvailableColumns(data) {
    $('.select-filter-column').each(function() {
        oldValue = $(this).val();
        this.options.length = 0;
        this.options.add(new Option("[" + data.columns.length + " options]", '', oldValue == ''));
        for ( i in data.columns ) {
            this.options.add(new Option(data.columns[i], data.columns[i], oldValue == data.columns[i]));
        }
    });
    $('.select-aggregate-column').each(function() {
        oldValue = $(this).val();
        this.options.length = 0;
        this.options.add(new Option("[" + data.columns.length + " options]", '', oldValue == ''));
        for ( i in data.columns ) {
            this.options.add(new Option(data.columns[i], data.columns[i], oldValue == data.columns[i]));
        }
    });
    
    values_select = $('#select-values');
    oldValues = values_select.val() || [];
    console.log(oldValues);
    values_select = values_select.get(0);
    values_select.options.length = 0;
    for ( i in data.keys ) {
        values_select.options.add(new Option(data.keys[i], data.keys[i]));
    }
    for ( i = 0; i < values_select.options.length; i++ ) {
        if ( oldValues.indexOf(values_select.options[i].value) > -1 ) {
            values_select.options[i].selected = true;
        }
    }
}

function updateAvailableValues(vals) {
    this.options.length = 0;
    this.options.add(new Option("[" + vals.length + " options]", '', true));
    for ( i in vals ) {
        this.options.add(new Option(vals[i], vals[i]));
    }
}

function selectedLogFiles() {
    logs = [];
    log_selects = $('.select-log').get();
    for ( i in log_selects ) {
        logs.push($(log_selects[i]).val());
    }
    return logs;
}

function serialisePipeline() {
    dict = {}
    dict['logs'] = selectedLogFiles();
    dict['columns'] = $('#select-values').val();
    
    blocks = []
    throwInvalid = false;
    if ( $('#pipeline .pipeline-block').length == 0 )
        return false;
    $('#pipeline .pipeline-block').each(function() {
        if ( $(this).hasClass('filter') ) {
            filters = []
            $('tr', this).each(function() {
                if ( $('.select-filter-is', this).val() == 'is' )
                    is = true;
                else
                    is = false;
                column = $('.select-filter-column', this).val();
                value = $('.select-filter-value', this).val();
                if ( column == '' || value == '' ) {
                    throwInvalid = true;
                    return false;
                }
                filters.push({'column': column, 'is': is, 'value': value});
            });
            blocks.push({'type': 'filter', 'filters': filters});
        }
        else if ( $(this).hasClass('aggregate') ) {
            column = $('.select-aggregate-column', this).val();
            type = $('.select-aggregate-type', this).val();
            if ( column == '' || type == '' ) {
                throwInvalid = true;
                return false;
            }
            blocks.push({'type': 'aggregate', 'params': {'column': column, 'type': type}});
        }
        else if ( $(this).hasClass('normalise') ) {
            column = $('.select-normalise-column', this).val();
            value = $('.select-normalise-value', this).val();
            if ( column == '' || value == '' ) {
                throwInvalid = true;
                return false;
            }
            blocks.push({'type': 'normalise', 'params': {'column': column, 'value': type}});
        }
        else if ( $(this).hasClass('graph') ) {
            blocks.push({'type': 'graph'});
        }
        if ( throwInvalid )
            return false;
    });
    if ( throwInvalid )
        return false;
    dict['blocks'] = blocks;
    return dict;
}

function refreshPipeline() {
    pipeline = serialisePipeline();
    if ( pipeline ) {
        encoded = PipelineEncoder.encode_pipeline(pipeline);
        console.log(encoded);
        $.get('/results/ajax/pipeline/' + encoded, function(data) {
            $('#output').html(data);
        });
    }
}

$(document).ready(function() {
    $(document).ajaxStart(function() {
        $('#loading-indicator').css({visibility: 'visible'});
    });
    $(document).ajaxStop(function() {
        $('#loading-indicator').css({display: 'hidden'});
    });
	$("#add-filter").click(function() {
		addBlock('filter');
	});
	$("#add-aggregate").click(function() {
		addBlock('aggregate');
	});
	$("#add-normalize").click(function() {
		addBlock('normalize');
	});
	$("#add-graph").click(function() {
		addBlock('graph');
	});
	$(".remove-button").live('click', function() {
		$(this).parent().remove();
		refreshPipeline();
	});
	$(".add-row").live('click', function() {
	    addBlockTableRow(this);
	});
	$(".remove-row").live('click', function() {
	    removeBlockTableRow(this);
	    refreshPipeline();
	});
	$(".select-log").live('change', function() {
	    $.getJSON('/results/ajax/log-values/' + selectedLogFiles().join(',') + '/', updateAvailableColumns);
	});
	$(".select-filter-column").live('change', function() {
	    values_select = $('.select-filter-value', $(this).parents('tr')).get(0);
	    $.ajax({
	        context: values_select,
	        dataType: 'json',
	        url: '/results/ajax/filter-values/' + selectedLogFiles().join(',') + '/' + $(this).val() + '/',
	        success: updateAvailableValues
	    });
	});
	
	$("#pipeline-log, #pipeline-values, .pipeline-block").find('select').live('change', refreshPipeline);
});
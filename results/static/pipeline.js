if ( typeof console === 'undefined' ) {
    var console = {
        log: function() {}
    }
}
if ( typeof Array.prototype.map === 'undefined' ) {
    Array.prototype.map = function(func, context) {
        var newList = [];
        for ( var i = 0; i < this.length; i++ ) {
            newList.push(func.call(context, this[i]));
        }
        return newList;
    }
}

if ( typeof Array.prototype.remove === 'undefined' ) {
    Array.prototype.remove = function(element) {
        var ret = [null];
        for ( var i = 0; i < this.length; i++ ) {
            if ( this[i] == element ) {
                ret = this.splice(i, 1);
                break;
            }
        }
        return ret[0];
    }
}

$.tablesorter.addParser({
    id: 'confidence-interval',
    is: function(s) {
        return s.indexOf('class="ci"') > -1;
    },
    format: function(s) {
        // parseFloat('12.34 <span ...') = 12.34
        return parseFloat(s);
    },
    type: 'numeric'
});

// Adds a distinct number to every normalise block to make sure the radio
// buttons toggle around correctly
var normaliseBlockCount = 0;

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
        for ( var j in dict )
            if ( dict[j] == lookup )
                return j;
        return null;
    },
    
    /*
     * Decoding routines
     */
    decode_pipeline: function(data) {
        if ( !this.hasInited )
            this.init();
        var chunks = data.split(this.BLOCK_SEPARATOR);
        var scenario_columns = chunks[1].split(this.GROUP_SEPARATOR);
        var value_columns = chunks[2].split(this.GROUP_SEPARATOR);
        var selected_logs = chunks[0].split(this.GROUP_SEPARATOR);
        return {'logs': selected_logs, 'scenario_columns': scenario_columns, 'value_columns': value_columns, 'blocks': chunks.slice(3).map(this.decode_pipeline_block, this)};
    },
    
    decode_pipeline_block: function(data) {
        var type = parseInt(data[0]);
        return this.BLOCK_DECODES[type].call(this, data.substr(1));
    },
    
    decode_filter_block: function(data) {
        var filter_strings = data.split(this.GROUP_SEPARATOR);
        var filters = [];
        for ( var i = 0; i < filter_strings.length; i++ ) {
            var split = filter_strings[i].split(this.FILTER_PARAM_SEPARATOR);
            var filter_dict = {'column': split[0], 'value': split[2]};
            if ( split[1] == '0' )
                filter_dict['is'] = false;
            else
                filter_dict['is'] = true;
            filters.push(filter_dict);
        }
        return {'type': 'filter', 'filters': filters};
    },
    
    decode_aggregate_block: function(data) {
        var params_string = data.split(this.GROUP_SEPARATOR);
        return {'type': 'aggregate', 'params': {'column': params_string[0], 'type': this.AGGREGATE_TYPES[parseInt(params_string[1])]}};
    },
    
    decode_normalise_block: function(data) {
        var params_string = data.split(this.GROUP_SEPARATOR);
        if ( params_string[0] == '0' )
            return {'type': 'normalise', 'params': {'normaliser': 'select', 'column': params_string[1], 'value': params_string[2]}};
        else if ( params_string[0] == '1' )
            return {'type': 'normalise', 'params': {'normaliser': 'best', 'group': params_string.slice(1)}};
    },
    
    decode_graph_block: function(data) {
        var params_string = data.split(this.GROUP_SEPARATOR);
        if ( params_string[0] == '0' )
            return {'type': 'graph', 'params': {'graph-type': 'histogram', 'column': params_string[1], 'row': params_string[2], 'value': params_string[3]}};
        else
            return {};
    },

    
    /*
     * Encoding routines
     */
    encode_pipeline: function(data) {
        if ( !this.hasInited )
            this.init();
        return [data['logs'].join(this.GROUP_SEPARATOR), data['scenario_columns'].join(this.GROUP_SEPARATOR), data['value_columns'].join(this.GROUP_SEPARATOR)].concat(data['blocks'].map(this.encode_pipeline_block, this)).join(this.BLOCK_SEPARATOR);
    },
    
    encode_pipeline_block: function(data) {
        return this.reverse_dict_lookup(this.BLOCK_IDS, data['type']) + this.BLOCK_ENCODES[data['type']].call(this, data);
    },
    
    encode_filter_block: function(data) {
        var filter_strings = [];
        for ( var i = 0; i < data['filters'].length; i++ ) {
            var is_type;
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
        if ( data['params']['normaliser'] == 'select' )
            return ['0', data['params']['column'], data['params']['value']].join(this.GROUP_SEPARATOR);
        else
            return ['1', data['params']['group'].join(this.GROUP_SEPARATOR)].join(this.GROUP_SEPARATOR);
    },
    
    encode_graph_block: function(data) {
        if ( data['params']['graph-type'] == 'histogram' )
            return ['0', data['params']['column'], data['params']['row'], data['params']['value']].join(this.GROUP_SEPARATOR);
        else
            return '';
    }
}

function hashChange(hash) {
    if ( $('#pipeline-hash').val() == hash ) return;
    console.log("hashChange: " + hash);
    $('#output table').remove();
    $('#pipeline .pipeline-block').remove();
    $('.select-log').parents('tr').slice(1).remove();
    $('.select-log').get(0).selectedIndex = 0;
    $('.remove-row').attr('disabled', 'disabled');
    updateAvailableData({scenarioCols: [], valueCols: []});
    if ( hash != "" ) {
        var decoded = PipelineEncoder.decode_pipeline(hash);
        console.log('Reconstructing pipeline: ', decoded);
        
        // Load the available scenario and value columns and populate the dropdowns
        $.ajax({
            url: '/results/ajax/log-values/' + decoded['logs'].join(',') + '/',
            dataType: 'json',
            success: function(data) {
                updateAvailableData(data, decoded['scenario_columns'], decoded['value_columns']);
            },
            async: false
        });
        
        // Populate the log selections
        var newLogRow = $('#pipeline-log tr:first-child');
        var logDropdownOptions = jQuery.map($('select', newLogRow).get(0).options, function(a) { return a.value; });
        $('select', newLogRow).get(0).selectedIndex = jQuery.inArray(decoded['logs'][0], logDropdownOptions);
        for ( var i = 1; i < decoded['logs'].length; i++ ) {
            var newRow = newLogRow.clone();
            $('select', newRow).get(0).selectedIndex = jQuery.inArray(decoded['logs'][i], logDropdownOptions);
            $('#pipeline-log table').append(newRow);
        }
        updateAddRemoveButtons($('#pipeline-log table'));
        
        // Create all the blocks and set their selections
        jQuery.each(decoded['blocks'], function() {
            var newBlock = addBlock(this['type']);
            if ( this['type'] == 'filter' ) {
                var newFilterRow = $('tr:first-child', newBlock);
                var filterDropdownOptions = jQuery.map($('.select-filter-column', newFilterRow).get(0).options, function(a) { return a.value; });
                var setRowValues = function(row, filter) {
                    var selectValueDropdown = $('.select-filter-value', row).get(0);
                    $('.select-filter-column', row).get(0).selectedIndex = jQuery.inArray(filter['column'], filterDropdownOptions);
                    $('.select-filter-is', row).get(0).selectedIndex = filter['is'] ? 0 : 1;
                    $.getJSON('/results/ajax/filter-values/' + decoded['logs'].join(',') + '/' + filter['column'] + '/', function(data) {
                        updateAvailableValues.call(selectValueDropdown, data, filter['value']);
                        refreshPipeline();
                    });
                }
                setRowValues(newFilterRow, this['filters'].shift());
                jQuery.each(this['filters'], function() {
                    var newRow = newFilterRow.clone();
                    setRowValues(newRow, this);
                    $('table', newBlock).append(newRow);
                });
                updateAddRemoveButtons($('table', newBlock));
            }
            else if ( this['type'] == 'aggregate' ) {
                var aggTypeOptions = jQuery.map($('.select-aggregate-type', newBlock).get(0).options, function(a) { return a.value; });
                var aggColumnOptions = jQuery.map($('.select-aggregate-column', newBlock).get(0).options, function(a) { return a.value; });
                $('.select-aggregate-type', newBlock).get(0).selectedIndex = jQuery.inArray(this['params']['type'], aggTypeOptions);
                $('.select-aggregate-column', newBlock).get(0).selectedIndex = jQuery.inArray(this['params']['column'], aggColumnOptions);
            }
            else if ( this['type'] == 'normalise' ) {
                if ( this['params']['normaliser'] == 'select' ) {
                    var params = this['params'];
                    var normColumnOptions = jQuery.map($('.select-normalise-column', newBlock).get(0).options, function(a) { return a.value; });
                    $('.select-normalise-column', newBlock).get(0).selectedIndex = jQuery.inArray(params['column'], normColumnOptions);
                    var selectValueDropdown = $('.select-normalise-value', newBlock).get(0);
                    $.getJSON('/results/ajax/filter-values/' + decoded['logs'].join(',') + '/' + params['column'] + '/', function(data) {
                        updateAvailableValues.call(selectValueDropdown, data, params['value']);
                        refreshPipeline();
                    });
                }
                else {
                    $('input:radio[value="best"]', newBlock).get(0).checked = true;
                    $('.normalise-group', newBlock).css('display', 'block');
                    $('.select-normalise-group', newBlock).val(this['params']['group']);
                    $('.select-normalise-column, .select-normalise-value', newBlock).attr('disabled', 'disabled');
                    $('.select-normalise-group', newBlock).toChecklist();
                    $(newBlock).delegate(".select-normalise-group input", 'change', function() {
    	                refreshPipeline();
    	            });
                }
            }
            else if ( this['type'] == 'graph' ) {
                if ( this['params']['graph-type'] == 'histogram' ) {
                    var selectScenarioOptions = jQuery.map($('.select-graph-column', newBlock).get(0).options, function(a) { return a.value; });
                    var selectValueOptions = jQuery.map($('.select-graph-value', newBlock).get(0).options, function(a) { return a.value; });
                    $('.select-graph-column', newBlock).get(0).selectedIndex = jQuery.inArray(this['params']['column'], selectScenarioOptions);
                    $('.select-graph-row', newBlock).get(0).selectedIndex = jQuery.inArray(this['params']['row'], selectScenarioOptions);
                    $('.select-graph-value', newBlock).get(0).selectedIndex = jQuery.inArray(this['params']['value'], selectValueOptions);
                }
            }
        });
        refreshPipeline();
    }
}

function addBlock(type) {
	var newBlock = $('#pipeline-' + type + '-template').clone();
	newBlock.attr('id', '');
	
	if ( type == 'normalise' ) {
	    $('input:radio', newBlock).attr('name', 'normalise-type-' + normaliseBlockCount).first().attr('checked', 'checked');
	    $('.select-normalise-group').attr('name', 'normalise-group-' + normaliseBlockCount);
	    normaliseBlockCount++;
    }
	    
	newBlock.insertBefore('#pipeline-add');
	
	updateScenarioColumns();
	updateValueColumns();
	
	return newBlock;
}

function updateAddRemoveButtons(table) {
    var rows = $('tr', table);
    if ( rows.length > 1 ) {
        $('.remove-row', rows).attr('disabled', '');
        $('.add-row', rows).css('display', 'none');
    }
    else {
        $('.remove-row', rows).attr('disabled', 'disabled');
    }
    $('tr:last-child .add-row', table).css('display', 'block');
}

function addBlockTableRow(button) {
    var table = $(button).parents('table');
    var newRow = $('tr:first-child', table).clone();
    
    $('select', newRow).each(function() {
        this.selectedIndex = 0;
    });
    
    $(table).append(newRow);
    
    updateAddRemoveButtons(table);
    
    return newRow;
}

function removeBlockTableRow(button) {
    var table = $(button).parents('table');
    $(button).parents('tr').remove();
    updateAddRemoveButtons(table);
}

function updateAvailableData(data, selectedScenarioCols, selectedValueCols) {
    updateMultiSelect('#select-scenario-cols, .select-normalise-group', data.scenarioCols, selectedScenarioCols || true);
    updateMultiSelect('#select-value-cols', data.valueCols, selectedValueCols || false);

    updateScenarioColumns();
}

function updateScenarioColumns() {
    var selected = $("#select-scenario-cols").val() || [];
    
    $('#pipeline .pipeline-block').each(function() {
        $('.scenario-column', this).each(function() {
            var oldValue = $(this).val();
            this.options.length = 0;
            this.options.add(new Option("[" + selected.length + " options]", '-1'));
            for ( var i = 0; i < selected.length; i++ ) {
                this.options.add(new Option(selected[i], selected[i]));
                if ( selected[i] == oldValue )
                    this.options.selectedIndex = i+1;
            }
        });
        
        if ( $(this).hasClass('filter') ) {
            var filters = []
            $('tr', this).each(function() {
                if ( $('.select-filter-is', this).val() == 'is' ) {
                    var value = $('.select-filter-column', this).val();
                    if ( value != '-1' ) {
                        selected.remove(value);
                    }
                }
            });
        }
        else if ( $(this).hasClass('aggregate') ) {
            var value = $('.select-aggregate-column', this).val();
            if ( value != '-1' ) {
                selected.remove(value);
            }
        }
    });
}

function updateValueColumns() {
    var selected = $("#select-value-cols").val() || [];
    
    $('.value-column').each(function() {
        var oldValue = $(this).val();
        this.options.length = 0;
        this.options.add(new Option("[" + selected.length + " options]", '-1'));
        for ( var i = 0; i < selected.length; i++ ) {
            this.options.add(new Option(selected[i], selected[i]));
            if ( selected[i] == oldValue )
                this.options.selectedIndex = i+1;
        }
    });
}

/* It's much easier to throw out the old multi-select and build a new one
 * when we need to update the available values, when we're using the checkbox
 * plugin. */
function updateMultiSelect(selector, vals, selection) {
    // Get the old selections
    var considerSelectAll = (selection === true);
    var useSpecifiedSelection = (typeof selection === 'object');
    $(selector).each(function() {
        var selected = useSpecifiedSelection ? selection : ( $(this).val() || [] );
        var selectAll = false;
        if ( considerSelectAll && (selected.length == $(this).children('input').length || selected.length == 0) )
            selectAll = true;
        
        // Build a new select
        var dropdown = document.createElement('select');
        dropdown.multiple = "multiple";
        for ( var i = 0; i < vals.length; i++ )
            dropdown.options.add(new Option(vals[i], vals[i]));
        if ( selectAll || selected.length > 0 )
            for ( var i = 0; i < vals.length; i++ )
                if ( selectAll || jQuery.inArray(dropdown.options[i].value, selected) > -1 )
                    dropdown.options[i].selected = true;
                    
        dropdown.id = $(this).attr('id');
        dropdown.name = $(this).attr('name');
        dropdown.className = $(this).attr('class');
        //dropdown.style.width = "100%";
        
        // Replace the old select
        $(this).replaceWith(dropdown);
    });

    // Transform only the visible ones (we can't transform the invisible ones
    // until they show up otherwise the dimensions are broken)
    $(selector).filter(':visible').toChecklist();
}

function updateAvailableValues(vals, selected) {
    this.options.length = 0;
    this.options.add(new Option("[" + vals.length + " options]", '', true));
    for ( var i = 0; i < vals.length; i++ ) {
        this.options.add(new Option(vals[i], vals[i]));
        if ( vals[i] == selected )
            this.options.selectedIndex = i+1;
    }
}

function selectedLogFiles() {
    var logs = [];
    var log_selects = $('.select-log').get();
    for ( var i = 0; i < log_selects.length; i++ ) {
        logs.push($(log_selects[i]).val());
    }
    return logs;
}

function serialisePipeline() {
    var dict = {}
    dict['logs'] = selectedLogFiles();
    dict['scenario_columns'] = $('#select-scenario-cols').val();
    dict['value_columns'] = $('#select-value-cols').val();
    
    if ( dict['scenario_columns'].length == 0 || dict['value_columns'].length == 0 )
        return false;
    
    var blocks = [];
    var throwInvalid = false;
    //if ( $('#pipeline .pipeline-block').length == 0 )
    //    return false;
    $('#pipeline .pipeline-block').each(function() {
        if ( $(this).hasClass('filter') ) {
            var filters = []
            $('tr', this).each(function() {
                var is;
                if ( $('.select-filter-is', this).val() == 'is' )
                    is = true;
                else
                    is = false;
                var column = $('.select-filter-column', this).val();
                var value = $('.select-filter-value', this).val();
                if ( column == '-1' || value == '' ) {
                    throwInvalid = true;
                    return false;
                }
                filters.push({'column': column, 'is': is, 'value': value});
            });
            blocks.push({'type': 'filter', 'filters': filters});
        }
        else if ( $(this).hasClass('aggregate') ) {
            var column = $('.select-aggregate-column', this).val();
            var type = $('.select-aggregate-type', this).val();
            if ( column == '-1' || type == '' ) {
                throwInvalid = true;
                return false;
            }
            blocks.push({'type': 'aggregate', 'params': {'column': column, 'type': type}});
        }
        else if ( $(this).hasClass('normalise') ) {
            var selected_type = $('input:radio:checked', this);
            if ( selected_type.val() == 'select' ) {
                var column = $('.select-normalise-column', this).val();
                var value = $('.select-normalise-value', this).val();
                if ( column == '-1' || value == '' ) {
                    throwInvalid = true;
                    return false;
                }
                blocks.push({'type': 'normalise', 'params': {'normaliser': 'select', 'column': column, 'value': value}});
            }
            else if ( selected_type.val() == 'best' ) {
                var group = $('.select-normalise-group', this).val();
                blocks.push({'type': 'normalise', 'params': {'normaliser': 'best', 'group': group}});
            }
            else {
                throwInvalid = true;
                return false;
            }
        }
        else if ( $(this).hasClass('graph') ) {
            var type = $('.select-graph-type', this).val();
            if ( type == 'histogram' ) {
                var column = $('.select-graph-column', this).val();
                var row = $('.select-graph-row', this).val();
                var value = $('.select-graph-value', this).val();
                if ( column == '-1' || row == '-1' || value == '-1' ) {
                    throwInvalid = true;
                    return false;
                }
                blocks.push({'type': 'graph', 'params': {'graph-type': 'histogram', 'column': column, 'row': row, 'value': value}});
            }
            else {
                throwInvalid = true;
                return false;
            }
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
    if ( $('#pause-loading').get(0).checked === true )
        return;
    
    var pipeline = serialisePipeline();
    if ( pipeline ) {
        var encoded = PipelineEncoder.encode_pipeline(pipeline);
        console.log('Loading pipeline: ' + encoded);
        $('#pipeline-hash').val(encoded);
        $('#pipeline-save-name, #pipeline-save-go').attr('disabled', '');
        $.history.load(encoded);
        $('#pipeline-debug-link').attr('href', 'list/' + encoded + '?debug');
        $.getJSON('/results/ajax/pipeline/' + encoded, function(data) {
            $('#output').children().not('#loading-indicator').remove();
            // Stop the sparklines from being rendered unless we actually want them
            $('#output').hide();
            $('#output').append(data.html);
            if ( $('#show-sparklines').get(0).checked === false )
                $('.sparkline').hide();
            if ( data.rows > 100 ) {
                $('#output table, #output .foldable.table').hide();
                $('#large-table-confirm span').html(data.rows);
                $('#large-table-confirm').show();
            }
            else {
                $('#large-table-confirm').hide();
            }
            $('#output').show();
            if ( data.rows < 100 )
                startTableSort();
            $('.error-block').removeClass('error-block');
            $('.ambiguous-block').removeClass('error-block');
            if ( data.error === true )
                // Highlight the erroneous block
                if ( typeof data.index !== 'undefined' )
                    $('#pipeline .pipeline-block').eq(data.index).addClass('error-block');
            if ( data.ambiguity === true )
                // Highlight the ambiguous block
                if ( typeof data.index !== 'undefined' )
                    $('#pipeline .pipeline-block').eq(data.index).addClass('ambiguous-block');
        });
    }
    else {
        $('#pipeline-save-name, #pipeline-save-go').attr('disabled', 'disabled');
    }
}

function startTableSort() {
    $('#output table.results').each(function() {
        var numScenarioHeaders = $(this).find('th.scenario-header').length;
        var sortList = [];
        for ( var i = 0; i < numScenarioHeaders; i++ )
            sortList.push([i, 0]);
        $(this).tablesorter({sortList: sortList});
    });
}

$(document).ready(function() {
    $.ajaxSetup({
        cache: false
    });
    $(document).ajaxStart(function() {
        $('#loading-indicator').show();
    });
    $(document).ajaxStop(function() {
        $('#loading-indicator').hide();
    });
	$("#add-filter").click(function() {
		addBlock('filter');
	});
	$("#add-aggregate").click(function() {
		addBlock('aggregate');
	});
	$("#add-normalise").click(function() {
		addBlock('normalise');
	});
	$("#add-graph").click(function() {
		addBlock('graph');
	});
	$(".remove-button").live('click', function() {
		$(this).parent().remove();
		updateScenarioColumns();
		refreshPipeline();
	});
	$(".add-row").live('click', function() {
	    addBlockTableRow(this);
	});
	$(".remove-row").live('click', function() {
	    if ( this.disabled === true ) return; // This is the silliest IE bug ever
	    removeBlockTableRow(this);
	    refreshPipeline();
	});
	$("#pipeline-log").delegate(".select-log", 'change', function() {
	    $.getJSON('/results/ajax/log-values/' + selectedLogFiles().join(',') + '/', function(data) {
	        updateAvailableData(data);
	    });
	});
	$("#pipeline").delegate(".select-filter-column", 'change', function() {
	    var values_select = $('.select-filter-value', $(this).parents('tr')).get(0);
	    $.ajax({
	        context: values_select,
	        dataType: 'json',
	        url: '/results/ajax/filter-values/' + selectedLogFiles().join(',') + '/' + $(this).val() + '/',
	        success: updateAvailableValues
	    });
	});
	$("#pipeline").delegate(".select-normalise-column", 'change', function() {
	    var values_select = $('.select-normalise-value', $(this).parent()).get(0);
	    $.ajax({
	        context: values_select,
	        dataType: 'json',
	        url: '/results/ajax/filter-values/' + selectedLogFiles().join(',') + '/' + $(this).val() + '/',
	        success: updateAvailableValues
	    });
	});
	$("#pipeline-values").delegate("#select-scenario-cols input", 'change', function() {
	    updateScenarioColumns();
	    refreshPipeline();
	});
	$("#pipeline-values").delegate("#select-value-cols input", 'change', function() {
	    updateValueColumns();
	    refreshPipeline();
	});
	$("#pipeline").delegate("input:radio", 'change', function() {
	    var group_select = $('.normalise-group', $(this).parents(".pipeline"));
	    if ( this.checked == true && this.value == 'select' ) {
	        group_select.css('display', 'none');
	        $('select', $(this).parents(".pipeline")).attr('disabled', '');
        }
	    else if ( this.checked == true && this.value == 'best' ) {
	        group_select.css('display', 'block');
	        if ( $('select', group_select).length > 0 ) {
	            $('select', group_select).toChecklist();
	            $(this).parents(".pipeline").delegate(".select-normalise-group input", 'change', function() {
	                refreshPipeline();
	            });
            }
	        $('select', $(this).parents(".pipeline")).attr('disabled', 'disabled');
	        refreshPipeline();
        }
	});
	$("#output").delegate('.foldable h1 a', 'click', function() {
        var foldable_content = $(this).parents('.foldable').children('.foldable-content');
        if ( foldable_content.hasClass('hidden') ) {
            foldable_content.removeClass('hidden');
            $(this).html('[hide]');
        }
        else {
            foldable_content.addClass('hidden');
            $(this).html('[show]');
        }
        return false;
    });
	$("#pipeline-load-go").click(function() {
	    var selected = $('#pipeline-load-select').val();
        if ( selected != '-1' )
            $.history.load(selected);
	});
	$("#pipeline-save-form").submit(function() {
	    var name = $('#pipeline-save-name').val();
	    var encoded = $('#pipeline-hash').val();
	    if ( name == '' )
	        return false;
	    $.post('/results/ajax/save-pipeline/', {
	        'name': name,
	        'encoded': encoded
	    }, function(data) {
	        console.log('saved: ' + name + ' = ' + encoded);
	        var load_dropdown = $('#pipeline-load-select');
	        load_dropdown.get(0).options.add(new Option(name, encoded));
	        load_dropdown.val(encoded);
	        $('#pipeline-save-name').val('');
	        $('#pipeline').animate({scrollTop: $('#pipeline').offset().top}, 500, function() {
                $('#pipeline-load').css('background-color', '#C5FFBF').animate({'background-color': 'white'}, 3000);
	        });
	    });
	    return false;
	});
	$('#pipeline-save-go').click(function() {
	    $('#pipeline-save-form').submit();
	});
	$('#pause-loading').change(function() {
	    if ( this.checked === false ) {
	        refreshPipeline();
	    }
	});
	$('#show-sparklines').change(function() {
	    if ( this.checked === true ) {
	        $('.sparkline').show();
	    }
	    else {
	        $('.sparkline').hide();
	    }
	});
	$('#load-large-table').click(function() {
	    startTableSort();
	    $('#output table, #output .foldable.table').show();
	    $('#large-table-confirm').hide();
	});
	$("#select-scenario-cols, #select-value-cols").toChecklist();
	
	$("#pipeline").delegate('select', 'change', refreshPipeline);
	
	$.history.init(hashChange);
});

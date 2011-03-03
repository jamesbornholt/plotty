/**
 * Debugging stuff
 */
if ( typeof console === 'undefined' ) {
    var console = {
        log:   function() {},
        error: function() {}
    }
}


/**
 * Implement prototype methods for arrays, since IE doesn't implement them.
 */
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


var Utilities = {
    /**
     * Update a select element with new options. The old value will be
     * preserved if it appears in the new list.
     *
     * @param element Element The dropdown to have its options updated
     * @param list Array The values of the options
     * @return boolean True if the selection was kept (i.e. the selected value
     *   appears in list)
     */
    updateSelect: function(element, list) {
        var jqElem = $(element);
        var oldValue = jqElem.val();
        var keptSelection = false;
        element = jqElem.get(0);
        element.options.length = 0;
        element.options.add(new Option("[" + list.length + " options]", '-1', true));
        for ( var i = 0; i < list.length; i++ ) {
            element.options.add(new Option(list[i], list[i]));
            if ( list[i] == oldValue ) {
                keptSelection = true;
                element.options.selectedIndex = i+1;
            }
        }
        return keptSelection;
    },
    
    /**
     * Update a multiselect created by the toChecklist plugin. We can
     * optionally either maintain the current selection when updating, or
     * specify a new list of elements to select.
     *
     * @param element Element The multiselect element to update.
     * @param list Array The new available options.
     * @param selectedList Array|Boolean True to keep the old selection, or
     *   a non-empty array to specify a list of selected elements.
     */
    updateMultiSelect: function(element, list, selectedList) {
        var jQElem = $(element);
        // Get the currently selected options if needed
        if ( selectedList === true ) {
            selectedList = Utilities.multiSelectValue(jQElem) || [];
        }
        else if ( typeof selectedList === 'undefined' ) {
            selectedList = [];
        }
        
        // Create a new dropdown and populate it
        var dropdown = document.createElement('select');
        dropdown.multiple = 'multiple';
        dropdown.id = jQElem.attr('id');
        dropdown.name = jQElem.attr('name');
        dropdown.className = jQElem.attr('class');
        
        for ( var i = 0; i < list.length; i++ ) {
            dropdown.options.add(new Option(list[i], list[i]));
            if ( jQuery.inArray(list[i], selectedList) > -1 ) {
                dropdown.options[i].selected = true;
            }
        }
        
        // Replace the old select
        var wasVisible = jQElem.is(':visible');
        jQElem.replaceWith(dropdown);
        if ( wasVisible ) {
            $(dropdown).toChecklist();
        }
    },
    
    /**
     * Get the value of a multiselect.
     *
     * @param element Element The multiselect element.
     * @return Array The selected values of the given multiselect.
     */
    multiSelectValue: function(element) {
        return $('input:checked', element).map(function() {
            return this.value;
        }).get();
    }
};


/**
 * The basic Block object
 */
var Block = Base.extend({
    /**
     * The HTML div that contains this block.
     */
    element: null,
    
    /**
     * Where to find the template for this block
     */
    templateID: null,
    
    /**
     * Construct a new block. The block will be inserted into the pipeline
     * at the given index. This method should create the new HTML elements
     * and insert them into the page. It can also take an optional parameter
     * string, which it should decode and update appropriately
     *
     * @param insertIndex int The index to insert the block at, where 0 is
     *   before the first block so n is after the n-th block.
     * @param params string (optional) A parameter string that this block
     *   should be set to
     */
    constructor: function(insertIndex, params) {
        // Spawn the new block and clear its ID
        var newBlock = $(this.templateID).clone();
        newBlock.attr('id', '');
        
        // Insert the block.
        var existingBlocks = $("#pipeline .pipeline-block");
        if ( insertIndex > existingBlocks.length ) {
            console.error("Trying to insert a new block at index " + insertIndex + " when there are only " + existingBlocks.length + " blocks.");
            return;
        }
        
        if ( existingBlocks.length > 0 ) {
            existingBlocks.eq(insertIndex - 1).after(newBlock);
        }
        else {
            newBlock.insertBefore('#pipeline-add');
        }
        
        // Hook the remove button
        $(".remove-button", newBlock).click({block: this}, function(e) {
            Pipeline.removeBlock(e.data.block);
        });
        
        this.element = newBlock;
        
        // Decode the parameter string if it's there
        if ( typeof params !== 'undefined' ) {
            this.decode(params);
        }
    },
    
    /**
     * Decode a parameter string and set this block's configuration according
     * to those parameters.
     *
     * @param params string A parameter string that this block should be set
     *   to
     */
    decode: function(params) {
        
    },
    
    /**
     * Encode this block into a parameter string based on its configuration.
     *
     * @return An encoded parameter string that would recreate this object's
     *   settings if fed to decode()
     */
    encode: function() {
        
    },

    /**
     * Take this block's HTML, and use those values to update the local
     * configurations.
     */
    readState: function() {
        
    },

    /**
     * Take this block's local configurations, and use them to update the
     * HTML for this block.
     */
    loadState: function() {
        
    },
    
    /**
     * The available scenario or value columns have changed, so we need to
     * cascade those changes through the pipeline. If these changes have 
     * forced a change in our configuration (e.g. if a scenario column we were
     * using has disappeared), warn the user somehow.
     * This function should validate the block's local configuration, and,
     * if something has changed, call loadState to update the block.
     *
     * @param scenarioCols array The scenario columns available
     * @param valueCols array the value columns now available
     * @param reason int The reason for cascading
     * @return [newScenarioCols, newValueCols], where newScenarioCols and
     *   newValueCols contain the available scenario and value columns
     *   respectively after this block takes effect
     */
    cascade: function(scenarioCols, valueCols, reason) {
        
    },
    
    /**
     * Remove this block from the DOM
     */
    removeBlock: function() {
        $(this.element).remove();
    }
});


/**
 * The available block implementations
 */
var Blocks = {
    /**
     * The filter block allows certain filters to be specified that will
     * remove rows from the data.
     * TODO more complex filtering - AND/OR combinations
     */
    FilterBlock: Block.extend({
        /**
         * The ID of the template for this filter
         */
        templateID: "#pipeline-filter-template",
        
        /**
         * The currently valid filters
         */
        filters: [{scenario: -1, is: 1, value: -1}],
        
        /**
         * The options table for selecting filters
         */
        optionsTable: null,
        
        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex, params) {
            this.base(insertIndex, params);
            
            // Create a closure to use as the callback for removing objects.
            // This way, the scope of this block is maintained.
            var thisBlock = this;
            var removeClosure = function(row) {
                thisBlock.removeFilter.call(thisBlock, row); 
            };
            var addClosure = function(row) {
                thisBlock.filters.push({scenario: -1, is: 1, value: -1});
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED);
            };
            
            // Create the option table
            this.optionsTable = new OptionsTable($('.pipeline-filter-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the dropdowns
            $(this.element).delegate('select', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED);
            });
        },
        
        /**
        * Decode a parameter string and set this block's configuration according
        * to those parameters.
         */
        decode: function(params) {
            var filts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            var thisBlock = this;
            jQuery.each(filts, function(i ,filter) {
                var parts = filter.split(Pipeline.encoder.PARAM_SEPARATOR);
                thisBlock.filters.push({scenario: parts[0], is: (parts[0] == Pipeline.constants.filter.IS), value: parts[2]});
            });
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = []
            jQuery.each(this.filters, function(i, filter) {
                if ( filter.scenario != -1 && filter.value != -1 ) {
                    strs.push(filter.scenario + Pipeline.encoder.PARAM_SEPARATOR
                              + (filter.is ? Pipeline.constants.filter.IS : Pipeline.constants.filter.IS_NOT)
                              + Pipeline.encoder.PARAM_SEPARATOR + filter.value);
                }
            });
            return strs.join(Pipeline.encoder.GROUP_SEPARATOR);
        },

        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
            this.filters = [];
            var thisBlock = this;
            $('tr', this.element).each(function() {
                var scenarioSelect = $('.select-filter-column', this);
                var isSelect = $('.select-filter-is', this);
                var valueSelect = $('.select-filter-value', this);

                thisBlock.filters.push({
                    scenario: scenarioSelect.val(),
                    is: (isSelect.val() == Pipeline.constants.filter.IS),
                    value: valueSelect.val()
                });
            });
        },

        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            // Get rid of all but the first row
            this.optionsTable.reset();
            
            // Create new rows for each filter
            var thisBlock = this;
            jQuery.each(this.filters, function(i, filter) {
                var row = thisBlock.optionsTable.addRow();
                var scenarioSelect = $('.select-filter-column', row);
                var isSelect = $('.select-filter-is', row);
                var valueSelect = $('.select-filter-value', row);
                
                // Note here we assume the scenario dropdown has already been
                // updated, and the value cache is also up to date with new
                // logs.
                scenarioSelect.val(filter.scenario);
                isSelect.val( (filter.is ? Pipeline.constants.filter.IS : Pipeline.constants.filter.IS_NOT) );
                if ( filter.scenario != -1 ) {
                    Utilities.updateSelect(valueSelect, Pipeline.valueCache[filter.scenario]);
                }
                else {
                    Utilities.updateSelect(valueSelect, []);
                }
                valueSelect.val(filter.value);
            });
        },
        
        /**
         * Visit this block and cascade the available scenario and value 
         * columns. See Block.cascade for parameters and return.
         */
        cascade: function(scenarioCols, valueCols, reason) {
            var thisBlock = this;
            var changed = false;
            
            // Update the scenario columns
            $('.select-filter-column', this.element).each(function() {
                Utilities.updateSelect(this, scenarioCols, true);
            });
            
            jQuery.each(this.filters, function(i, filter) {
                // If the selected scenario isn't in the new available ones,
                // reset this row
                if ( jQuery.inArray(filter.scenario, scenarioCols) == -1 ) {
                    filter.scenario = -1;
                    filter.value = -1;
                    changed = true;
                    return;
                }
                
                // Check that the value is still in the valueCache
                if ( jQuery.inArray(filter.value, Pipeline.valueCache[filter.scenario]) == -1 ) {
                    filter.value = -1;
                    changed = true;
                    return;
                }
                
                // We now have valid scenario and value. Remove the scenario
                // from scenarioCols
                if ( filter.is ) {
                    scenarioCols.remove(filter.scenario);
                }
            });
            
            // If the values have changed, or the logs have changed (and thus
            // the valueCache), we have to reload the HTML.
            if ( changed || reason == Pipeline.constants.CASCADE_REASON_LOGS_CHANGED ) {
                this.loadState();
            }
            
            if ( changed ) {
                return false;
            }
            else {
                return [scenarioCols, valueCols];
            }
        },
        
        /**
         * A row is about to be removed from the OptionsTable. We need to
         * clean it up here.
         *
         * @param row Element The table row to be removed
         */
        removeFilter: function(row) {
            var value = this.filterValue(row);
            
            for ( var i = 0; i < this.filters.length; i++ ) {
                if ( this.filters[i].scenario == value.scenario
                     && this.filters[i].is == value.is
                     && this.filters[i].value == value.value ) {
                    this.filters.splice(i, 1);
                    break;
                }
            }
        },
        
        /**
         * Turns a <tr> in the OptionsTable into a dictionary
         *
         * @param row Element The table row to gather values from
         * @return dict|boolean The values in the given row, or false if
         *   the selection is incomplete
         */
        filterValue: function(row) {
            var scenario = $('.select-filter-column', row).val();
            var is       = $('.select-filter-is', row).val();
            var value    = $('.select-filter-value', row).val();
            
            return {scenario: scenario, is: (is == Pipeline.constants.filter.IS), value: value};
        }
    }),
    
    
    /**
     * The aggregate block allows rows of data to be aggregated together
     * based on matching values in a scenario column.
     * TODO: multiple column aggregate?
     */
    AggregateBlock: Block.extend({
        /**
         * The ID of the template for this filter
         */
        templateID: "#pipeline-aggregate-template",
        
        /**
         * The scenario column to aggregate over
         */
        column: -1,
        
        /**
         * The type of aggregate to use. This should be a value from
         * Pipeline.constants.aggregate
         */
        type: null,
        
        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex, params) {
            this.base(insertIndex, params);
            this.type = Pipeline.constants.aggregate.MEAN;
            
            // Hook the dropdowns
            var thisBlock = this;
            $(this.element).delegate('select', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED);
            });
        },
        
        /**
         * Decode a parameter string and set this block's configuration according
         * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            this.type = parts[0];
            this.column = parts[1];
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            return this.type + Pipeline.encoder.GROUP_SEPARATOR + this.column;
        },

        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
            var typeSelect = $('.select-aggregate-type', this.element);
            var scenarioSelect = $('.select-aggregate-column', this.element);
            
            this.type = typeSelect.val();
            this.column = scenarioSelect.val();
        },
        
        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            // By the time this function is called, the scenario dropdown
            // should already have been updated with available scenario
            // columns
            var typeSelect = $('.select-aggregate-type', this.element);
            var scenarioSelect = $('.select-aggregate-column', this.element);
            
            typeSelect.val(this.type);
            scenarioSelect.val(this.column);
        },
        
        /**
         * Visit this block and cascade the available scenario and value 
         * columns. See Block.cascade for parameters and return.
         */
        cascade: function(scenarioCols, valueCols, reason) {
            // Update the scenario column dropdown. If the selection was not
            // kept, the block is invalid.
            var scenarioSelect = $('.select-aggregate-column', this.element);
            if ( !Utilities.updateSelect(scenarioSelect, scenarioCols) ) {
                this.column = -1;
                return false;
            }
            else {
                scenarioCols.remove(this.column);
                return [scenarioCols, valueCols];
            }
        }
    }),
    
    
    /**
     * The normalise blocks allows data to be normalised to a specific value,
     * selected either by selecting a combination of scenario columns and
     * values, or by finding the best value in the group.
     */
    NormaliseBlock: Block.extend({
        /**
         * The ID of the template for this filter
         */
        templateID: "#pipeline-normalise-template",
        
        /**
         * The type of normaliser. This should be a value from
         * Pipeline.constants.normaliser
         */
        type: null,
        
        /**
         * The scenario that selects the normaliser. This only exists if
         * the type of normaliser is SELECT.
         */
        normaliser: [{scenario: -1, value: -1}],
        
        /**
         * The scenario columns used to group the rows before normalising.
         * Scenario columns can appear in either this or normaliser (if type
         * is SELECT), but not both.
         */
        group: [],
        
        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex, params) {
            this.base(insertIndex, params);
            
            // Create a closure to use as the callback for removing objects.
            // This way, the scope of this block is maintained.
            var thisBlock = this;
            var removeClosure = function(row) {
                thisBlock.removeNormaliser.call(thisBlock, row); 
            };
            var addClosure = function(row) {
                thisBlock.normaliser.push({scenario: -1, value: -1});
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED);
            };
            
            // Create the option table
            this.optionsTable = new OptionsTable($('.pipeline-normalise-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the dropdowns
            $(this.element).delegate('select, .select-normalise-group input', 'change', function() {
		        thisBlock.readState();
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED_NORMALISER);
            });
            
            // We need to give the radio buttons a unique name to make sure
            // they toggle correctly.
            var radios = $('input:radio', this.element);
            radios.attr('name', 'normalise-type-' + parseInt(Math.random() * 1E7));
            
            // By default we are selecting a specific normaliser
            radios.first().attr('checked', 'checked');
            this.type = Pipeline.constants.normaliser.SELECT;
            
            // Hook the radio buttons to show/hide the table
            radios.change(function() {
                if ( !this.checked ) {
                    return;
                }
                if ( this.value == Pipeline.constants.normaliser.SELECT ) {
                    thisBlock.optionsTable.element.show();
                }
                else if ( this.value == Pipeline.constants.normaliser.BEST ) {
                    thisBlock.optionsTable.element.hide();
                }
                thisBlock.readState();
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED)
            });
        },
        
        /**
        * Decode a parameter string and set this block's configuration according
        * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            this.type = parts[0];
            this.normaliser = [];
            this.group = [];
            
            if ( this.type == Pipeline.constants.normaliser.SELECT ) {
                for ( var i = 1; i < parts.length; i++ ) {
                    if ( parts[i].indexOf(Pipeline.encoder.PARAM_SEPARATOR) > -1 ) {
                        var opts = parts[i].split(Pipeline.encoder.PARAM_SEPARATOR);
                        this.normaliser.push({scenario: opts[0], value: opts[1]});
                    }
                    else {
                        this.group.push(parts[i]);
                    }
                }
            }
            else {
                this.group = parts.slice(1);
            }
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = []
            strs.push(this.type);
            if ( this.type == Pipeline.constants.normaliser.SELECT ) {
                jQuery.each(this.normaliser, function(i, norm) {
                    if ( norm.scenario != -1 && norm.value != -1 ) {
                        strs.push(norm.scenario + Pipeline.encoder.PARAM_SEPARATOR + norm.value);
                    }
                });
            }
            strs.push(this.group.join(Pipeline.encoder.PARAM_SEPARATOR));
            
            return strs.join(Pipeline.encoder.GROUP_SEPARATOR);
        },
				 
        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
	        this.group = [];
	        this.normaliser = [];
	    
	        // Read the type
	        this.type = $('input:radio:checked', this.element).val();
	    
	        // If needed, read the normaliser
	        if ( this.type == Pipeline.constants.normaliser.SELECT ) {
	            var thisBlock = this;
		        $('tr', this.element).each(function() {
		            var scenarioSelect = $('.select-normalise-column', this);
		            var valueSelect = $('.select-normalise-value', this);
		            
		            thisBlock.normaliser.push({
			            scenario: scenarioSelect.val(),
			            value: valueSelect.val()
		            });
		        });
	        }
	    
	        // Read the grouping
	        this.group = Utilities.multiSelectValue($('.select-normalise-group', this.element));
	    },
	
	    /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
	        if ( this.type == Pipeline.constants.normaliser.SELECT ) {
		        // Show and reset the table
		        this.optionsTable.element.show();
		        this.optionsTable.reset();
		        
		        var thisBlock = this;
		        jQuery.each(this.normaliser, function(i, norm) {
		            var row = thisBlock.optionsTable.addRow();
		            var scenarioSelect = $('.select-normalise-column', row);
		            var valueSelect = $('.select-normalise-value', row);
		            
		            // Note here we assume the scenario dropdown has already been updated
		            scenarioSelect.val(norm.scenario);
		            if ( norm.scenario == -1 ) {
		        	    Utilities.updateSelect(valueSelect, []);
		            }
		            else {
		        	    Utilities.updateSelect(valueSelect, Pipeline.valueCache[norm.scenario]);
		            }
		            valueSelect.val(norm.value);
		        });
	        }
	        else {
		        // Hide the table, and reset it anyway
		        this.optionsTable.element.hide();
	        }

		    // Update the grouping
		    var thisBlock = this;
		    $('.select-normalise-group input:checkbox', this.element).each(function() {
		        if ( jQuery.inArray($(this).val(), thisBlock.group) > -1 ) {
		            $(this).attr('checked', 'checked');
		        }
		        else {
		            $(this).attr('checked', '');
		        }
		    });
	    },
        
        /**
         * Visit this block and cascade the available scenario and value 
         * columns. See Block.cascade for parameters and return.
         */
        cascade: function(scenarioCols, valueCols, reason) {
            var thisBlock = this;
            var changed = false;
            
            // We don't want to remove scenario cols prematurely
            var returnScenarioCols = scenarioCols.slice();
            
            // If we are selecting a normaliser, we need to update the 
            // options table.
            if ( this.type == Pipeline.constants.normaliser.SELECT ) {
                // Update all the scenario columns
                $('.select-normalise-column', this.optionsTable.element).each(function() {
                    Utilities.updateSelect(this, scenarioCols, true);
                });
                
                jQuery.each(this.normaliser, function(i, norm) {
                    // If the selected scenario isn't in the new available ones,
                    // reset this row
                    if ( jQuery.inArray(norm.scenario, scenarioCols) == -1 ) {
                        norm.scenario = -1;
                        norm.value = -1;
                        changed = true;
                        return;
                    }
                    
                    // Check that the value is still in the value cache
                    if ( jQuery.inArray(norm.value, Pipeline.valueCache[norm.scenario]) == -1 ) {
                        norm.value = -1;
                        changed = true;
                        return;
                    }
                    
                    // We now have a valid scenario and value. Remove this scenario
                    // from returnScenarioCols
                    returnScenarioCols.remove(norm.scenario);
                });
            }
            
            // Update the groups
            Utilities.updateMultiSelect($('.select-normalise-group', this.element), scenarioCols, true);
            
            // Check that all the groups are in the new scenario cols
            jQuery.each(this.group, function(i, grp) {
                if ( jQuery.inArray(grp, scenarioCols) == -1 ) {
                    // This is safe due to the way jQuery.each iterates.
                    thisBlock.group.splice(i, 1);
                    changed = true;
                }
                else {
                    returnScenarioCols.remove(grp);
                }
            });
            
            // If the values have changed, or the logs have changed (and thus
            // the valueCache), we have to reload the HTML.
            if ( changed || reason == Pipeline.constants.CASCADE_REASON_LOGS_CHANGED ) {
                this.loadState();
            }
            
            if ( changed ) {
                return false;
            }
            else {
                return [returnScenarioCols, valueCols];
            }
        },
        
        /**
         * A row is about to be removed from the OptionsTable. We need to
         * clean it up here.
         *
         * @param row Element The table row to be removed
         */
        removeNormaliser: function(row) {
            var value = this.normaliserValue(row);

            for ( var i = 0; i < this.normaliser.length; i++ ) {
                if ( this.normaliser[i].scenario == value.scenario && this.normaliser[i].value == value.value ) {
                    this.normaliser.splice(i, 1);
                    break;
                }
            }
        },
        
        /**
         * Turns a <tr> in the OptionsTable into a dictionary
         *
         * @param row Element The table row to gather values from
         * @return dict|boolean The values in the given row, or false if
         *   the selection is incomplete
         */
        normaliserValue: function(row) {
            var scenario = $('.select-normalise-column', row).val();
            var value    = $('.select-normalise-value', row).val();
            return {scenario: scenario, value: value};
        }
    }),
    
    
    /**
     *
     */
    GraphBlock: Block.extend({
        /**
         * The ID of the template for this filter
         */
        templateID: "#pipeline-graph-template",
        
        /**
         * The type of graph. Should be a value from Pipeline.constants.graph
         */
        type: null,
        
        /**
         * The options for the specified graph
         */
        options: {},
        
        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex, params) {
            this.base(insertIndex, params);
            this.type = Pipeline.constants.graph.HISTOGRAM;
            
            // Hook the dropdowns
            var thisBlock = this;
            $(this.element).delegate('select', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh(Pipeline.constants.CASCADE_REASON_SELECTION_CHANGED);
            });
            
            // Hide all blocks except our default one
            $('.pipeline-graph-type-options', this.element).hide();
            $('.graph-histogram', this.element).show();
            $('.select-graph-type').val(this.type);
        },
        
        /**
         * Decode a parameter string and set this block's configuration according
         * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            this.type = parts[0];
            if ( this.type == Pipeline.constants.graph.HISTOGRAM || this.type == Pipeline.constants.graph.XY ) {
                this.options = {
                    column: parts[1],
                    row: parts[2],
                    value: parts[3]
                };
            }
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = [];
            strs.push(this.type);
            if ( this.type == Pipeline.constants.graph.HISTOGRAM || this.type == Pipeline.constants.graph.XY ) {
                strs.push(this.options.column);
                strs.push(this.options.row);
                strs.push(this.options.value);
            }
            
            return strs.join(Pipeline.encoder.GROUP_SEPARATOR);
        },
        
        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
            this.options = {};
            
            // Read the type
            this.type = $('.select-graph-type', this.element).val();
            
            // These could be consolidated, but are left split as an example
            // of how to do more complicated graphs with different options.
            if ( this.type == Pipeline.constants.graph.HISTOGRAM ) {
                var blockOptions = $('.graph-histogram', this.element);

                var columnSelect = $('.select-graph-column', blockOptions);
                var rowSelect = $('.select-graph-row', blockOptions);
                var valueSelect = $('.select-graph-value', blockOptions);
                
                this.options.column = columnSelect.val();
                this.options.row = rowSelect.val();
                this.options.value = valueSelect.val();
            }
            else if ( this.type == Pipeline.constants.graph.XY ) {
                var blockOptions = $('.graph-xy', this.element);

                var columnSelect = $('.select-graph-column', blockOptions);
                var rowSelect = $('.select-graph-row', blockOptions);
                var valueSelect = $('.select-graph-value', blockOptions);
                
                this.options.column = columnSelect.val();
                this.options.row = rowSelect.val();
                this.options.value = valueSelect.val();
            }
        },
        
        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            // Hide all the blocks (we'll show one soon)
            $('.pipeline-graph-type-options', this.element).hide();
            
            // Set the type dropdown
            $('.select-graph-type').val(this.type);
            
            // These could be consolidated, but are left split as an example
            // of how to do more complicated graphs with different options.
            if ( this.type == Pipeline.constants.graph.HISTOGRAM ) {
                var blockOptions = $('.graph-histogram', this.element);
                
                // Show this block
                blockOptions.show();

                var columnSelect = $('.select-graph-column', blockOptions);
                var rowSelect = $('.select-graph-row', blockOptions);
                var valueSelect = $('.select-graph-value', blockOptions);
                
                columnSelect.val(this.options.column);
                rowSelect.val(this.options.row);
                valueSelect.val(this.options.value);
            }
            else if ( this.type == Pipeline.constants.graph.XY ) {
                var blockOptions = $('.graph-xy', this.element);
                
                // Show this block
                blockOptions.show();

                var columnSelect = $('.select-graph-column', blockOptions);
                var rowSelect = $('.select-graph-row', blockOptions);
                var valueSelect = $('.select-graph-value', blockOptions);
                
                columnSelect.val(this.options.column);
                rowSelect.val(this.options.row);
                valueSelect.val(this.options.value);
            }
        },
        
        /**
         * Visit this block and cascade the available scenario and value 
         * columns. See Block.cascade for parameters and return.
         */
        cascade: function(scenarioCols, valueCols, reason) {
            var valid = true;
            
            $('.pipeline-graph-type-options', this.element).hide();
            
            // These could be consolidated, but are left split as an example
            // of how to do more complicated graphs with different options.
            if ( this.type == Pipeline.constants.graph.HISTOGRAM ) {
                var blockOptions = $('.graph-histogram', this.element);
                
                // Show this block
                blockOptions.show();

                var columnSelect = $('.select-graph-column', blockOptions);
                var rowSelect = $('.select-graph-row', blockOptions);
                var valueSelect = $('.select-graph-value', blockOptions);
                
                if ( !Utilities.updateSelect(columnSelect, scenarioCols) ) {
                    this.options.column = -1;
                    valid = false;
                }
                if ( !Utilities.updateSelect(rowSelect, scenarioCols) ) {
                    this.options.row = -1;
                    valid = false;
                }
                if ( !Utilities.updateSelect(valueSelect, valueCols) ) {
                    this.options.value = -1;
                    valid = false;
                }
                
                if ( valid ) {
                    scenarioCols.remove(this.options.column);
                    scenarioCols.remove(this.options.row);
                }
                
            }
            else if ( this.type == Pipeline.constants.graph.XY ) {
                var blockOptions = $('.graph-xy', this.element);
                
                // Show this block
                blockOptions.show();

                var columnSelect = $('.select-graph-column', blockOptions);
                var rowSelect = $('.select-graph-row', blockOptions);
                var valueSelect = $('.select-graph-value', blockOptions);
                
                if ( !Utilities.updateSelect(columnSelect, scenarioCols) ) {
                    this.options.column = -1;
                    valid = false;
                }
                if ( !Utilities.updateSelect(rowSelect, scenarioCols) ) {
                    this.options.row = -1;
                    valid = false;
                }
                if ( !Utilities.updateSelect(valueSelect, valueCols) ) {
                    this.options.value = -1;
                    valid = false;
                }
                
                if ( valid ) {
                    scenarioCols.remove(this.options.column);
                    scenarioCols.remove(this.options.row);
                }
            }
            
            if ( valid ) {
                return [scenarioCols, valueCols];
            }
            else {
                return false;
            }
        }
    })
};


/**
 * A table that can contain multiple rows of options.
 */
var OptionsTable = Base.extend({
    /**
     * The table element this OptionsTable relates to
     */
    element: null,
    
    /**
     * The callback to call after a row is added.
     */
    addCallback: null,

    /**
     * The callback to call before a row is removed.
     */
    preRemoveCallback: null,
    
    /**
     * The callback to call after a row is removed.
     */
    postRemoveCallback: null,

    /**
     * The number of rows in the table currently.
     */
    numRows: 0,
    
    /**
     * Initialise the table's event handlers and the like.
     *
     * @param element Element The table to transform. This table should have
     *   a first row that will be used as a template for creating new rows.
     * @param preRemoveCallback function(Element) The callback to fire before
     *   a row is removed from this option table. The callback will be passed
     *   the <tr> element to be removed. The default is null.
     * @param postRemoveCallback function() The callback to fire when a row is
     *   removed from this option table. By default this is Pipeline.refresh()
     * @param addCallback function() The callback to fire when a row is added
     *   to this option table. By default this is null.
     */
    constructor: function(element, preRemoveCallback, postRemoveCallback, addCallback) {
        this.element = $(element);
        if ( typeof preRemoveCallback !== 'undefined' ) {
            this.preRemoveCallback = preRemoveCallback;
        }
        if ( typeof postRemoveCallback === 'undefined' ) {
            this.postRemoveCallback = Pipeline.refresh;
        }
        else {
            this.postRemoveCallback = postRemoveCallback;
        }
        if ( typeof addCallback !== 'undefined' ) {
            this.addCallback = addCallback;
        }
        // Hook elements on the table
        $(".add-row", element).live("click", {table: this}, function(e) {
            e.data.table._addBlockTableRow.call(e.data.table);
        });
        $(".remove-row", element).live("click", {table: this}, function(e) {
            // Strange IE bug where disabled buttons still fire click events 
            if ( this.disabled ) return;
            e.data.table._removeBlockTableRow.call(e.data.table, this);
        });
        
        this._clearSelects(element);
    },

    /**
     * Reset the table to a blank state
     */
    reset: function() {
        $('tr', this.element).not(':first').remove();
        this.numRows = 0;
    },

    /**
     * Create a new row and return it for use programatically
     * (as opposed to being created by the user clicking +)
     */
    addRow: function() {
        var row = $('tr', this.element).eq(0);
        this.numRows += 1;

        // If the table is blank, we should return the first row.
        // Otherwise, create a new one.
        if ( this.numRows > 1 ) {
            row = row.clone();
            this.element.append(row);
        }
        
        this._updateAddRemoveButtons();

        return row;
    },
    
    /**
     * Update the add/remove buttons on a table of option rows
     */
    _updateAddRemoveButtons: function() {
        var rows = $('tr', this.element);
        if ( rows.length > 1 ) {
            $('.remove-row', rows).attr('disabled', '');
            $('.add-row', rows).css('display', 'none');
        }
        else {
            $('.remove-row', rows).attr('disabled', 'disabled');
        }
        $('tr:last-child .add-row', this.element).css('display', 'block');
    },
    
    /**
     * Add a new row to a table of option rows
     */
    _addBlockTableRow: function() {
        var newRow = $('tr:first-child', this.element).clone();

        this.numRows += 1;

        this._clearSelects(newRow);

        this.element.append(newRow);

        this._updateAddRemoveButtons();

        if ( this.addCallback !== null ) {
            this.addCallback.call(this);
        }
    },
    
    /**
     * Remove a row from the table of option rows, as given by the button
     * that was clicked
     *
     * @param button Element The button that triggered the removal
     */
    _removeBlockTableRow: function(button) {
        var row = $(button).parents('tr');
        
        if ( this.preRemoveCallback !== null ) {
            this.preRemoveCallback.call(this, row);
        }
        
        $(button).parents('tr').remove();
        this._updateAddRemoveButtons();
        
        if ( this.postRemoveCallback !== null ) {
            this.postRemoveCallback.call(this);
        }
    },
    
    /**
     * Clear the selects in a row
     *
     * @param elements Element The element which contains those selects to
     *   clear.
     */
    _clearSelects: function(elements) {
        $('select', elements).each(function() {
            if ( $(this).is('.scenario-column, .value-column, .scenario-column-values') ) {
                Utilities.updateSelect(this, []);
            }
            this.selectedIndex = 0;
        });
    }
});


/**
 * Constructs an encoded pipeline string
 */
var PipelineBuilder = Base.extend({
    
});


var Pipeline = {
    /**
     * Some constants
     */
    constants: {
        // Type of filter
        filter: {
            IS: 1,
            IS_NOT: 2
        },
        
        // Type of aggregate
        aggregate: {
            MEAN: 1,    // Arithmetic mean
            GEOMEAN: 2  // Geometric mean
        },
        
        // Type of normaliser
        normaliser: {
            SELECT: 1,  // A specific scenario is the normaliser
            BEST: 2     // The best value in the group is the normaliser
        },
        
        // Type of graph
        graph: {
            HISTOGRAM: 1, // Bar chart
            XY: 2         // XY scatter plot
        },
        
        // Reasons for cascade being called
        CASCADE_REASON_LOGS_CHANGED: 1,      // Available logs have changed
        CASCADE_REASON_BLOCK_ADDED: 2,       // A new block was added
        CASCADE_REASON_BLOCK_REMOVED: 3,     // A block was removed
        CASCADE_REASON_SELECTION_CHANGED: 4, // A selection changed 
        CASCADE_REASON_SELECTION_CHANGED_NORMALISER: 5    // Scenario selection changed
    },
    
    /**
     * Some special strings for pipeline encoding
     */
    encoder: {
        BLOCK_SEPARATOR: "|",
        GROUP_SEPARATOR: "&",
        PARAM_SEPARATOR: "^"
    },
    
    /**
     * Caches the available values for scenario columns. Should be invalidated
     * when the selected logs change.
     */
    valueCache: {},
    
    /**
     * The option table for log files
     */
    logFileOptionTable: null,
    
    /**
     * Blocks in the pipeline
     */
    blocks: [],
    
    /**
     ** Public methods
     **/
    
    /**
     * Initialise things that need to be set up at runtime. This should be
     * called after the DOM is ready.
     */
    init: function() {
        console.debug("Pipeline.init start");
        
        // Set up AJAX request options
        $.ajaxSetup({
            cache: false,
            // TODO: A nice exception handler for AJAX failure
            error: function(xhr, textStatus, errorThrown) {
                console.log("ajax failed: ", xhr, textStatus, errorThrown);
            }
        });
        $('#loading-indicator').ajaxStart(function() {
            $(this).show();
        }).ajaxStop(function() {
            $(this).hide();
        });
        
        // Create the options table for log files
        this.logFileOptionTable = new OptionsTable($('#pipeline-log-table'), null, Pipeline.refreshAvailableColumns);
        
        // Hook the log selection dropdowns
        $("#pipeline-log").delegate(".select-log", 'change', Pipeline.refreshAvailableColumns);
        
        // Turn the scenario and value column selects into multiselects
        $("#select-scenario-cols, #select-value-cols").toChecklist();
        
        // Hook the checkboxes in the scenario and value column selects
        $("#pipeline-values").delegate("#select-scenario-cols input, #select-value-cols input", 'change', Pipeline.refresh);
        
        // Hook the add buttons for different blocks
        $('#add-filter').click(function() {
            Pipeline.createBlock(Blocks.FilterBlock);
        });
        $('#add-aggregate').click(function() {
            Pipeline.createBlock(Blocks.AggregateBlock);
        });
        $('#add-normalise').click(function() {
            Pipeline.createBlock(Blocks.NormaliseBlock);
        });
        $('#add-graph').click(function() {
            Pipeline.createBlock(Blocks.GraphBlock);
        });
    },
    
    /**
     * Create a new fresh block and add it to the pipeline at the end.
     * TODO: Add blocks at any index.
     *
     * @param block Block The block class to instantiate
     */
    createBlock: function(block) {
        Pipeline.blocks.push(new block(Pipeline.blocks.length));
        Pipeline.refresh(Pipeline.constants.CASCADE_REASON_BLOCK_ADDED);
    },
    
    /**
     * Remove a block from the pipeline.
     *
     * @param block Block The block to remove
     */
    removeBlock: function(block) {
        Pipeline.blocks.remove(block);
        block.removeBlock();
        Pipeline.refresh(Pipeline.constants.CASCADE_REASON_BLOCK_REMOVED);
    },
    
    /**
     * Try to refresh the pipeline by cascading down the blocks and building
     * the encoded string.
     *
     * @param reason int The reason why this refresh was called. Value comes
     *   from Pipeline.constants.
     */
    refresh: function(reason) {
        var encoded = Pipeline.cascade(reason);
        if ( encoded === false ) {
            console.debug("Pipeline.refresh: Pipeline not valid.");
        }
        else {
            console.debug("Pipeline.refresh: Pipeline valid.");
        }
    },
    
    /**
     * Cascade the available scenario and value columns down the pipeline.
     *
     * @param reason int The reason why this cascade was called. Value comes
     *   from Pipeline.constants.
     * @return string The encoded pipeline, or False if the pipeline is not
     *   valid.
     */
    cascade: function(reason) {
        // Load the initial scenario and value columns from their selectors
        var scenarioCols = Utilities.multiSelectValue($("#select-scenario-cols"));
        var valueCols = Utilities.multiSelectValue($("#select-value-cols"));
        
        // We want to visit every block even if the pipeline is invalid, since
        // we also need to notify blocks about their new scenario and value
        // columns.
        var valid = true;
        
        if ( scenarioCols.length == 0 || valueCols.length == 0 ) {
            console.debug("Pipeline not valid because scenario or value cols empty: [" +  scenarioCols + "], [" + valueCols + "]");
            valid = false;
        }
        
        var ret;
        for ( var i = 0; i < Pipeline.blocks.length; i++ ) {
            ret = Pipeline.blocks[i].cascade(scenarioCols, valueCols, reason);
            if ( ret === false ) {
                console.debug("Block " + i + ": not valid");
                valid = false;
            }
            else {
                console.debug("Block " + i + ": valid, scenario=[" + ret[0] + "], value=[" + ret[1] + "]");
                scenarioCols = ret[0];
                validCols = ret[1];
            }
        }
        
        if ( !valid ) {
            $("#header-config").css('background-color', 'red');
            return false;
        }
        else {
            $('#header-config').css('background-color', 'green');
            return "hello";
        }
    },
    
    /**
     * Refresh the available scenario and value columns by requesting from
     * the server what's available.
     */
    refreshAvailableColumns: function() {
        // Clear the values cache, since a log changed it's invalid now.
        Pipeline.valueCache = {};
        
        // Load new columns.
        var url = 'ajax/log-values/' + Pipeline._selectedLogFiles().join(',') + '/';
        $.getJSON(url, function(data, textStatus, xhr) {
            Pipeline.updateAvailableColumns(data.scenarioCols, data.valueCols);
            Pipeline.valueCache = data.scenarioValues;
            Pipeline.refresh(Pipeline.constants.CASCADE_REASON_LOGS_CHANGED);
        });
    },
    
    /**
     * Update the available scenario and value columns.
     *
     * @param scenarioCols Array The available scenario columns
     * @param valueCols Array The available value columns
     */
    updateAvailableColumns: function(scenarioCols, valueCols) {
        Utilities.updateMultiSelect($("#select-scenario-cols"), scenarioCols, true);
        Utilities.updateMultiSelect($("#select-value-cols"), valueCols, true);
    },
    
    /**
     * Load the available values for a scenario column.
     *
     * @param scenarioCol string The scenario column to load available values
     *   for.
     * @param callback function(Array) The callback function to call when the
     *   data has been loaded. Since this may result in an AJAX request, it
     *   may not happen immediately.
     */
    loadValuesForScenarioColumn: function(scenarioCol, callback) {
        // Check if we already have values in the cache; if so, trigger the
        // callback now with cached values
        if ( scenarioCol in Pipeline.valueCache ) {
            console.debug("Values for " + scenarioCol + " are cached.");
            callback.call(this, Pipeline.valueCache[scenarioCol]);
        }
         
        else {
            var url = 'ajax/filter-values/' + Pipeline._selectedLogFiles().join(',') + '/' + scenarioCol + '/';
            $.getJSON(url, function(data, textStatus, xhr) {
                Pipeline.valueCache[scenarioCol] = data;
                callback.call(this, data);
            });
        }
    },
     
    /**
     ** Utility methods
     **/
     
    /**
     * Return the list of currently selected logs
     */
    _selectedLogFiles: function() {
        var logs = [];
        $('.select-log').each(function() {
            if ( $(this).val() != '-1' ) {
                logs.push($(this).val());
            }
        });
        return logs;
    }
}

$(document).ready(Pipeline.init);
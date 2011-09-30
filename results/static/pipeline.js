
/**
 * Debugging stuff
 */
if ( typeof console === 'undefined' ) {
    var console = {
        log:   function() {},
        error: function() {},
        debug: function() {}
    }
}
// IE 9
if ( typeof console.debug === 'undefined' ) {
    console.debug = console.log;
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
     * Create the html for a foldable div
     */
    makeFoldable: function(title, inner_html, visible) {
        if (visible) {
            return '<div class="foldable"><h1>'+ title +'<button class="foldable-toggle-hide pipeline-button">Hide</button></h1><div class="foldable-content">' + inner_html + '</div></div>'
        }
        return '<div class="foldable"><h1>'+ title +'<button class="foldable-toggle-show pipeline-button">Show</button></h1><div class="foldable-content hidden">' + inner_html + '</div></div>'
    },

    /**
     * Update a select element with new options. The old value will be
     * preserved if it appears in the new list.
     *
     * @param element Element The dropdown to have its options updated
     * @param list Array The values of the options
     * @return boolean True if the selection was kept (i.e. the selected value
     *   appears in list)
     */
    updateSelect: function(element, displayList, list) {
        var jqElem = $(element);
        var oldValue = jqElem.val();
        var keptSelection = false;
        element = jqElem.get(0);
        element.options.length = 0;
        element.options.add(new Option("[" + list.length + " options]", '-1', true));
        for ( var i = 0; i < list.length; i++ ) {
            var o = new Option(list[i], list[i]);
            o.innerHTML = displayList[i];
            element.options.add(o);
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
    updateMultiSelect: function(element, displayList, list, selectedList) {
        var jQElem = $(element);

        var oldDisplay = $(element).data('display');
        var oldList = $(element).data('list');

        if (oldList != null && list.length == oldList.length) {
            var same = true;
            jQuery.each(list, function(i) {
                if (list[i] != oldList[i] || displayList[i] != oldDisplay[i]) {
                    same = false;
                    return false;
                }
            });
            if (same) return;
        }

        // Get the currently selected options if needed
        if ( selectedList === true ) {
            selectedList = Utilities.multiSelectValue(jQElem) || [];
        }
        else if ( typeof selectedList === 'undefined' ) {
            selectedList = [];
        }
        
        // Create a new dropdown and populate it
        var dropdown = document.createElement('select');
        var className = jQElem.attr('class');

        dropdown.multiple = 'multiple';
        dropdown.id = jQElem.attr('id');
        dropdown.name = jQElem.attr('name');
        dropdown.className = className;
        
        for ( var i = 0; i < list.length; i++ ) {
            var o = new Option(list[i], list[i]);
            o.innerHTML = displayList[i];
            dropdown.options.add(o);
            if ( jQuery.inArray(list[i], selectedList) > -1 ) {
                dropdown.options[i].selected = true;
            }
        }
        
        // Replace the old select
        var wasVisible = jQElem.is(':visible');
        jQElem.replaceWith(dropdown);
        var p = $(dropdown).parent();
        if ( wasVisible ) {
            $(dropdown).toChecklist();
        }
        $('.'+className, p).data('display', displayList);
        $('.'+className, p).data('list', list);
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
    },

    /**
     * Initiate table sorting on all output tables
     */
    outputTableSort: function() {
        $('#output table.results').each(function() {
            var numScenarioHeaders = $(this).find('th.scenario-header').length;
            var sortList = [];
            for ( var i = 0; i < numScenarioHeaders; i++ ) {
                sortList.push([i, 0]);
            }
            $(this).tablesorter({sortList: sortList});
        });
    },

    /**
     * Return the set of keys from a map.
     */
    keys: function(theArray) {
        var keys = $.map(theArray, function(value, key) { return key; });
        keys.sort();
        return keys;
    }
};


/**
 * The basic Block object
 */
var Block = Base.extend({
    /**
     ** Static fields
     **/

    /**
     * Where to find the template for this block
     */
    TEMPLATE_ID: null,

    /**
     * The ID of this block for encoding (the inverse of the mapping in
     * Pipeline.encoder.MAPPINGS)
     */
    ID: null,

    /**
     * Possible flags for Block.flags, ORed onto the flagword
     */
    FLAGS: {},

    /**
     ** Object fields
     **/

    /**
     * Caches the available scenario columns.
     */
    scenarioColumnsCache: {},


    /**
     * Caches the available values for scenario columns.
     */
    scenarioValuesCache: {},

    /**
     * Caches the corresponding display values for scenario columns.
     */
    scenarioDisplayCache: {},


    /**
     * Caches the available value columns.
     */
    valueColumnsCache: {},


    /**
     * The HTML div that contains this block.
     */
    element: null,

    /**
     * Block-local flags
     */
    flags: 0,
    
    /**
     ** Object methods
     **/
    
    /**
     * Construct a new block. The block will be inserted into the pipeline
     * at the given index. This method should create the new HTML elements
     * and insert them into the page. It can also take an optional parameter
     * string, which it should decode and update appropriately
     *
     * @param insertIndex int The index to insert the block at, where 0 is
     *   before the first block so n is after the n-th block.
     */
    constructor: function(insertIndex) {
        // Spawn the new block and clear its ID
        var newBlock = $(this.TEMPLATE_ID).clone();
        newBlock.attr('id', '');
        
        // Insert the block.
        var existingBlocks = $("#pipeline .pipeline-block");
        if ( insertIndex > existingBlocks.length ) {
            console.error("Trying to insert a new block at index " + insertIndex + " when there are only " + existingBlocks.length + " blocks.");
            return;
        }
        
        if ( existingBlocks.length == 0 || insertIndex == existingBlocks.length ) {
            newBlock.insertBefore('#pipeline-add');
        }
        else {
            existingBlocks.eq(insertIndex).before(newBlock);
        }
        
        // Hook the remove button
        $(".remove-button", newBlock).click({block: this}, function(e) {
            Pipeline.removeBlock(e.data.block);
        });
        // Hook the insert button
        $(".insert-button", newBlock).click({block: this}, function(e) {
            Pipeline.showInsertButtons(e.data.block.element);
        });
        
        this.element = newBlock;
    },

    /**
     * Modify this.flags by turning the given flag on or off depending on a
     * boolean
     *
     * @param flag The flag to set/clear, should be a power of 2, usually comes
     *   from this.FLAGS
     * @param on true to turn the flag on, false to turn the flag off
     */
    setFlag: function(flag, on) {
        if ( (flag & (flag - 1)) != 0 ) return; // not a power of two
        if ( on ) {
            this.flags |= flag;
        }
        else {
            this.flags &= ~flag;
        }
    },

    /**
     * Read a flag and return a boolean representing its state. We need this
     * because (0 & 1) != false and so will turn checkboxes on.
     *
     * @param flag the flag to read
     * @return boolean true if the flag is on, false if off
     */
    getFlag: function(flag) {
        return (this.flags & flag) != 0;
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
     * Check that the data for this block is still valid after changing
     * the available cache
     */
    checkNewColumns: function() {
    
    },
    
    /**
     * The available scenario or value columns may have changed, so we need to
     * update those changes through the pipeline. If these changes have 
     * forced a change in our configuration (e.g. if a scenario column we were
     * using has disappeared), warn the user somehow.
     */
    validate: function() {
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
         ** Static fields
         **/

        /**
         * The ID of the template for this filter
         */
        TEMPLATE_ID: "#pipeline-filter-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 1,

        /**
         * The type of filter
         */
        TYPE: {
            IS: 1,
            IS_NOT: 2
        },
        
        /**
         ** Object fields
         **/

        /**
         * The currently valid filters
         */
        filters: null,
        
        /**
         * The options table for selecting filters
         */
        optionsTable: null,
        
        /**
         ** Object methods
         **/

        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);

            this.filters = [{scenario: -1, is: 1, value: -1}];
            
            // Create a closure to use as the callback for removing objects.
            // This way, the scope of this block is maintained.
            var thisBlock = this;
            var removeClosure = function(row) {
                thisBlock.removeFilter.call(thisBlock, row); 
            };
            var addClosure = function() {
                thisBlock.filters.push({scenario: -1, is: 1, value: -1});
                thisBlock.loadState();
            };
            
            // Create the option table
            this.optionsTable = new OptionsTable($('.pipeline-filter-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the dropdowns
            $(this.element).delegate('select', 'change', function() {
                thisBlock.readState();
                thisBlock.loadState();
                if (thisBlock.complete()) Pipeline.refresh();
            });
        },
        
        /**
        * Decode a parameter string and set this block's configuration according
        * to those parameters.
         */
        decode: function(params) {
            this.filters = [];
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // There must be at least two - a flagword and one filter
            if ( parts.length < 2 ) {
                console.debug("Filter block invalid: not enough parts");
                return;
            }

            this.flags = parseInt(parts[0]);

            var filts = parts.slice(1);
            var thisBlock = this;
            jQuery.each(filts, function(i ,filter) {
                var settings = filter.split(Pipeline.encoder.PARAM_SEPARATOR);
                // Exactly three parts - scenario, is, value
                if ( settings.length != 3 ) {
                    console.debug("Filter invalid: not enough parts in ", filter);
                }
                thisBlock.filters.push({scenario: settings[0], is: settings[1], value: settings[2]});
            });
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = [this.flags];
            jQuery.each(this.filters, function(i, filter) {
                if ( filter.scenario != -1 && filter.value != -1 ) {
                    strs.push(filter.scenario + Pipeline.encoder.PARAM_SEPARATOR
                              + filter.is + Pipeline.encoder.PARAM_SEPARATOR + filter.value);
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
                    is: isSelect.val(),
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
            var thisBlock = this;
            
            // Update the scenario columns
            $('.select-filter-column', this.element).each(function() {
                Utilities.updateSelect(this, thisBlock.scenarioColumnsCache, thisBlock.scenarioColumnsCache, true);
            });

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
                isSelect.val(filter.is);
                if ( filter.scenario != -1 ) {
                    Utilities.updateSelect(valueSelect, thisBlock.scenarioDisplayCache[filter.scenario], thisBlock.scenarioValuesCache[filter.scenario]);
                }
                else {
                    Utilities.updateSelect(valueSelect, [], []);
                }
                valueSelect.val(filter.value);
            });
        },
       
        refreshColumns: function() {
            var thisBlock = this;
            var changed = false;
            jQuery.each(this.filters, function(i, filter) {
                if ( filter.scenario != -1 && jQuery.inArray(filter.scenario, thisBlock.scenarioColumnsCache) == -1 ) { 
                    thisBlock.filters[i].scenario = -1;
                    changed = true;
                    return;
                } 
                if ( filter.value != -1 && jQuery.inArray(filter.value, thisBlock.scenarioValuesCache[filter.scenario]) == -1 ) {
                    thisBlock.filters[i].value = -1;
                    changed = true;
                    return;
                }
            });

            return changed;
        },

        /**
         * Update this block using newly cached column information.
         */
        complete: function() {
            var valid = true;
            jQuery.each(this.filters, function(i, filter) {
                // If the selected scenario isn't in the new available ones,
                // reset this row
                if ( filter.scenario == -1 || filter.value == -1) {
                    valid = false;
                }
            });

            return valid; 
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
            
            return {scenario: scenario, is: is, value: value};
        }
    }),
    
    
    /**
     * The aggregate block allows rows of data to be aggregated together
     * based on matching values in a scenario column.
     * TODO: multiple column aggregate?
     */
    AggregateBlock: Block.extend({
        /**
         ** Static fields
         **/

        /**
         * The ID of the template for this block
         */
        TEMPLATE_ID: "#pipeline-aggregate-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 2,

        /**
         * The type of aggregate
         */
        TYPE: {
            MEAN: 1,
            GEOMEAN: 2
        },
        
        /**
         ** Object fields
         **/
        
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
         ** Object methods
         **/
        
        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);
            this.type = this.TYPE.MEAN;
            
            // Hook the dropdowns
            var thisBlock = this;
            $(this.element).delegate('select', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh();
            });
        },
        
        /**
         * Decode a parameter string and set this block's configuration according
         * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // Exactly 2 parts - flagword and settings
            if ( parts.length != 2 ) {
                console.debug("Aggregate block invalid: incorrect number of parts");
                return;
            }

            this.flags = parseInt(parts[0]);

            var settings = parts[1].split(Pipeline.encoder.PARAM_SEPARATOR);
            if ( settings.length != 2 ) {
                console.debug("Aggregate block invalid: incorrect number of settings");
                return;
            }
            this.type = settings[0];
            this.column = settings[1];
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            return this.flags + Pipeline.encoder.GROUP_SEPARATOR + this.type + Pipeline.encoder.PARAM_SEPARATOR + this.column;
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
            var typeSelect = $('.select-aggregate-type', this.element);
            var scenarioSelect = $('.select-aggregate-column', this.element);
            
            Utilities.updateSelect(scenarioSelect, this.scenarioColumnsCache, this.scenarioColumnsCache);
            
            typeSelect.val(this.type);
            scenarioSelect.val(this.column);
        },
       
        refreshColumns: function() {
            if (this.column != -1 && jQuery.inArray(this.column, this.scenarioColumnsCache) == -1) {
                this.column = -1;
                return true;
            }
            return false;
        },
 
        complete: function() {
            return this.column != -1;
        },
    }),
    
    
    /**
     * The normalise blocks allows data to be normalised to a specific value,
     * selected either by selecting a combination of scenario columns and
     * values, or by finding the best value in the group.
     */
    NormaliseBlock: Block.extend({
        /**
         ** Static fields
         **/
        
        /**
         * The ID of the template for this filter
         */
        TEMPLATE_ID: "#pipeline-normalise-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 3,

        /**
         * The type of normalisation
         */
        TYPE: {
            SELECT: 1,
            BEST: 2
        },

        /**
         * The available flags for this block
         */
        FLAGS: {
            NORMALISE_TO_SPECIFIC_VALUE: 1 << 0
        },

        /**
         ** Object fields
         **/
        
        /**
         * The type of normaliser. This should be a value from
         * Pipeline.constants.normaliser
         */
        type: null,
        
        /**
         * The scenario that selects the normaliser. This only exists if
         * the type of normaliser is SELECT.
         */
        normaliser: null,
        
        /**
         * The scenario columns used to group the rows before normalising.
         * Scenario columns can appear in either this or normaliser (if type
         * is SELECT), but not both.
         */
        group: null,

        /**
         * The value column to use as normaliser if we're normalising to a
         * specific column
         */
        normaliserValue: null,
        
        /**
         ** Object methods
         **/

        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);

            this.normaliser = [{scenario: -1, value: -1}];
            this.group = [];
            this.normaliserValue = -1;
            
            // Create a closure to use as the callback for removing objects.
            // This way, the scope of this block is maintained.
            var thisBlock = this;
            var removeClosure = function(row) {
                thisBlock.removeNormaliser.call(thisBlock, row); 
            };
            var addClosure = function() {
                thisBlock.normaliser.push({scenario: -1, value: -1});
                thisBlock.loadState();
            };
            
            // Create the option table
            this.optionsTable = new OptionsTable($('.pipeline-normalise-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the dropdowns
            $(this.element).delegate('select, .select-normalise-group input', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh();
            });
            
            // We need to give the radio buttons a unique name to make sure
            // they toggle correctly.
            var allradios = $('input:radio', this.element);
            var typeradios = allradios.filter('.radio-normalise-type');
            var valueradios = allradios.filter('.radio-normalise-value-type');

            var randomId = parseInt(Math.random() * 1E7);
            allradios.each(function(i, elem) {
                $(this).attr('name', $(this).attr('name') + randomId);
            });

            // By default we are selecting a specific normaliser and normalising
            // to the corresponding normaliser
            typeradios.first().attr('checked', true);
            valueradios.first().attr('checked', true);
            this.type = this.TYPE.SELECT;
            
            // Hook the radio buttons to show/hide the table
            typeradios.change(function() {
                if ( !this.checked ) {
                    return;
                }
                if ( this.value == thisBlock.TYPE.SELECT ) {
                    thisBlock.optionsTable.element.show();
                }
                else if ( this.value == thisBlock.TYPE.BEST ) {
                    thisBlock.optionsTable.element.hide();
                }
                thisBlock.readState();
                Pipeline.refresh()
            });

            valueradios.change(function() {
                if ( !this.checked ) {
                    return;
                }
                if ( this.value == thisBlock.FLAGS.NORMALISE_TO_SPECIFIC_VALUE ) {
                    $('.select-normalise-normaliser-value', thisBlock.element).show();
                }
                else {
                    $('.select-normalise-normaliser-value', thisBlock.element).hide();
                }
                thisBlock.readState();
                Pipeline.refresh();
            });
        },

        /**
        * Decode a parameter string and set this block's configuration according
        * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // At least 3 parts - flagword, type, groups (possibly empty)
            if ( parts.length < 3 ) {
                console.debug("Normalise block invalid: incorrect number of parts");
                return
            }

            this.flags = parseInt(parts[0]);
            this.type = parts[1];

            this.normaliser = [];
            this.group = [];

            // Part 3 is the groupings
            var groupings = parts[2].split(Pipeline.encoder.PARAM_SEPARATOR);
            for ( var i = 0; i < groupings.length; i++ ) {
                if ( $.trim(groupings[i]).length > 0 ) { // Make sure it's not empty
                    this.group.push($.trim(groupings[i]));
                }
            }

            // If this is a select normaliser, part 4 is the pairs
            if ( this.type == this.TYPE.SELECT ) {
                if ( parts.length < 4 || $.trim(parts[3]).length == 0 ) {
                    console.debug("Normalise block invalid: no pairings for select normaliser");
                    return;
                }
                var pairs = parts[3].split(Pipeline.encoder.PARAM_SEPARATOR);
                for ( var i = 0; i < pairs.length; i++ ) {
                    var elements = pairs[i].split(Pipeline.encoder.TUPLE_SEPARATOR);
                    if ( elements.length != 2 ) {
                        console.debug("Normalise block: Not a valid pairing: ", pairs[i]);
                        continue;
                    }
                    this.normaliser.push({scenario: elements[0], value: elements[1]});
                }
            }

            // If we are normalising to a specific column, part 5 is that column
            if ( this.getFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE) ) {
                var nextIdx = (this.type == this.TYPE.SELECT ? 4 : 3);
                if ( parts.length <= nextIdx ) {
                    console.debug("Normalise block invalid: no column for normalise value");
                    return;
                }
                this.normaliserValue = $.trim(parts[nextIdx]);
            }
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = [this.flags, this.type];

            strs.push(this.group.join(Pipeline.encoder.PARAM_SEPARATOR));

            if ( this.type == this.TYPE.SELECT ) {
                var pairs = [];
                jQuery.each(this.normaliser, function(i, norm) {
                    if ( norm.scenario != -1 && norm.value != -1 ) {
                        pairs.push(norm.scenario + Pipeline.encoder.TUPLE_SEPARATOR + norm.value);
                    }
                });
                strs.push(pairs.join(Pipeline.encoder.PARAM_SEPARATOR));
            }

            if ( this.getFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE) ) {
                strs.push(this.normaliserValue);
            }
            
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
            if ( this.type == this.TYPE.SELECT ) {
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

            // Read the normaliser column setting
            var n = $('input.radio-normalise-value-type:checked', this.element).val();
            this.setFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE, n == this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE);

            // Read the value column is needed
            if ( n == this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE ) {
                this.normaliserValue = $('.select-normalise-normaliser-value', this.element).val();
            }
        },
    
        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            var typeradios = $('.radio-normalise-type', this.element);
            var valueradios = $('.radio-normalise-value-type', this.element);

            typeradios.removeAttr('checked');
            typeradios.filter('[value=' + this.type + ']').attr('checked', true);

            valueradios.removeAttr('checked');
            valueradios.filter('[value=' + (this.getFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE) & 1) + ']').attr('checked', true);

            // Update all the scenario columns
            var thisBlock = this;
            $('.select-normalise-column', this.optionsTable.element).each(function() {
                Utilities.updateSelect(this, thisBlock.scenarioColumnsCache, thisBlock.scenarioColumnsCache, true);
            });
            // Update the groups
            Utilities.updateMultiSelect($('.select-normalise-group', this.element), thisBlock.scenarioColumnsCache, thisBlock.scenarioColumnsCache, true);

            if ( this.type == this.TYPE.SELECT ) {
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
                        Utilities.updateSelect(valueSelect, [], []);
                    }
                    else {
                        Utilities.updateSelect(valueSelect, thisBlock.scenarioDisplayCache[norm.scenario], thisBlock.scenarioValuesCache[norm.scenario]);
                    }
                    valueSelect.val(norm.value);
                });
            }
            else {
                // Hide the table, and reset it anyway
                this.optionsTable.element.hide();
            }

            // Update the grouping
            $('.select-normalise-group input:checkbox', this.element).each(function() {
                if ( jQuery.inArray($(this).val(), thisBlock.group) > -1 ) {
                    $(this).attr('checked', true);
                }
                else {
                    $(this).removeAttr('checked');
                }
            });

            Utilities.updateSelect($('.select-normalise-normaliser-value', this.element), this.valueColumnsCache, this.valueColumnsCache);
            if ( this.getFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE) ) {
                $('.select-normalise-normaliser-value', this.element).val(this.normaliserValue).show();
            }
            else {
                $('.select-normalise-normaliser-value', this.element).hide();
            }
            
        },
        
        refreshColumns: function() {
            var thisBlock = this;
            var changed = false;

            // If we are selecting a normaliser, we need to update the 
            // options table.
            if ( this.type == this.TYPE.SELECT ) {                
                jQuery.each(this.normaliser, function(i, norm) {
                    // If the selected scenario isn't in the new available ones,
                    // reset this row
                    if ( norm.scenario != -1 && jQuery.inArray(norm.scenario, thisBlock.scenarioColumnsCache) == -1 ) {
                        norm.scenario = -1;
                        norm.value = -1;
                        changed = true;
                        return;
                    }
                    
                    // Check that the value is still in the value cache
                    if ( norm.value != -1 && jQuery.inArray(norm.value, thisBlock.scenarioValuesCache[norm.scenario]) == -1 ) {
                        norm.value = -1;
                        changed = true;
                        return;
                    }
                });
            }
            
            // Check that all the groups are in the new scenario cols
            jQuery.each(this.group, function(i, grp) {
                if ( jQuery.inArray(grp, thisBlock.scenarioColumnsCache) == -1 ) {
                    // This is safe due to the way jQuery.each iterates.
                    thisBlock.group.splice(i, 1);
                    changed = true;
                }
            });

            if ( this.getFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE) ) {
                if ( this.normaliserValue != -1 && jQuery.inArray(this.normaliserValue, this.valueColumnsCache) == -1 ) {
                    this.normaliserValue = -1;
                    changed = true;
                }
            }

            return changed;
        },

        complete: function() {
            var valid = true;
            if ( this.type == this.TYPE.SELECT ) {
                jQuery.each(this.normaliser, function(i, norm) {
                    // If the selected scenario isn't in the new available ones,
                    // reset this row
                    if ( norm.scenario == -1 || norm.value == -1) {
                        valid = false;
                    }
                });
            }

            if ( this.getFlag(this.FLAGS.NORMALISE_TO_SPECIFIC_VALUE) ) {
                if ( this.normaliserValue == -1 ) {
                    valid = false;
                }
            }

            return valid;
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
         ** Static fields
         **/
        
        /**
         * The ID of the template for this filter
         */
        TEMPLATE_ID: "#pipeline-graph-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 4,

        /**
         ** Object fields
         **/
        
        /**
         * The format for the graph.
         */
        format: -1,
       
        /**
         * The column to use for series, includes a special value to use 'values'.
         */ 
        series: -1,

        /**
         * The column to use for pivoting
         */
        pivot: -1,
        
        /**
         * The values selected in this graph 
         */
        values: [-1],

        /**
         * The options table for the values.
         */
        valueOptionsTable: null,

        /**
         ** Object methods
         **/

        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);
            
            // Hook the dropdowns and text inputs
            var thisBlock = this;
            $(this.element).delegate('select, input', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh();
            });
            var removeClosure = function(row) {
                var value = $('.select-graph-value', row).val();
                for ( var i = 0; i < thisBlock.values.length; i++ ) {
                    if ( thisBlock.values[i] == value) {
                        thisBlock.values.splice(i, 1);
                        break;
                    }
                }
            };
            var addClosure = function(row) {
                Utilities.updateSelect($('.select-graph-value', row), thisBlock.valueColumnsCache, thisBlock.valueColumnsCache, true);
                thisBlock.values.push(-1);
            };
            
            // Create the option table
            this.valueOptionsTable = new OptionsTable($('.pipeline-graph-value-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the load button for loading the format
            $("#pipeline-format-load-go", this.element).click(function() {
                thisBlock.popupOpen($('.select-format-key', thisBlock.element).eq(0).val());
            });
            $("#pipeline-format-new-go", this.element).click(function() {
                thisBlock.popupOpen(-1);
            });

            // Hook up the popup
            var popup = $('.popup', this.element);
            $(".text-format-key", popup).change(function() {
                var oldVal = $(popup).data("initial_key");
                var newVal = $(".text-format-key", popup).val();
                if (oldVal == newVal) {
                    $('#popup-format-delete-go', popup).removeAttr("disabled");
                } else {
                    $('#popup-format-delete-go', popup).attr("disabled", "disabled");
                }
            });
            $(".select-format-parent", popup).change(function() {
                var val = $(".select-format-parent", popup).val();
                if (val == '-1') {
                    $('.textarea-format-parent-value', popup).hide();
                } else {
                    $('.textarea-format-parent-value', popup).show();
                    $('.textarea-format-parent-value', popup).val(Pipeline.graphFormatsCache[val]['full_value']);
                }
            });
            $(".cancel-button", popup).click(function() {
                $('.popup', thisBlock.element).hide();
                $('.popupfilter', thisBlock.element).hide();

            });
            $('#popup-format-save-go', popup).click(function() {
                thisBlock.popupSave();
            });
            $("#popup-format-delete-go", popup).click(function() {
                thisBlock.popupDelete();
            });
        },
        
        /**
         * Decode a parameter string and set this block's configuration according
         * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // Exactly three parts - flagword, settings, values
            if ( parts.length != 3 ) {
                console.debug("Graph block invalid: incorrect number of parts");
                return;
            }

            this.flags = parseInt(parts[0]);
            
            var settings = parts[1].split(Pipeline.encoder.PARAM_SEPARATOR);
            
            if (settings.length == 1) {
                // Compatibility: load old style pipeline.
                var errorbars = this.flags == 1;
                this.flags = 0;
                var type = parseInt(settings[0]);
                settings = parts[2].split(Pipeline.encoder.PARAM_SEPARATOR);

                if (type == 1 || type == 2) {
                    this.format = type == 1 ? "Histogram" : "XY"; 
                    this.series = settings[0];
                    this.pivot = settings[1];
                    this.values = [settings[2]];
                } else {
                    this.format = "Scatter";
                    this.values = [settings[0], settings[1]];
                    this.series = settings[2];
                    this.pivot = -1;
                }
                if (errorbars) {
                    this.format += " (with CI)";
                }
            } else {
                this.format = settings[0];
                this.series = settings[1] == '' ? -1 : settings[1];
                this.pivot = settings[2] == '' ? -1 : settings[2];
                this.values = parts[2] == '' ? [-1] : parts[2].split(Pipeline.encoder.PARAM_SEPARATOR);
            }

        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var main = [this.format, this.series == -1 ? '' : this.series, this.pivot == -1 ? '' : this.pivot];
            var valstrs = [] 
            
            jQuery.each(this.values, function(i, value) {
                if ( value != -1 ) {
                    valstrs.push(value);
                }
            });

            var groups = [this.flags, main.join(Pipeline.encoder.PARAM_SEPARATOR), valstrs.join(Pipeline.encoder.PARAM_SEPARATOR)];

            return groups.join(Pipeline.encoder.GROUP_SEPARATOR);
        },
        
        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
            this.format = $('.select-format-key', this.element).val();
            this.series = $('.select-graph-series', this.element).val();
            this.pivot = $('.select-graph-pivot', this.element).val();

            var thisBlock = this;
            this.values = [];
            $('.select-graph-value', this.element).each(function(i, row) {
                thisBlock.values.push($(row).val());
            });
        },
        
        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            var graphFormat = $('.select-format-key', this.element);
            Utilities.updateSelect(graphFormat, Pipeline.graphFormatKeysCache, Pipeline.graphFormatKeysCache);
            graphFormat.val(this.format);

            var seriesSelect = $('.select-graph-series', this.element);
            Utilities.updateSelect(seriesSelect, this.scenarioColumnsCache, this.scenarioColumnsCache);
            seriesSelect.val(this.series);

            var pivotSelect = $('.select-graph-pivot', this.element);
            Utilities.updateSelect(pivotSelect, this.scenarioColumnsCache, this.scenarioColumnsCache);
            pivotSelect.val(this.pivot);

            // Update the value columns
            this.valueOptionsTable.reset();
            var thisBlock = this;
            var valueColumns = thisBlock.valueColumnsCache;
            $('.select-graph-value', this.element).each(function() {
                Utilities.updateSelect(this, valueColumns, valueColumns, true);
            });
            jQuery.each(this.values, function(i, value) {
                var row = thisBlock.valueOptionsTable.addRow();
                var valueSelect = $('.select-graph-value', row);
                valueSelect.val(value);
            });
        },
        
        refreshColumns: function() {
            var changed = false;
            if ( this.format != -1 && jQuery.inArray(this.format, Pipeline.graphFormatKeysCache) == -1 ) {
                this.format = -1;
                changed = true;
            }

            if ( this.series != -1 && jQuery.inArray(this.series, this.scenarioColumnsCache) == -1 ) {
                this.series = -1;
                changed = true;
            }
            
            if ( this.pivot != -1 && jQuery.inArray(this.pivot, this.scenarioColumnsCache) == -1 ) {
                this.pivot = -1;
                changed = true;
            }

            var thisBlock = this;
            jQuery.each(this.values, function(i, value) {
                if (value != -1 && jQuery.inArray(value, thisBlock.valueColumnsCache) == -1 ) {
                    thisBlock.values[i] = -1;
                    changed = true;
                }
            });

            return changed;
        },

        complete: function() {
            var missingValue = false;
            jQuery.each(this.values, function(i, value) {
                if (value == -1) missingValue = true;
            });
            return this.format != -1 && (!missingValue || this.values.length == 1);
        },

        popupOpen: function(key) {
            var popup = $('.popup', this.element);
            popup.show();
            $('.popupfilter', this.element).show();

            key = (key == -1) ? "" : key;
            $(popup).data("initial_key", key);
            
            // Key dropdown and key field
            $('.text-format-key', popup).val(key);

            // Update the parent drop-down
            var parentFormat = $('.select-format-parent', popup);
            Utilities.updateSelect(parentFormat, Pipeline.graphFormatKeysCache, Pipeline.graphFormatKeysCache);

            if (key == "") {
                $('#popup-format-delete-go', popup).hide();
                $('.textarea-format-value', popup).val('');
                parentFormat.val(-1);
                parentFormat.change();
            } else {
                var data = Pipeline.graphFormatsCache[key];
                parentFormat.val(data.parent != null ? data.parent : -1);
                parentFormat.change();
                $('.textarea-format-value', popup).val(data.value);
                $('#popup-format-delete-go', popup).show();
                $('#popup-format-delete-go', popup).removeAttr("disabled");
            }
        },

        popupSave: function() {
            var thisBlock = this;
            var popup = $('.popup', this.element)
            var key = $('.text-format-key', popup).val();
            if (key != '') {
                var value =  $('.textarea-format-value', popup).val();
                var parent = $('.select-format-parent', popup).val();
                if (parent == -1) parent = null;
                var thisBlock = this;
                Pipeline.ajax.saveGraphFormat(key, parent, value, function(data) {
                    if (data.error == false) {
                        $('.popupfilter', thisBlock.element).hide();
                        $('.popup', thisBlock.element).hide();
                        thisBlock.format = key;
                        thisBlock.loadState();
                        Pipeline.refresh();
                    }
                });
            }
        },

        popupDelete: function() {
            var popup = $('.popup', this.element);
            var thisBlock = this;
            var key = $('.text-format-key', popup).val();
            if ( key != '' ) {
                Pipeline.ajax.deleteGraphFormat(key, function(data) {
                    if ( data.error == false ) {
                        $('.popupfilter', thisBlock.element).hide();
                        $('.popup', thisBlock.element).hide();
                        thisBlock.format = -1;
                        thisBlock.loadState();
                        Pipeline.refresh();
                    }
                });
            }
        }
    }),

    /**
     * The value filter block allows certain filters to be specified that will
     * remove rows from the data.
     */
    ValueFilterBlock: Block.extend({
        /**
         ** Static fields
         **/

        /**
         * The ID of the template for this filter
         */
        TEMPLATE_ID: "#pipeline-valuefilter-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 5,

        /**
         * The type of filter
         */
        TYPE: {
            IS: 1,
            IS_NOT: 2
        },
        
        /**
         ** Object fields
         **/

        /**
         * The currently valid filters
         */
        filters: null,
        
        /**
         * The options table for selecting filters
         */
        optionsTable: null,
        
        /**
         ** Object methods
         **/

        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);
            this.filters = [{column: -1, is: 1, lowerbound: '-inf', upperbound: '+inf'}];
            
            // Create a closure to use as the callback for removing objects.
            // This way, the scope of this block is maintained.
            var thisBlock = this;
            var removeClosure = function(row) {
                thisBlock.removeFilter.call(thisBlock, row); 
            };
            var addClosure = function() {
                thisBlock.filters.push({column: -1, is: 1, lowerbound: '-inf', upperbound: '+inf'});
                thisBlock.loadState();
            };
            
            // Create the option table
            this.optionsTable = new OptionsTable($('.pipeline-valuefilter-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the dropdowns and text inputs
            $(this.element).delegate('select, input', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh();
            });
        },
        
        /**
        * Decode a parameter string and set this block's configuration according
        * to those parameters.
         */
        decode: function(params) {
            this.filters = [];
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // There must be at least two - a flagword and one filter
            if ( parts.length < 2 ) {
                console.debug("ValueFilter block invalid: not enough parts");
                return;
            }

            this.flags = parseInt(parts[0]);

            var filts = parts.slice(1);
            var thisBlock = this;
            jQuery.each(filts, function(i ,filter) {
                var settings = filter.split(Pipeline.encoder.PARAM_SEPARATOR);
                // Exactly four parts - column, is, lowerbound, upperbound
                if ( settings.length != 4 ) {
                    console.debug("ValueFilter invalid: not enough parts in ", filter);
                }
                thisBlock.filters.push({column: settings[0], is: settings[1], lowerbound: settings[2], upperbound: settings[3]});
            });
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = [this.flags];
            jQuery.each(this.filters, function(i, filter) {
                if ( filter.scenario != -1 ) {
                    strs.push(filter.column + Pipeline.encoder.PARAM_SEPARATOR
                              + filter.is + Pipeline.encoder.PARAM_SEPARATOR
                              + filter.lowerbound + Pipeline.encoder.PARAM_SEPARATOR
                              + filter.upperbound);
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
                var columnSelect = $('.select-valuefilter-column', this);
                var isSelect = $('.select-valuefilter-is', this);
                var lowerboundText = $('.text-valuefilter-lowerbound', this);
                var upperboundText = $('.text-valuefilter-upperbound', this);

                thisBlock.filters.push({
                    column: columnSelect.val(),
                    is: isSelect.val(),
                    lowerbound: lowerboundText.val(),
                    upperbound: upperboundText.val(),
                });
            });
        },

        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            var thisBlock = this;

            // Get rid of all but the first row
            this.optionsTable.reset();
            
            // Update the value columns
            $('.select-valuefilter-column', this.element).each(function() {
                Utilities.updateSelect(this, thisBlock.valueColumnsCache, thisBlock.valueColumnsCache, true);
            });

            // Create new rows for each filter
            var thisBlock = this;
            jQuery.each(this.filters, function(i, filter) {
                var row = thisBlock.optionsTable.addRow();
                var columnSelect = $('.select-valuefilter-column', row);
                var isSelect = $('.select-valuefilter-is', row);
                var lowerboundText = $('.text-valuefilter-lowerbound', row);
                var upperboundText = $('.text-valuefilter-upperbound', row);
                
                // Note here we assume the scenario dropdown has already been
                // updated, and the value cache is also up to date with new
                // logs.
                columnSelect.val(filter.column);
                isSelect.val(filter.is);
                lowerboundText.val(filter.lowerbound);
                upperboundText.val(filter.upperbound);
            });
        },
        
        refreshColumns: function() {
            var thisBlock = this;
            var changed = false;
            
            jQuery.each(this.filters, function(i, filter) {
                // If the selected scenario isn't in the new available ones,
                // reset this row
                if ( filter.column != -1 && jQuery.inArray(filter.column, thisBlock.valueColumnsCache) == -1 ) {
                    filter.column = -1;
                    changed = true;
                    return;
                }
            });
            
            return changed;
        },

        complete: function() {
            var valid = true;
            jQuery.each(this.filters, function(i, filter) {
                if ( filter.column == -1 ) {
                    valid = false;
                }
            });

            return valid;
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
            var column     = $('.select-valuefilter-column', row).val();
            var is         = $('.select-valuefilter-is', row).val();
            var lowerbound = $('.text-valuefilter-lowerbound', row).val();
            var upperbound = $('.text-valuefilter-upperbound', row).val();
            
            return {column: column, is: is, lowerbound: lowerbound, upperbound: upperbound};
        }
    }),

    /**
     * The composite scenario block allows the addition of scenario columns.
     */
    CompositeScenarioBlock: Block.extend({
        /**
         ** Static fields
         **/

        /**
         * The ID of the template for this filter
         */
        TEMPLATE_ID: "#pipeline-compositescenario-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 6,

        /**
         ** Object fields
         **/

        /**
         * The currently valid filters
         */
        columns: null,
        
        /**
         * The options table for selecting filters
         */
        optionsTable: null,
        
        /**
         ** Object methods
         **/

        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);
            this.columns = [-1];
            
            // Create a closure to use as the callback for removing objects.
            // This way, the scope of this block is maintained.
            var thisBlock = this;
            var removeClosure = function(row) {
                thisBlock.removeColumn.call(thisBlock, row); 
            };
            var addClosure = function() {
                thisBlock.columns.push(-1);
                thisBlock.loadState();
            };
            
            // Create the option table
            this.optionsTable = new OptionsTable($('.pipeline-compositescenario-table', this.element), removeClosure, Pipeline.refresh, addClosure);
            
            // Hook the dropdowns and text inputs
            $(this.element).delegate('select, input', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh();
            });
        },
        
        /**
        * Decode a parameter string and set this block's configuration according
        * to those parameters.
         */
        decode: function(params) {
            this.columns = [];
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // There must be at least two - a flagword and one filter
            if ( parts.length < 2 ) {
                console.debug("CompositeScenario block invalid: not enough parts");
                return;
            }

            this.flags = parseInt(parts[0]);

            var cols = parts.slice(1);
            var thisBlock = this;
            jQuery.each(cols, function(i, column) {
                var settings = column.split(Pipeline.encoder.PARAM_SEPARATOR);
                // Exactly four parts - column, is, lowerbound, upperbound
                if ( settings.length != 1 ) {
                    console.debug("CompositeScenario block invalid: incorrect number of parts in ", column);
                }
                thisBlock.columns.push(settings[0]);
            });
        },
        

        seed: function(scenarioCols, valueCols) {
            $('.scenario-column', this.element).each(function() {
                Utilities.updateSelect(this, scenarioCols, scenarioCols);
            });
            column = this.columns.join('-');
            scenarioCols.push(column);
        },

        /**
         * Encode this block into a parameter string based on its configuration.
         */

        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            var strs = [this.flags];
            jQuery.each(this.columns, function(i, column) {
                if ( column != -1) strs.push(column);
            });
            return strs.join(Pipeline.encoder.GROUP_SEPARATOR);
        },

        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
            this.columns = [];
            var thisBlock = this;
            $('tr', this.element).each(function() {
                var columnSelect = $('.select-compositescenario-column', this);

                thisBlock.columns.push(columnSelect.val());
            });
        },

        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            // Get rid of all but the first row
            this.optionsTable.reset();
            var thisBlock = this;
            
            // Update the scenario columns
            $('.select-compositescenario-column', this.element).each(function() {
                Utilities.updateSelect(this, thisBlock.scenarioColumnsCache, thisBlock.scenarioColumnsCache, true);
            });
            
            // Create new rows for each filter
            var thisBlock = this;
            jQuery.each(this.columns, function(i, column) {
                var row = thisBlock.optionsTable.addRow();
                var columnSelect = $('.select-compositescenario-column', row);
                
                // Note here we assume the scenario dropdown has already been
                // updated, and the value cache is also up to date with new
                // logs.
                columnSelect.val(column);
            });
        },
        
        refreshColumns: function() {
            var thisBlock = this;
            var changed = false;
            
            jQuery.each(this.columns, function(i, column) {
                // If the selected scenario isn't in the new available ones,
                // reset this row
                if ( column != -1 && jQuery.inArray(column, thisBlock.scenarioColumnsCache) == -1 ) {
                    thisBlock.columns[i] = -1;
                    changed = true;
                    return;
                }
            });

            return changed;
        },

        complete: function() {
            var valid = true;
            var thisBlock = this;

            jQuery.each(this.columns, function(i, column) {
                if (thisBlock.columns[i] == -1) {
                    valid = false;
                    return;
                }
            });

            return valid;
        },
        
        /**
         * A row is about to be removed from the OptionsTable. We need to
         * clean it up here.
         *
         * @param row Element The table row to be removed
         */
        removeColumn: function(row) {
            var value = $('.select-compositescenario-column', row).val();
            
            for ( var i = 0; i < this.columns.length; i++ ) {
                if ( this.columns[i] == value) {
                    this.columns.splice(i, 1);
                    break;
                }
            }
        },
    }),
    
    /**
     * The format block is used to add formatting information 
     */
    FormatBlock: Block.extend({
        /**
         ** Static fields
         **/

        /**
         * The ID of the template for this block
         */
        TEMPLATE_ID: "#pipeline-format-template",

        /**
         * The ID of this block for encoding (the inverse of the mapping in
         * Pipeline.encoder.MAPPINGS)
         */
        ID: 7,

        /**
         ** Object fields
         **/
        
        /**
         * The scenario column to format
         */
        column: -1,
        
        /**
         * The key of the configured formatting information to use.
         */
        key: -1,

        /**
         * The configured formatting information to use.
         */
        format: null,

        /**
         * The entries in the associated popup
         */
        popupEntryOptionsTable: null,

        /**
         ** Object methods
         **/
        
        /**
         * Creates a new block. See Block.constructor for parameters.
         */
        constructor: function(insertIndex) {
            this.base(insertIndex);
            
            var thisBlock = this;
            // Hook the load button for loading the format
            $("#pipeline-format-load-go", this.element).click(function() {
                var col = $('.select-format-column', thisBlock.element).val();
                var key = $('.select-format-key', thisBlock.element).eq(0).val();
                thisBlock.popupOpen(col, key);
            });
            $("#pipeline-format-new-go", this.element).click(function() {
                var col = $('.select-format-column', thisBlock.element).val();
                thisBlock.popupOpen(col, '-1');
            });

            // Hook up the popup
            var popup = $('.popup', this.element);
            $(".text-format-key", popup).change(function() {
                var oldVal = $(popup).data("initial_key");
                var newVal = $(".text-format-key", popup).val();
                if (oldVal == newVal) {
                    $('#popup-format-delete-go', popup).removeAttr("disabled");
                } else {
                    $('#popup-format-delete-go', popup).attr("disabled", "disabled");
                }
            });
            bindColorPicker($('.text-format-color', popup));
            $(".cancel-button", popup).click(function() {
                $('.popup', thisBlock.element).hide();
                $('.popupfilter', thisBlock.element).hide();

            });
            $(".check-group", popup).change(function() {
                if ($(".check-group", popup).attr("checked")) {
                    $('.text-format-group', popup).removeAttr('disabled');
                } else {
                    $('.text-format-group', popup).attr('disabled', 'disabled');
                }
            });
            $('.text-format-group', popup).attr('disabled', 'disabled');
            $(".check-color", popup).change(function() {
                if ($(".check-color", popup).attr("checked")) {
                    $('.text-format-color', popup).removeAttr('disabled');
                } else {
                    $('.text-format-color', popup).attr('disabled', 'disabled');
                }
            });
            $('.text-format-color', popup).attr('disabled', 'disabled');
            var addClosure = function(row) {
                $('.text-format-value', row).val('');
                $('.text-format-display', row).val('');
                $('.text-format-group', row).val('');
                bindColorPicker($('.text-format-color', row));
                $('.text-format-color', row).val('');
                $('.text-format-color', row).change();
            };
            this.popupEntryOptionsTable = new OptionsTable($('.popup-format-table', popup), null, null, addClosure); 
            $('#popup-format-save-go', popup).click(function() {
                thisBlock.popupSave();
            });
            $("#popup-format-delete-go", popup).click(function() {
                thisBlock.popupDelete();
            });


            // Hook the dropdowns
            $(this.element).delegate('select', 'change', function() {
                thisBlock.readState();
                Pipeline.refresh();
            });
        },
        
        /**
         * Decode a parameter string and set this block's configuration according
         * to those parameters.
         */
        decode: function(params) {
            var parts = params.split(Pipeline.encoder.GROUP_SEPARATOR);
            // Exactly 2 parts - flagword and settings
            if ( parts.length != 2 ) {
                console.debug("Format block invalid: incorrect number of parts");
                return;
            }

            this.flags = parseInt(parts[0]);

            var settings = parts[1].split(Pipeline.encoder.PARAM_SEPARATOR);
            if ( settings.length != 2 ) {
                console.debug("Format block invalid: incorrect number of settings");
                return;
            }
            this.column = settings[0];
            this.key = settings[1];
        },
        
        /**
         * Encode this block into a parameter string based on its configuration.
         */
        encode: function() {
            return this.flags + Pipeline.encoder.GROUP_SEPARATOR + this.column + Pipeline.encoder.PARAM_SEPARATOR + this.key;
        },

        /**
         * Take this block's HTML values and load them into local
         * configuration.
         */
        readState: function() {
            var scenarioSelect = $('.select-format-column', this.element);
            var keySelect = $('.select-format-key', this.element);
            
            this.column = scenarioSelect.val();
            this.key = keySelect.val();
        },
        
        /**
         * Take this block's local configuration and load it into the
         * HTML.
         */
        loadState: function() {
            // By the time this function is called, the scenario dropdown
            // should already have been updated with available scenario
            // columns
            var scenarioSelect = $('.select-format-column', this.element);
            var keySelect = $('.select-format-key', this.element);
            
            Utilities.updateSelect(scenarioSelect, this.scenarioColumnsCache, this.scenarioColumnsCache);
            Utilities.updateSelect(keySelect, Pipeline.formatStyleKeysCache, Pipeline.formatStyleKeysCache);

            scenarioSelect.val(this.column);
            keySelect.val(this.key);
        },
        
        refreshColumns: function() {
            if ( this.column != -1 && jQuery.inArray(this.column, this.scenarioColumnsCache) == -1 ) {
                this.column = -1;
                return true;
            }

            if ( this.key != -1 && jQuery.inArray(this.key, Pipeline.formatStyleKeysCache) == -1 ) {
                this.key = -1;
                return true;
            }

            return false;
        },

        complete: function() {
            return this.column != -1 && this.key != -1;
        },
        
        popupOpen: function(col, key) {
            var popup = $('.popup', this.element);
            popup.show();
            $('.popupfilter', this.element).show();

            key = (key == -1) ? "" : key;
            $(popup).data("initial_key", key);
            
            // Key dropdown and key field
            $('.text-format-key', popup).val(key);

            // Suggested values
            $('.format-suggestions', popup).text(col == -1 ? 'None (no column selected)' : this.scenarioValuesCache[col].join(' '));

            // Rows
            // Get rid of all but the first row
            this.popupEntryOptionsTable.reset();

            if (key == "") {
                $('#popup-format-delete-go', popup).hide();
                $('.text-format-color', popup).val('');
                $('.text-format-color', row).change();
            } else {
                $('#popup-format-delete-go', popup).show();
                $('#popup-format-delete-go', popup).removeAttr("disabled");

                // Need to load existing columns
                $('input', popup).attr('disabled', 'disabled');
                $(".check-color", popup).attr('checked', 'checked');
                $(".check-group", popup).attr('checked', 'checked');
                 
                var thisBlock = this;
                Pipeline.ajax.loadFormatStyle(key, function(data) {
                    if ( data.error == false ) {
                        var foundGroup = 0;
                        var foundColor = 0;
                        jQuery.each(data.styles, function(i, style) {
                            var row = thisBlock.popupEntryOptionsTable.addRow();
                            $('.text-format-value', row).val(style.value);
                            $('.text-format-display', row).val(style.display);
                            $('.text-format-group', row).val(style.group);
                            bindColorPicker($('.text-format-color', row));
                            $('.text-format-color', row).val(style.color);
                            $('.text-format-color', row).change();

                            if (style.group != null) {
                              foundGroup++;
                            }
                            if (style.color != null) {
                              foundColor++;
                            }
                        });
                        $('input', popup).removeAttr('disabled');
                        if (foundColor == 0) {
                            $('.text-format-color', popup).attr('disabled', 'disabled');
                            $(".check-color", popup).removeAttr('checked');
                        }
                        if (foundGroup == 0) {
                            $('.text-format-group', popup).attr('disabled', 'disabled');
                            $(".check-group", popup).removeAttr('checked');
                        }
                    } else {
                        $(".popup", thisBlock.element).hide();
                        $('.popupfilter', thisBlock.element).hide();
                    }
                });

            }
        },

        popupSave: function() {
            var popup = $('.popup', this.element);
            var table = $('.popup-format-table', popup);
            var styles = [];
            var useColor = $(".check-color", popup).attr("checked");
            var useGroup = $(".check-group", popup).attr("checked");
            var index = 0;
            $('tr', popup).not('.header').each(function(i, row) { 
                value = $.trim($('.text-format-value', row).val());
                display = $.trim($('.text-format-display', row).val());
                group = $.trim($('.text-format-group', row).val()); 
                color = $('.text-format-color', row).val();
                if (!useColor || color.length != 7) color = null;
                if (!useGroup || group.length == 0) group = null;
                if (value.length > 0 && display.length > 0 && (group == null || group.length > 0) && (color == null || color.length == 7)) {
                    var style = {'index': index, 'value': value, 'display': display, 'group': group, 'color': color};
                    var conflict = false;
                    for(otherstyle in styles) {
                       if (otherstyle.value == style.value) {
                           conflict = true;
                       }
                    }
                    if (!conflict) {
                        styles[index] = style;
                        index++;
                    }
                }
            });
            var key = $('.text-format-key', popup).val();
            if (key != '') {
                var thisBlock = this;
                Pipeline.ajax.saveFormatStyle(key, styles, function(data) {
                    if (data.error == false) {
                        $('.popupfilter', thisBlock.element).hide();
                        $('.popup', thisBlock.element).hide();
                        thisBlock.key = key;
                        thisBlock.loadState();
                        Pipeline.refresh();
                    }
                });
            }
        },

        popupDelete: function() {
            var popup = $('.popup', this.element);
            var thisBlock = this;
            var key = $('.text-format-key', popup).val();
            if ( key != '' ) {
                Pipeline.ajax.deleteFormatStyle(key, function(data) {
                    if ( data.error == false ) {
                        $('.popupfilter', thisBlock.element).hide();
                        $('.popup', thisBlock.element).hide();
                        thisBlock.key = '-1';
                        thisBlock.loadState();
                        Pipeline.refresh();
                    }
                });
            }
        }
    }),
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
        this.element.delegate(".add-row", "click", {table: this}, function(e) {
            e.data.table._addBlockTableRow.call(e.data.table);
        });
        this.element.delegate(".remove-row", "click", {table: this}, function(e) {
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
        $('tr', this.element).not('.header').not(':first').remove();
        this.numRows = 0;
    },

    /**
     * Create a new row and return it for use programatically
     * (as opposed to being created by the user clicking +)
     */
    addRow: function() {
        var row = $('tr', this.element).not('.header').eq(0);
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
        var rows = $('tr', this.element).not('.header');
        if ( rows.length > 1 ) {
            $('.remove-row', rows).removeAttr('disabled');
            $('.add-row', rows).hide();
        }
        else {
            $('.remove-row', rows).attr('disabled', 'disabled');
        }
        $('tr:last-child .add-row', this.element).show();
    },
    
    /**
     * Add a new row to a table of option rows
     */
    _addBlockTableRow: function() {
        var newRow = $('tr', this.element).not('.header').eq(0).clone();

        this.numRows += 1;

        this._clearSelects(newRow);

        this.element.append(newRow);

        this._updateAddRemoveButtons();

        if ( this.addCallback !== null ) {
            this.addCallback.call(this, newRow);
        }
    },
    
    /**
     * Remove a row from the table of option rows, as given by the button
     * that was clicked
     *
     * @param button Element The button that triggered the removal
     */
    _removeBlockTableRow: function(button) {
        var row = $(button).parents('tr').eq(0);
        
        if ( this.preRemoveCallback !== null ) {
            this.preRemoveCallback.call(this, row);
        }
        
        row.remove();
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
                Utilities.updateSelect(this, [], []);
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
     * True to enable debug link and output
     */
    DEBUG: false,

    /**
     * Some constants
     */
    constants: {        
        // Timeout after the last typing event in a derived value column
        // expression before the pipeline is refreshed
        DERIVED_VALUE_COLUMN_CHANGE_TIMEOUT: 1000, // ms

        // How many rows should a table contain before we don't render it
        // automatically?
        MAX_TABLE_ROWS_AUTO_RENDER: 200
    },

    /**
     * Possible flags; ORed onto Pipeline.flags
     */
    FLAGS: {
        NOTHING: 0 // not a real flag, just for demonstration
    },
    
    /**
     * Some special strings for pipeline encoding
     */
    encoder: {
        BLOCK_SEPARATOR: "|",
        GROUP_SEPARATOR: "&",
        PARAM_SEPARATOR: "^",
        TUPLE_SEPARATOR: ";",

        // Mappings from IDs to blocks (the inverse of the mappings inside each
        // block)
        MAPPINGS: {
            1: Blocks.FilterBlock,
            2: Blocks.AggregateBlock,
            3: Blocks.NormaliseBlock,
            4: Blocks.GraphBlock,
            5: Blocks.ValueFilterBlock,
            6: Blocks.CompositeScenarioBlock,
            7: Blocks.FormatBlock,
        }
    },
    
    /**
     * Caches the available scenario columns.
     */
    scenarioColumnsCache: {},
    
    /**
     * Caches the available values for scenario columns at the start of the pipeline.
     */
    scenarioValuesCache: {},
    
    /**
     * Caches the corresponding display values.
     */
    scenarioDisplayCache: {},

    /**
     * Caches the available value columnss;
     */
    valueColumnsCache: [],

    /**
     * Caches the available values for scenario columns at the end of the pipeline.
     */
    newBlockScenarioColumnsCache: {},
    
    /**
     * Caches the available values for scenario columns at the end of the pipeline.
     */
    newBlockScenarioValuesCache: {},
    
    /**
     * Caches the corresponding display values.
     */
    newBlockScenarioDisplayCache: {},

    /**
     * Caches the available value columnss;
     */
    newBlockValueColumnsCache: [],

    /**
     * The currently selected log files.
     */
    selectedLogFiles: [],

    /**
     * The curerntly selected scenario columns.
     */ 
    selectedScenarioColumns: [],

    /**
     * The curerntly selected value columns.
     */ 
    selectedValueColumns: [],

    /**
     * The curerntly defined derived value columns. 
     */ 
    derivedValueColumns: [],

    /**
     * Caches the keys of available formatting styles.
     */
    formatStyleKeysCache: [],
    
    /**
     * Caches the set of graph format keys
     */
    graphFormatKeysCache: [],

    /**
     * Caches the graph format configurations (including text for the ui)
     */
    graphFormatsCache: {},


    /**
     * The option table for log files
     */
    logFileOptionsTable: null,

    /**
     * The option table for derived value columns
     */
    derivedValueColsOptionsTable: null,
    
    /**
     * Blocks in the pipeline
     */
    blocks: [],
    
    /**
     * The current page hash, used to run hashchange events
     */
    hash: "",

    /**
     * Pipeline-global flags
     */
    flags: 0,

    /**
     * The timeout ID for the timeout used to decide when to try to load
     * a pipeline after a derived value column has been modified.
     */
    derivedValueColTimeoutID: -1,

    /**
     ** Public methods
     **/
    
    /**
     * Initialise things that need to be set up at runtime. This should be
     * called after the DOM is ready.
     */
    init: function() {
        // Add the debug link if needed
        if ( Pipeline.DEBUG ) {
            $('#pipeline-purgecache-go').after(' <button id="pipeline-debug-go" class="pipeline-button">Debug</button>');
            $('#pipeline-debug-go').click(function() {
                window.location.href = 'list/' + Pipeline.hash + '?debug';
            });
        }
        else {
            console.debug = function() { return; };
        }

        // Set up AJAX request options
        $.ajaxSetup({
            cache: false
        });
        $('#loading-indicator').ajaxStart(function() {
            $('#output .exception').remove();
            $(this).show();
        }).ajaxStop(function() {
            $(this).hide();
        }).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
            var html = '<div class="exception"><h1>AJAX error</h1>Error thrown: \
                     ' + thrownError + ' when loading URL <a href="' + ajaxSettings.url + '">\
                     ' + ajaxSettings.url + '</a>';
            // Try to get the python exception
            //html += '<br />Traceback:<pre>' + jqXHR.responseText.length + '</pre>';
            if ( Pipeline.DEBUG ) {
                var exceptionHTML = $(jqXHR.responseText);
                var exceptionTrace = exceptionHTML.find('#traceback_area');
                if ( exceptionTrace.length > 0 ) {
                    html += '<br />Traceback:<pre>' + exceptionTrace.val() + '</pre>';
                }
            }
            html += '</div>';
            $('#output').prepend(html);
        });
        
        // Create the options table for log files and derived value cols
        Pipeline.logFileOptionsTable = new OptionsTable($('#pipeline-log-table'), null, Pipeline.refresh);
        Pipeline.derivedValueColsOptionsTable = new OptionsTable($('#pipeline-derived-value-cols'), null, Pipeline.refresh, function() {
            $('.pipeline-derived-value-field', this).val("");
        });

        // Hook the log selection dropdowns
        $("#pipeline-log").delegate(".select-log", 'change', function() {
            Pipeline.selectedLogFiles = [];
            $('.select-log', Pipeline.logFileOptionsTable.element).each(function() {
                if ( $(this).val() != '-1' ) {
                    Pipeline.selectedLogFiles.push($(this).val());
                }
            });
            Pipeline.refresh();
        });
        
        // Turn the scenario and value column selects into multiselects
        $("#select-scenario-cols, #select-value-cols").toChecklist();
        
        // Hook the [all] links
        $("#select-scenario-cols-all").click(function() {
            if ( $('#select-scenario-cols input:checkbox').length == 0 ) return false;
            $('#select-scenario-cols input:checkbox').attr('checked', true);
            $('#select-scenario-cols li').addClass('checked');
            Pipeline.selectedScenarioColumns = Utilities.multiSelectValue($("#select-scenario-cols"));
            Pipeline.refresh();
            return false;
        });
        $('#select-scenario-cols-none').click(function() {
            if ( $('#select-scenario-cols input:checkbox').length == 0 ) return false;
            $('#select-scenario-cols input:checkbox').removeAttr('checked');
            $('#select-scenario-cols li').removeClass('checked');
            Pipeline.selectedScenarioColumns = [];
            Pipeline.refresh();
            return false;
        });

        // Hook the checkboxes in the scenario and value column selects
        $("#pipeline-scenario-cols").delegate("#select-scenario-cols input", 'change', function() {
            Pipeline.selectedScenarioColumns = Utilities.multiSelectValue($("#select-scenario-cols"));
            Pipeline.refresh();
        });
        $("#pipeline-value-cols").delegate("#select-value-cols input", 'change', function() {
            Pipeline.selectedValueColumns = Utilities.multiSelectValue($("#select-value-cols"));
            Pipeline.refresh();
        });
        
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
        $('#add-valuefilter').click(function() {
            Pipeline.createBlock(Blocks.ValueFilterBlock);
        });
        $('#add-compositescenario').click(function() {
            Pipeline.createBlock(Blocks.CompositeScenarioBlock);
        });
        $('#add-format').click(function() {
            Pipeline.createBlock(Blocks.FormatBlock);
        });

        // Hook the button for showing large tables
        $('#load-large-table').click(function() {
            Utilities.outputTableSort();
            $('#output table, #output .foldable.table').show();
            $('#output').css('paddingTop', '60px');
            $('#large-table-confirm').hide();
        });

        // Hook the foldable things
        $("#output").delegate('.foldable h1 button', 'click', function() {
            var foldable_content = $(this).parents('.foldable').eq(0).children('.foldable-content').eq(0);
            if ( foldable_content.hasClass('hidden') ) {
                foldable_content.removeClass('hidden');
                $(this).replaceWith('<button class="foldable-toggle-hide pipeline-button">Hide</button>');
            }
            else {
                foldable_content.addClass('hidden');
                $(this).replaceWith('<button class="foldable-toggle-show pipeline-button">Show</button>');
            }
            return false;
        });

        // Hook the hashchange event for history nav. Based on
        // http://www.bcherry.net/static/lib/js/jquery.pathchange.js
        var isSupported = "onhashchange" in window;
        if ( !isSupported && window.setAttribute ) {
            window.setAttribute("onhashchange", "return;");
            isSupported = ( typeof window.onhashchange === "function" );
        }
        $(window).bind("hashchange", Pipeline.hashChange);
        if ( !isSupported ) {
            var lastHash = window.location.hash;
            setInterval(function() {
                if ( lastHash !== window.location.hash ) {
                    $(window).trigger("hashchange");
                    lastHash = window.location.hash;
                }
            });
        }

        // Hook the save button and form for saving pipelines
        $("#pipeline-save-form").submit(function() {
            Pipeline.savePipeline();
            return false;
        });
        $('#pipeline-save-go').click(function() {
            Pipeline.savePipeline();
            return false;
        });

        // Hook the load button for loading pipelines
        $("#pipeline-load-go").click(function() {
            var selected = $('#pipeline-load-select').val();
            if ( selected != '-1' ) {
                Pipeline.pushState(selected, true);
            }
        });

        // Hook the create short URL button
        $("#pipeline-shorturl-go").click(function() {
            Pipeline.createShortURL();
            return false;
        });

        // Hook the load button for loading pipelines
        $("#pipeline-new-go").click(function() {
            window.location = ".";
        });

        // Hook the load button for loading pipelines
        $("#pipeline-purgecache-go").click(function() {
            Pipeline.purgeCache();
        });

        $("#pipeline-delete-go").click(function() {
            var select = $('#pipeline-load-select');
            if ( select.val() != '-1' ) {
                // Get the name
                var selectedOption = select.children(':selected');
                var name = selectedOption.html();
                Pipeline.ajax.deletePipeline(name, function(data) {
                    if ( data.error == false ) {
                        selectedOption.remove();
                        select.val('-1');
                    }
                });
            }
        });

        // Hook the onchange for derived value cols to start a timer to refresh
        // the pipeline
        $('#pipeline-derived-value-cols').delegate('.pipeline-derived-value-field', 'keyup', function() {
            clearTimeout(Pipeline.derivedValueColTimeoutID);
            Pipeline.derivedValueColTimeoutID = setTimeout(function() { 
                Pipeline.derivedValueColumns = [];
                $('.pipeline-derived-value-field').each(function() {
                    var s = $.trim(this.value);
                    if ( s.length > 0 ) Pipeline.derivedValueColumns.push(s);
                });
                Pipeline.refresh();
            }, Pipeline.constants.DERIVED_VALUE_COLUMN_CHANGE_TIMEOUT);
        });

        // Trigger it once now
        Pipeline.hashChange();
    },
    
    /**
     * Create a new fresh block and add it to the pipeline at the end.
     * TODO: Add blocks at any index.
     *
     * @param block Block The block class to instantiate
     * @param indexBlock Block The block to insert before
     */
    createBlock: function(block, indexBlock) {
        var index;
        var vc;
        var sc;
        var sd;
        var sv;
        if ( typeof indexBlock === 'undefined' ) {
            index = Pipeline.blocks.length;
            sc = Pipeline.newBlockScenarioColumnsCache;
            sv = Pipeline.newBlockScenarioValuesCache;
            sd = Pipeline.newBlockScenarioDisplayCache;
            vc = Pipeline.newBlockValueColumnsCache;
        }
        else {
            index = $(indexBlock).prevAll('.pipeline-block').length;
            sc = index == 0 ? Pipeline.scenarioColumnsCache : Pipeline.blocks[index-1].scenarioColumnsCache;
            sv = index == 0 ? Pipeline.scenarioValuesCache : Pipeline.blocks[index-1].scenarioValuesCache;
            sd = index == 0 ? Pipeline.scenarioDisplayCache : Pipeline.blocks[index-1].scenarioDisplayCache;
            vc = index == 0 ? Pipeline.valueColumnsCache : Pipeline.blocks[index-1].valueColumnsCache;
        }
        var b =  new block(index);
        b.scenarioColumnsCache = sc;
        b.scenarioValuesCache = sv;
        b.scenarioDisplayCache = sd;
        b.valueColumnsCache = vc;
        Pipeline.blocks.splice(index, 0, b);
        Pipeline.refresh();
    },
    
    /**
     * Remove a block from the pipeline.
     *
     * @param block Block The block to remove
     */
    removeBlock: function(block) {
        Pipeline.blocks.remove(block);
        block.removeBlock();
        Pipeline.refresh();
    },

    /**
     * Show the insert block buttons at the given index in the pipeline.
     *
     * @param block The block that triggered this; we should insert before it
     */
    showInsertButtons: function(block) {
        // Remove any existing ones
        $('#pipeline-insert').remove();
        // Clone the add block div, modify it slightly
        var addBlock = $("#pipeline-add").clone();
        addBlock.attr('id', 'pipeline-insert');
        addBlock.find('button').each(function() {
            $(this).unbind();
            $(this).attr('id', $(this).attr('id').replace("add-", "insert-"));
        });
        // XXX TODO no reason to duplicate this code vs the handlers for
        // the add buttons
        $('#insert-filter', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.FilterBlock, block);
        });
        $('#insert-aggregate', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.AggregateBlock, block);
        });
        $('#insert-normalise', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.NormaliseBlock, block);
        });
        $('#insert-graph', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.GraphBlock, block);
        });
        $('#insert-valuefilter', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.ValueFilterBlock, block);
        });
        $('#insert-compositescenario', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.CompositeScenarioBlock, block);
        });
        $('#insert-format', addBlock).click(function() {
            $(this).parents("#pipeline-insert").remove();
            Pipeline.createBlock(Blocks.FormatBlock, block);
        });
        addBlock.append('<div class="pipeline-footer"></div>');
        $('.pipeline-header', addBlock).html("<img src='static/brick_add.png'/> Insert Block");
        $('.pipeline-header-right', addBlock).html('<input type="image" class="remove-button" src="static/cross.png"/>');
        $('.remove-button', addBlock).click(function() {
            $(this).parents('#pipeline-insert').remove();
        });
        $(block).before(addBlock);
    },
    
    /**
     * Try to refresh the pipeline by cascading down the blocks and building
     * the encoded string.
     *
     * @param reason int The reason why this refresh was called. Value comes
     *   from Pipeline.constants.
     */
    refresh: function() {
        var encoded = [Pipeline.encodeHeader()];
        var error = false;
        // Reset any incomplete block styles
        $('.incomplete-block').removeClass('incomplete-block');
        if ( Pipeline.selectedLogFiles.length == 0 ) {
            console.debug("Pipeline not valid because no logs selected.");
            $('#pipeline-log').addClass('incomplete-block');
            return;
        }
        if ( Pipeline.selectedScenarioColumns.length == 0 ) {
            console.debug("Pipeline not valid because scenario cols empty.");
            error = true ;
            $('#pipeline-scenario-cols').addClass('incomplete-block');
        }
        if ( Pipeline.selectedValueColumns.length == 0 ) {
            console.debug("Pipeline not valid because value cols empty.");
            error = true ;
            $('#pipeline-value-cols').addClass('incomplete-block');
        }
        jQuery.each(Pipeline.blocks, function(i, block) {
            block.errorBeforeBlock = error;
            if (error) {
                //$('.select', block.element).attr("disabled","disabled");
            } else { 
                //$('.select', block.element).removeAttr("disabled");
                if (block.complete()) {
                    if (!error) encoded.push(block.ID + block.encode());
                } else {
                    error = true;
                    $(block.element).addClass('incomplete-block');
                }
            }
        });
        var hash = encoded.join(Pipeline.encoder.BLOCK_SEPARATOR);
        if (error) {
            console.debug("Pipeline.refresh: Pipeline not valid.");
            // Disable the save pipeline fields
            $('#pipeline-save-name, #pipeline-save-go').attr('disabled', 'disabled');
        } else {
            console.debug("Pipeline.refresh: Pipeline valid: " + encoded);
            // Push the new state onto the history stack
            Pipeline.pushState(hash);
            $('#pipeline-save-name, #pipeline-save-go').removeAttr('disabled');
        }

        Pipeline.ajax.pipeline(hash, function(data) {
            if ( data.tabulating === true ) {
                // Data is still being tabulated - show a progress indicator,
                // then bail.
                Pipeline.tabulating(data, function() {
                    Pipeline.refresh();
                });
                return;
            }

            if (!(data.block_scenarios === undefined)) {
                Pipeline.scenarioColumnsCache = Utilities.keys(data.block_scenarios[0]);
                Pipeline.scenarioValuesCache = data.block_scenarios[0];
                Pipeline.scenarioDisplayCache = data.block_scenario_display[0];
                Pipeline.valueColumnsCache = data.block_values[0];
                Pipeline.formatStyleKeysCache = data.format_styles;
                Pipeline.graphFormatKeysCache = Utilities.keys(data.graph_formats);
                Pipeline.graphFormatsCache = data.graph_formats;

                var changed = false;
                jQuery.each(Pipeline.blocks, function(i, block) {
                    if (i+1 >= data.block_scenarios.length) return;
                    Pipeline.blocks[i].scenarioColumnsCache = Utilities.keys(data.block_scenarios[i+1]);
                    Pipeline.blocks[i].scenarioValuesCache = data.block_scenarios[i+1];
                    Pipeline.blocks[i].scenarioDisplayCache = data.block_scenario_display[i+1];
                    Pipeline.blocks[i].valueColumnsCache = data.block_values[i+1];

                    if (!block.errorBeforeBlock) {
                        changed |= Pipeline.blocks[i].refreshColumns();
                        Pipeline.blocks[i].loadState();
                    }
                });

                if (changed) {
                    Pipeline.refresh();
                    return;
                }

                var scenarioDisplay = jQuery.map(Pipeline.scenarioColumnsCache, function(col) {
                    var colvals = Pipeline.scenarioValuesCache[col];
                    var numvals = colvals.length;
                    return '<b>' + col + '</b> (' + numvals + ') <font size="-2">[' + colvals.join(', ') + ']</font>';
                });

                Utilities.updateMultiSelect($("#select-scenario-cols"), scenarioDisplay, Pipeline.scenarioColumnsCache, Pipeline.selectedScenarioColumns);
                Utilities.updateMultiSelect($("#select-value-cols"), Pipeline.valueColumnsCache, Pipeline.valueColumnsCache, Pipeline.selectedValueColumns);
            }

            if (!error) {
                var output = $('#output');
                output.children().not('#loading-indicator').remove();
                output.hide();
                output.append(data.error_html);
                output.append('<table width="100%" class="graph-table"></table>');
                var graphs = $('.graph-table', output);

                var graphCount = 0;
                jQuery.each(data.graphs, function(i, gb) { jQuery.each(gb, function(i, g) { graphCount++; }); });
                var perRow = graphCount > 4 ? 3 : (graphCount > 1 ? 2 : 1);
                var row_count = 0;
                var row_html = '';

                jQuery.each(data.graphs, function(i, gb) {
                    jQuery.each(gb, function(i, g) {
                        //'title': title, 'hash': graph_hash, 'table': table_html, 'output': plot_output, 'suffixes
                        // svg
                        var html = '<img width="100%" src="graph/' + g.hash + '.svg"/>';
                        // links
                        html += '<p>' + jQuery.map(g.suffixes, function(s) {
                            return '<a href="graph/' + g.hash + '.' + s + '">' + s + '</a>';
                        }).join("\n") + '</p>';
                        // error
                        if (g.output != "") html += '<pre>' + g.output + '</pre>';
                        // table
                        html += Utilities.makeFoldable('Data', g.table, false);
                        row_html += '<td width=' + Math.floor(100*(1/perRow)) + '%>' + Utilities.makeFoldable(g.title, html, true) + '</td>';
                        if (++row_count == perRow) {
                            graphs.append('<tr>' + row_html + '</tr>');
                            row_html = '';
                            row_count = 0;
                        }
                    });
                });
                 
                output.append(Utilities.makeFoldable('Table', data.table_html, graphCount > 0));
                output.append(data.warn_html);
                if ( data.rows > Pipeline.constants.MAX_TABLE_ROWS_AUTO_RENDER && !data.graph) {
                    $('#output table, #output .foldable.table').hide();
                    $('#large-table-confirm span').html(data.rows);
                    $('#large-table-confirm').show();
                    output.css('paddingTop', '6em');
                }
                else {
                    $('#large-table-confirm').hide();
                    output.css('paddingTop', '60px');
                    Utilities.outputTableSort();
                }
                output.show();
    
                $('.error-block').removeClass('error-block');
                $('.ambiguous-block').removeClass('ambiguous-block');
                if ( data.error === true ) {
                    if ( data.index === 'selected log files' ) {
                        $('#pipeline-log').addClass('error-block');
                    }
                    else if ( typeof data.index === 'number' ) {
                        $('#pipeline .pipeline-block').eq(data.index).addClass('error-block');
                    }
                } else if ( data.ambiguity === true ) {
                    if ( data.index === 'selected data' ) {
                        $('#pipeline-log').addClass('ambiguity-block');
                    }
                    else if ( typeof data.index === 'number' ) {
                        $('#pipeline .pipeline-block').eq(data.index).addClass('ambiguous-block');
                    }
                } else {
                    Pipeline.newBlockScenarioColumnsCache = Utilities.keys(data.block_scenarios[Pipeline.blocks.length+1]);
                    Pipeline.newBlockScenarioValuesCache = data.block_scenarios[Pipeline.blocks.length+1];
                    Pipeline.newBlockScenarioDisplayCache = data.block_scenario_display[Pipeline.blocks.length+1];
                    Pipeline.newBlockValueColumnsCache = data.block_values[Pipeline.blocks.length+1];
                }
            } 
        });
    },

    /**
     * Data was recieved that says a log file is being tabulated. Track its
     * progress and call the callback when done.
     *
     * @param data dict The data dictionary returned from the tabulation start
     * @param callback function() The callback to fire once the tabulation is
     *   done.
     */
    tabulating: function(data, callback) {
        var progressDiv = $('#tabulate-progress');
        var progressName = $('.tabulate-logfile', progressDiv);
        var progressPercent = $('.tabulate-percent', progressDiv);
        var maxBGWidth = $('#output').width();
        var pid = data.pid;
        progressName.html(data.log);
        progressPercent.html("0");
        progressDiv.css('backgroundSize', '0px');
        progressDiv.show();
        var timerID;
        timerID = setInterval(function() {
            Pipeline.ajax.tabulateProgress(pid, function(data, textStatus, xhr) {
                if ( data.complete === true ) {
                    clearTimeout(timerID);
                    progressDiv.hide();
                    callback();
                }
                else {
                    progressPercent.html(data.percent);
                    progressDiv.css('backgroundSize', (data.percent * maxBGWidth / 100) + 'px');
                }
            });
        }, 1000);
    },

    /**
     * The hash has changed. Read it, check it, and do something about it.
     */
    hashChange: function() {
        var hash = window.location.hash;
        if ( hash[0] == "#" ) {
            hash = hash.substr(1);
        }
        console.debug("Hashchange: window.location.hash = " + hash + ", Pipeline.hash = " + Pipeline.hash);
        if ( hash == Pipeline.hash ) {
            console.debug("Hashchange: false alarm");
            return;
        }
        Pipeline.decode(hash);
        Pipeline.hash = hash;
    },
    
    /**
     * Push a new pipeline onto the history stack
     *
     * @param encoded string The encoded pipeline to push
     */
    pushState: function(encoded, forceRefresh) {
        console.debug("pushState: " + encoded + (typeof forceRefresh !== 'undefined' ? " (FORCE)" : ""));
        if ( typeof forceRefresh === 'undefined' ) {
            Pipeline.hash = encoded;
        }
        // Reset the short URL field
        $('#pipeline-shorturl-text').hide();
        $('#pipeline-shorturl-go').show();
        window.location.hash = encoded;
    },

    /**
     * Encode the header of the pipeline.
     */
    encodeHeader: function() {
        var strs = [];

        /*
         * part 1: flagword
         */
        strs.push(Pipeline.flags);

        /*
         * part 2: pipeline config
         */
        var pipelineConfig = [];

        // Encode the selected log files.
        pipelineConfig.push(Pipeline.selectedLogFiles.join(Pipeline.encoder.PARAM_SEPARATOR));
        pipelineConfig.push(Pipeline.selectedScenarioColumns.join(Pipeline.encoder.PARAM_SEPARATOR));
        pipelineConfig.push(Pipeline.selectedValueColumns.join(Pipeline.encoder.PARAM_SEPARATOR));
        pipelineConfig.push(Pipeline.derivedValueColumns.join(Pipeline.encoder.PARAM_SEPARATOR));
        strs.push(pipelineConfig.join(Pipeline.encoder.GROUP_SEPARATOR));

        return strs.join(Pipeline.encoder.BLOCK_SEPARATOR);
    },


    /**
     * Load a pipeline from an encoded string.
     *
     * @param encoded String The encoded pipeline string to parse.
     */
    decode: function(encoded) {
        // Try to convert old ones to new ones. No guarantees!
        // If the first character isn't a number, it is certainly not a new
        // pipeline. The converse is not true however, since logfiles may
        // start with a number (though that's unlikely, I think?). That is,
        // this code may *miss* an old pipeline, but will never mistakenly catch
        // a *new* pipeline.
        if ( !/[0-9]/.test(encoded[0]) ) {
            alert("Detected an old pipeline string. We'll try to convert, \
                  but no guarantees!\n\nYou should re-save the pipeline when \
                  it loads again.".replace(/[ ]+/g, " "));
            var newStyle = Pipeline.decodeOldStyle(encoded);
            Pipeline.pushState(newStyle);
            return;            
        }


        /*
         flagword | pipeline-config | block1 | ... | blockn
         flagword: an integer, default 0
         pipeline-config:   log1 ^ log2 ^ log3
                          & scenario1 ^ scenario2 ^ scenario3
                          & value1 ^ value2 ^ value3
                          & derivedVal1 ^ derivedVal2 ^ derivedVal3
         block: n[block specific]  -- n a single char identifier for the block
                (currently 1,2,3,4), which we'll split off here)
        */

        /*
         * Get the top-level parts of the encoded string
         */

        var parts = unescape(encoded).split(Pipeline.encoder.BLOCK_SEPARATOR);
        // Flagword and pipeline-config are required
        if ( parts.length < 2 ) {
            console.debug("Decode invalid because not enough parts");
            return;
        }

        var blocks = parts.slice(2); // everything from index 2 onwards

        /*
         * Set the pipeline config
         */

        Pipeline.setFlags(parts[0]);

        var pipelineConfig = parts[1].split(Pipeline.encoder.GROUP_SEPARATOR);
        // All parts required - logs, scenarios, values, derivedVals (may be empty)
        if ( pipelineConfig.length != 4 ) {
            console.debug("Decode invalid because not enough pipeline-config parts");
            return;
        }

        /*
         * Reset the pipeline
         */
        
        var logFiles = pipelineConfig[0].split(Pipeline.encoder.PARAM_SEPARATOR);
        var scenarioCols = pipelineConfig[1].split(Pipeline.encoder.PARAM_SEPARATOR);
        var valueCols = pipelineConfig[2].split(Pipeline.encoder.PARAM_SEPARATOR);
        var derivedValueCols = pipelineConfig[3].split(Pipeline.encoder.PARAM_SEPARATOR);
        // Remove whitespace-only columns from derivedValueCols
        Pipeline.derivedValueColsOptionsTable.reset();
        derivedValueCols = jQuery.map(derivedValueCols, function(val) {
            var s = $.trim(val);
            if ( s.length > 0 ) return s;
            else return null; // removes the item
        });

        Pipeline.selectedLogFiles = logFiles;
        Pipeline.selectedValueColumns = valueCols;
        Pipeline.selectedScenarioColumns = scenarioCols;
        Pipeline.derivedValueColumns = derivedValueCols;

        // Load the log files into the table
        Pipeline.logFileOptionsTable.reset();
        jQuery.each(logFiles, function(i, log) {
            var row = Pipeline.logFileOptionsTable.addRow();
            $('.select-log', row).val(log);
        });

        // Update the derived value cols
        jQuery.each(derivedValueCols, function(index, value) {
            var row = Pipeline.derivedValueColsOptionsTable.addRow();
            $('.pipeline-derived-value-field', row).val(value);
        });


        // Remove any old vlocks
        jQuery.each(Pipeline.blocks, function(i, block) {
            block.removeBlock();
        });

        Pipeline.blocks = [];

        // Start creating blocks
        jQuery.each(blocks, function(i, params) {
            if ( $.trim(params).length == 0 ) return;
            var paramString = params.slice(1); // The first character is the block ID
            var block = new Pipeline.encoder.MAPPINGS[params[0]](Pipeline.blocks.length);
            block.decode(paramString);
            Pipeline.blocks.push(block);
        });

        Pipeline.refresh();
    },

    /**
     * Attempt to decode an old-style URL and turn it into a new-style one.
     * Heavily untested - could be disastrous!
     */
    decodeOldStyle: function(encoded) {
        // Old format: log1&log2|scenario1&scenario2|value1&value2|derived1&derived2|block1|...|blockn
        var parts = unescape(encoded).split(Pipeline.encoder.BLOCK_SEPARATOR);

        var logFiles = parts[0].split(Pipeline.encoder.GROUP_SEPARATOR);
        var scenarioCols = parts[1].split(Pipeline.encoder.GROUP_SEPARATOR);
        var valueCols = parts[2].split(Pipeline.encoder.GROUP_SEPARATOR);
        var derivedValueCols = parts[3].split(Pipeline.encoder.GROUP_SEPARATOR);
        derivedValueCols = jQuery.map(derivedValueCols, function(val) {
            var s = $.trim(val);
            if ( s.length > 0 ) return s;
            else return null; // removes the item
        });
        var blocks = parts.slice(4);

        var blockStrs = [];

        jQuery.each(blocks, function(i, block) {
            if ( block[0] == '1' ) {
                // Filter block, mostly the same
                blockStrs.push("10&" + block.slice(1));
            }
            else if ( block[0] == '2' ) {
                // Aggregate block, different separator
                var bits = block.slice(1).split(Pipeline.encoder.GROUP_SEPARATOR);
                blockStrs.push("20&" + bits[0] + "^" + bits[1]);
            }
            else if ( block[0] == '3' ) {
                // Normalise block, very different!
                var bits = block.slice(1).split(Pipeline.encoder.GROUP_SEPARATOR);
                var type = bits[0];
                var normalisers = [];
                var groups = [];
                if ( type == '1' ) {
                    for ( var i = 1; i < bits.length; i++ ) {
                        if ( bits[i].indexOf(Pipeline.encoder.PARAM_SEPARATOR) > -1 ) {
                            normalisers.push(bits[i].replace('^', ';'));
                        }
                        else {
                            groups.push(bits[i]);
                        }
                    }
                    blockStrs.push("30&1&" + groups.join('^') + "&" + normalisers.join("^"));
                }
                else {
                    groups = parts.slice(1);
                    blockStrs.push("30&2&" + groups.join('^'));
                }
            }
            else if ( block[0] == '4' ) {
                // Graph block, nearly the same
                var parts = block.slice(1).split(Pipeline.encoder.GROUP_SEPARATOR);
                var type = parts[0][0];
                var errorbars = '1';
                if ( parts[0].length > 1 && parts[0][1] == '0') {
                    errorbars = '0';
                }
                blockStrs.push("4" + errorbars + "&" + type + "&" + parts.slice(1).join("^"));
            }
        });

        var pipelineConfig = [];
        pipelineConfig.push(logFiles.join(Pipeline.encoder.PARAM_SEPARATOR));
        pipelineConfig.push(scenarioCols.join(Pipeline.encoder.PARAM_SEPARATOR));
        pipelineConfig.push(valueCols.join(Pipeline.encoder.PARAM_SEPARATOR));
        pipelineConfig.push(derivedValueCols.join(Pipeline.encoder.PARAM_SEPARATOR));

        var newParts = [0, pipelineConfig.join(Pipeline.encoder.GROUP_SEPARATOR), blockStrs.join(Pipeline.encoder.BLOCK_SEPARATOR)];
        var newEncoded = newParts.join(Pipeline.encoder.BLOCK_SEPARATOR);
        console.debug("Old encoded: ", encoded);
        console.debug("New encoded: ", newEncoded);

        return newEncoded;
    },

    /**
     * Update the available scenario and value columns.
     *
     * @param scenarioCols Array The available scenario columns
     * @param valueCols Array The available value columns
     */
    updateAvailableColumns: function(scenarioCols, valueCols, selectedScenarioCols, selectedValueCols) {
        var scenarioDisplay = jQuery.map(scenarioCols, function(col) {
           var colvals = Pipeline.scenarioValuesCache[col];
           var numvals = colvals.length;
           return '<b>' + col + '</b> (' + numvals + ') <font size="-2">[' + colvals.join(', ') + ']</font>';
        });

        Utilities.updateMultiSelect($("#select-scenario-cols"), scenarioDisplay, scenarioCols, selectedScenarioCols);
        Utilities.updateMultiSelect($("#select-value-cols"), valueCols, valueCols, selectedValueCols);
    },

    /**
     * Purge the cache on the server. Also resets the pipeline
     */
    purgeCache: function() {
        Pipeline.ajax.purgeCache(function(data, textStatus, xhr) {
            Pipeline.refresh();
        });
    },

    /**
     * Save this pipeline to the server.
     */
    savePipeline: function() {
        var name = $('#pipeline-save-name').val();
        var encoded = Pipeline.hash;
        if ( name == '' ) {
            return false;
        }
        Pipeline.ajax.savePipeline(name, encoded, function(data, textStatus, xhr) {
            if ( data.error == false ) {
                console.debug("Saved pipeline: " + name + " = " + encoded);
                var loadDropdown = $("#pipeline-load-select");
                loadDropdown.get(0).options.add(new Option(name, encoded));
                loadDropdown.val(encoded);
                $('#pipeline-save-name').val('');
            }
        });
    },

    /**
     * Create a short URL for this pipeline.
     */
    createShortURL: function() {
        var encoded = Pipeline.hash;
        if ( encoded == '' ) {
            return;
        }
        Pipeline.ajax.createShortURL(encoded, function(data, textStatus, xhr) {
            if ( data.error === false ) {
                var textField = $("#pipeline-shorturl-text");
                textField.val(data.url);
                $("#pipeline-shorturl-go").hide();
                textField.show();
                textField.get(0).focus();
                textField.select();
            }
        });
    },

    /**
     * Set the flagword. This should also update the UI state according to
     * the flags.
     */
    setFlags: function(flags) {
        Pipeline.flags = parseInt(flags);
        // Update the UI
    },

    /**
     * Set a flag according to a boolean.
     */
    setFlag: function(flag, on) {
        if ( (flag & (flag - 1)) != 0 ) return; // not a power of two
        if ( on ) {
            Pipeline.flags |= flag;
        }
        else {
            Pipeline.flags &= ~flag;
        }
    },

    /**
     * Read a flag and return a boolean representing its state. We need this
     * because (0 & 1) != false and so will turn checkboxes on.
     *
     * @param flag the flag to read
     * @return boolean true if the flag is on, false if off
     */
    getFlag: function(flag) {
        return (Pipeline.flags & flag) == 0;
    },

    /**
     * Ajax requests.
     */
    ajax: {
        /**
         * ajax/log-values/<logs>/ returns information about the columns in the
         * specified logfiles
         */
        logValues: function(callback) {
            $.getJSON('ajax/log-values/' + Pipeline.selectedLogFiles.join(',') + '/', callback);
        },

        /**
         * ajax/pipeline/<pipeline> delivers the results of executing a
         * pipeline
         */
        pipeline: function(encoded, callback) {
            $.getJSON('ajax/pipeline/' + encoded, callback);
        },

        /**
         * ajax/save-pipeline/ saved a pipeline to the server given a name and
         * the encoded hash
         *
         * @param name string The name of the new pipeline
         * @param encoded string The encoded verison of the new pipeline
         */
        savePipeline: function(name, encoded, callback) {
            $.post('ajax/save-pipeline/', {'name': name, 'encoded': encoded}, callback, 'json');
        },

        /**
         * ajax/create-shorturl/<pipeline> creates a short url for the given
         * pipeline string
         */
        createShortURL: function(encoded, callback) {
            $.post('ajax/create-shorturl/', {'encoded': encoded}, callback, 'json');
        },

        saveFormatStyle: function(key, items, callback) {
            var itemString = JSON.stringify(items);
            $.post('ajax/save-formatstyle/' + key + '/', {'style': itemString}, callback, 'json');
        },

        loadFormatStyle: function(key, callback) {
            $.getJSON('ajax/load-formatstyle/' + key + '/', callback);
        },

        deleteFormatStyle: function(key, callback) {
            $.getJSON('ajax/delete-formatstyle/' + key + '/', callback);
        },

        saveGraphFormat: function(key, parent, value, callback) {
            data = parent != null ? {'parent': parent, 'value': value} : {'value': value};
            $.post('ajax/save-graphformat/' + key + '/', data, callback, 'json');
        },

        deleteGraphFormat: function(key, callback) {
            $.getJSON('ajax/delete-graphformat/' + key + '/', callback);
        },


        /**
         * ajax/save-pipeline/ deletes a pipeline on the server given a name
         *
         * @param name string The name of the pipeline to delete
         */
        deletePipeline: function(name, callback) {
            $.post('ajax/delete-pipeline/', {'name': name}, callback, 'json');
        },

        /**
         * ajax/purge-cache/ purge cache files on the server
         *
         */
        purgeCache: function(callback) {
            $.post('ajax/purge-cache/', {}, callback, 'json');
        },

        /**
         * ajax/tabulate-progress/<pid>/ checks the process of tabulating from
         * a given process id
         */
        tabulateProgress: function(pid, callback) {
            $.ajax({
                url: 'ajax/tabulate-progress/' + pid + '/',
                dataType: 'json',
                global: false,
                success: callback
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
        $('.select-log', Pipeline.logFileOptionsTable.element).each(function() {
            if ( $(this).val() != '-1' ) {
                logs.push($(this).val());
            }
        });
        return logs;
    }
}

Pipeline.DEBUG = ( typeof django_debug !== 'undefined' && django_debug );

$(document).ready(Pipeline.init);


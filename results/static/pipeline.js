function addBlock(type) {
	newBlock = $('#pipeline-' + type + '-template').clone();
	newBlock.attr('id', '');
	
	// do some replaces on the contents...
	
	newBlock.insertBefore('#pipeline-add');
}

function updateAddRemoveButtons(selector) {
    rows = $(selector + ' tr');
    if ( rows.length > 1 ) {
        rows.each(function(i) {
            $('.remove-row', this).attr('disabled', '');
            $('.add-row', this).css('display', 'none');
        });
    }
    $(selector + ' tr:last-child .add-row').css('display', 'block');
}

function addLog() {
    newRow = $('#pipeline-log-table tr:first-child').clone();
    
    $('select', newRow).get(0).selectedIndex = 0;
    
    $('#pipeline-log-table').append(newRow);
    
    updateAddRemoveButtons('#pipeline-log-table');
}

$(document).ready(function() {
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
	});
});
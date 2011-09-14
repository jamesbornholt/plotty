var bindColorPicker;
 
$(document).ready(function() {


  var preInput = ''; // for communicating between event handlers
  var paletteHTML = generateHTML(); //cached array of fully printed html for the palettes

  function fetchPalette() {

    var palettes = new Array();

    palettes[0] = [
              ["e3e3e7","e5e5e6","ecdfec","e6dfec","dfdfe6","dfe6e6","dfe6df","e8e8e0","f9f2df","f4e9df","ecdfdf","e5e4e2"],
              ["c7c7cf","cacbcd","d9bfd9","ccbfd9","bfbfcc","bfcccc","bfccbf","d1d1c0","f2e6bf","e9d4bf","d9bfbf","ccc8c5"],
              ["ababb7","b0b1b4","c69fc6","b39fc6","9f9fb3","9fb3b3","9fb39f","babaa1","ecd99f","ddbe9f","c69f9f","b2ada7"],
              ["8f8f9f","96979b","b380b3","9980b3","808099","809999","809980","a4a481","e6cc80","d2a980","b38080","99928a"],
              ["727287","7b7d81","9f609f","80609f","606080","608080","608060","8d8d62","dfbf60","c79360","9f6060","7f766d"],
              ["56566f","616368","8c408c","66408c","404066","406666","406640","767642","d9b340","bc7d40","8c4040","655b50"],
              ["3a3a57","46494f","792079","4d2079","20204d","204d4d","204d20","5f5f23","d2a620","b06820","792020","4c3f32"],
              ["1e1e3f","2c2f36","660066","330066","000033","003333","003300","484803","cc9900","a55200","660000","322415"]
            ];

    palettes[1] = [
              ["f2dfec","ece6f2","dfdff2","e6ecf9","dfecec","e6ece6","f2f2df","fff9df","fceddf","f2dfdf","ece6df","ffffff"],
              ["e6bfd9","d9cce6","bfbfe6","ccd9f2","bfd9d9","ccd9cc","e6e6bf","fff2bf","f8dabf","e6bfbf","d9ccbf","d8d8d8"],
              ["d99fc6","c6b3d9","9f9fd9","b3c6ec","9fc6c6","b3c6b3","d9d99f","ffec9f","f5c89f","d99f9f","c6b39f","b6b6b6"],
              ["cc80b3","b399cc","8080cc","99b3e6","80b3b3","99b399","cccc80","ffe680","f2b580","cc8080","b39980","929292"],
              ["bf609f","9f80bf","6060bf","809fdf","609f9f","809f80","bfbf60","ffdf60","eea360","bf6060","9f8060","6d6d6d"],
              ["b3408c","8c66b3","4040b3","668cd9","408c8c","668c66","b3b340","ffd940","eb9040","b34040","8c6640","494949"],
              ["a62079","794da6","2020a6","4d79d2","207979","4d794d","a6a620","ffd220","e77e20","a62020","794d20","242424"],
              ["990066","663399","000099","3366CC","006666","336633","999900","FFCC00","E46B00","990000","663300","000000"]
            ];
                
    palettes[2] = [
              ["fbdbee","ffdfff","f2dfff","ecdfff","dfdff9","e6ecff","dff2f2","dff2df","f2f9df","ffffdf","ffecdf","ffdfdf"],
              ["ffbfe6","ffbfff","e6bfff","d9bfff","bfbff2","ccd9ff","bfe6e6","bfe6bf","e6f2bf","ffffbf","ffd9bf","ffbfbf"],
              ["ff9fd9","ff9fff","d99fff","c69fff","9f9fec","b3c6ff","9fd9d9","9fd99f","d9ec9f","ffff9f","ffc69f","ff9f9f"],
              ["ff80cc","ff80ff","cc80ff","b380ff","8080e6","99b3ff","80cccc","80cc80","cce680","ffff80","ffb380","ff8080"],
              ["ff60bf","ff60ff","bf60ff","9f60ff","6060df","809fff","60bfbf","60bf60","bfdf60","ffff60","ff9f60","ff6060"],
              ["ff40b3","ff40ff","b340ff","8c40ff","4040d9","668cff","40b3b3","40b340","b3d940","ffff40","ff8c40","ff4040"],
              ["ff20a6","ff20ff","a620ff","7920ff","2020d2","4d79ff","20a6a6","20a620","a6d220","ffff20","ff7920","ff2020"],
              ["ff0099","ff00ff","9900ff","6600ff","0000cc","3366ff","009999","009900","99cc00","ffff00","ff6600","ff0000"]
             ];

    return palettes;
  }

  function generateHTML() {

    var palettes = fetchPalette();
    var html = new Array();

    for (palette=0; palette < palettes.length; palette++) {
      html[palette] = '<div class="kolorpicker-palette">\
             <ul class="palette-select">\
              <li>dark</li>\
              <li>neutral</li>\
              <li>bright</li>\
             </ul>\
            </div>\
            <div class="x-close-box">X</div>\
            <table id="palette-table" style="border-collapse: seperate;padding: 0px;margin:0; width: 290px;">';

      for (row=0; row < palettes[palette].length; row++) {
        html[palette] += '<tr>';
        for (col=0; col < palettes[palette][row].length; col++) {
          html[palette] += "<td class='tile' style='font-size:12px;padding:0;margin:0;border:1px solid #333333;cursor:pointer;background:#"+palettes[palette][row][col]+"' id='"+palettes[palette][row][col]+"'>&nbsp;</td>";
        }
        html[palette] += '</tr>';
      }

      html[palette] += '</tbody></table>';
    }

   return html;
  }

  function bindPicker(input) {
    $(input).data('selection', 1);
    $(input).wrap('<div class="kolorPicker-wrapper" />');
    $(input).click(function() {
      showPicker(this);
    });

    $(input).change(function () {
      var val = $(this).val();
      if (val != "") {
        var oldVal = val;
        val = val.toLowerCase(); 
        val = val.replace(/[^0-9a-f]/g,'');
        if (val.charAt(0) != '#') {
          val = '#' + val;
        }
        if (val.length > 7) {
          val = val.substring(0,7);
        }
        if (val != oldVal) {
          $(this).val(val);
        }
      }
      if (val.length < 7) {
        val = "#ffffff";
      }
      valCode = parseInt(val.substring(1,3), 16) + parseInt(val.substring(3,5), 16) + parseInt(val.substring(5,7), 16);
      $(this).css("background", val);
      $(this).css("color", valCode > 400 ? '#000000' : '#ffffff' );
    });
  }

  function bindPalette(input, wrapper) {
    $('.tile', wrapper).click(function() {
      //grab from the tile's id
      var color = '#' + $(this).attr('id');
      //unhook ourselves from the page
      hidePicker(input);
      $(input).val(color);
      $(input).change();
    });

    $('ul.palette-select li', wrapper).click(function(){

      $(input).data('selection', $(this).prevAll().length);
      $('.kolorPicker-popup', wrapper).html(paletteHTML[$(input).data('selection')]);
      $('li', wrapper).eq(selection).addClass('kolorpicker-palette-select');
      bindPalette(input, wrapper);
    });

    $('.x-close-box', wrapper).click(function(){
      hidePicker(input);
    });
  }

  function showPicker(input) {
    var wrapper = $(input).parent();
    $(input).css('z-index', 1020);
    $(input).after('<div class="kolorPicker-popup"/>');
    $(input).next().html(paletteHTML[$(input).data('selection')]);
    $('body').bind('click.kolorpicker', function(ev) {
      if ($(ev.target).parent().length > 0 && !($(ev.target).parents().is(wrapper))) {
        $('body').unbind('click.kolorpicker');
        hidePicker(input);
      }
    });

    bindPalette(input, wrapper);
  };

  function hidePicker(input) {
    if ($(input).next().is('.kolorPicker-popup')) {
      $(input).css('z-index', '');
      $(input).next().remove();
    }
  };

  bindColorPicker = bindPicker;
});



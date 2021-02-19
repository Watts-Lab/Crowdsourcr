/*global $ jQuery _*/

$(onLoad);

function getAdminTask() {
    var hash = $(window.location).attr('hash');
    var prefix = '#task=';
    if (hash.slice(0, prefix.length) === prefix) {
        return hash.slice(prefix.length);
    } else {
        return undefined;
    }
}

var haveUsedForcedHit = false;
function getForcedHit() {
    if (haveUsedForcedHit) return undefined;
    haveUsedForcedHit = true;
    var hash = $(window.location).attr('hash');
    var prefix = '#id=';
    if (hash.slice(0, prefix.length) === prefix) {
        return hash.slice(prefix.length);
    } else {
        return undefined;
    }
}

function ping() {
    $.post('/worker/ping', {}, function(data) {
        $("#ping-error").hide();
        setTimeout(ping, 5000);
    }).fail(function () {
        if (!$("#ping-error").is(":visible")) {
          $("#ping-error").show();
          scrollToTop($("#hit-modules-scroll"));
        }
        setTimeout(ping, 5000);
    });
}

function scrollToTop($div) {
  $div.animate({scrollTop : 0}, 500);
}
function scrollToBottom($div) {
  $div.animate({scrollTop : $div[0].scrollHeight}, 500);
}

var currentTypeGroup = null;

function showWithData(task, modules) {
    $('.content-main').show();
    $('#login-panel').hide();
    $("#hit-content-iframe").ready(function(){
        var iframe=document.getElementById('hit-content-iframe').contentWindow.$("#content");
        iframe.empty();
        iframe.append(task.content);
        currentTypeGroup = new CTypeGroup();
        $('#hit-modules').empty();
        for (var i = 0; i < task.modules.length; i++){
            var dest = $('<div/>').appendTo($('#hit-modules'));
            registerModule(i, modules[task.modules[i]], dest);
        }    
    });
}

var hitLoadingTime = undefined;
var maxWaitingTime = 45 * 1000;

function requestNextTask(response) {
    // Response is from the server indicating whether validation succeeded.
    $("#next-task-button").attr('disabled', false);
    if (response && response.error) {
	      switch (response.explanation) {
	      case 'no_cookies' :
            $("#next-task-button").attr('disabled', true);
            $("#other-error").show().text('Your cookies were cleared and you are no longer authenticated. Please reload this page and login with your worker id again.');
            scrollToTop($("#hit-modules-scroll"));
	          break;
	      case 'not_logged_in' :
            $("#next-task-button").attr('disabled', true);
            $("#other-error").show().text('You are not logged in. Please reload this page and login with your worker id again.');
            scrollToTop($("#hit-modules-scroll"));
	          break;
	      case 'invalid_response' :
            $("#validation-error").show();
            scrollToBottom($("#hit-modules-scroll"));
            break;
        default :
            $('#unknown-error').show();
            scrollToBottom($("#hit-modules-scroll"));
            break;
	      };
	      return;
    }

    if (hitLoadingTime === undefined) {
	      hitLoadingTime = Date.now();
    }
    if (getAdminTask() !== undefined) {
        $('#next-task-button').attr('disabled', true);
        $('#return-hit').attr('disabled', true);
        $('#hit-progress').text("Single task view");
        $.get('/admin/tasks/' + getAdminTask(), function (data) {
            $('.loading-holder').hide();
            showWithData(data.task, data.modules);
        });
        return;
    }
    var getData = {};
    var forcedId = getForcedHit();
    if (forcedId !== undefined) {
        getData['force'] = true;
        getData['hitid'] = forcedId;
        getData['workerid'] = $('#login-panel').find('input:first').val();
    }
    $.post('/HIT/view/', getData, function(data) {
	      $('.loading-holder').hide();

	      if (data.no_hits) {
	          $('.content-main').hide();
	          $('#login-panel').hide();
	          $('.turk-verify-content').hide();
	          if (data.unfinished_hits && (Date.now() - hitLoadingTime) < 45000) {
		            $('.loading-holder').show();
		            setTimeout(requestNextTask, 5000);
	          } else {
		            $('.turk-no-hits').show();
	          }
	          return;
	      }

	      if (data.needs_login) {
	          if (data.reforce) {
                haveUsedForcedHit = false;
            }
	          $('#login-panel').show();
            $('#login-panel').find('input').focus();
	          return;
	      }
	      
	      $('.content-main').show();
	      $('#login-panel').hide();

	      if (data.reload_for_first_task) {
	          requestNextTask();
	      } else if (data.completed_hit) {
	          $('.content-main').hide();
	          $('#login-panel').hide();
	          $('.turk-verify-content').show().find('.secret-code').html(data.verify_code);
	      } else {
            $('#hit-progress').text("You are on task " + (+data.task_num + 1) + " of " + data.num_tasks  + ".");
            showWithData(data.task, data.modules);
	      }
    });
}

function onLoad() {
    ping();

    $('#return-hit').click(function(e) {
	      e.preventDefault();
	      if (window.confirm('Are you sure you want to return this HIT? You will lose all of your progress and this HIT will be assigned to another worker.')) {
	          window.location.href = '/HIT/return';
	      }
    });

    $('#next-task-button').click(function(evt) {
	      evt.preventDefault();
        $("#validation-error").hide();
        $("#unknown-error").hide();
        if (currentTypeGroup.validate()) {
	          submitTask(requestNextTask);
        } else {
            var invalidQ = $(".question-invalid");
            if (invalidQ) {
                $("#hit-modules-scroll").prop("scrollTop", invalidQ.prop("offsetTop")-16*5);
            }
        }
    });

    $('#worker-login-submit').click(function(evt) {
	      evt.preventDefault();
	      $.post('/worker/login/', {'workerid' : $('#login-panel').find('input:first').val()}, requestNextTask);
    });

    $('body').on('click', function (e) {
        var target = $(e.target);
        if (!target.hasClass('popover') && !target.parent().hasClass('popover') && !target.hasClass('help')) {
            $('.help').each(function() {
		            $(this).popover('hide');
            });
        }
    });

    requestNextTask();
}

function submitTask(callback) {
    $("#next-task-button").attr('disabled', true);
    $.post('/HIT/submit/', {data : JSON.stringify(serializeModules())}, callback)
     .fail(function () {
        $('#unknown-error').show();
        scrollToBottom($("#hit-modules-scroll"));
        $("#next-task-button").attr('disabled', false);
     });
}

function serializeModules() {
    return currentTypeGroup.serialize();
}

function registerModule(i, data, dest) {
    var module_container = $(document.createElement('div'));
    var module = module_container.CType(currentTypeGroup, data);
    module.renderDisplay();
    dest.append($(document.createElement('li')).html(module_container));
    if (i == 0) {
        currentTypeGroup.showType(module);
    }
}

function showMyImage(fileInput,element) {
    var files = fileInput.files;
    for (var i = 0; i < files.length; i++) {           
        var file = files[i];
        var imageType = /image.*/;     
        if (!file.type.match(imageType)) {
            continue;
        }           
        var img=element.parent().parent().find('img')[0]; 
        img.style.display="";           
        img.file = file;    
        var reader = new FileReader();
        var hiddenElement=element.parent().parent().children('input')[0];
        reader.onload = (function(aImg,hiddenElement) { 
            return function(e) { 
                aImg.src = e.target.result;
                hiddenElement.value=aImg.src;
            }; 
        })(img,hiddenElement);
        reader.readAsDataURL(file);
    }    
}

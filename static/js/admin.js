      var seenEvents = {};

      $(onReady);

      function nocache() {
          return "?nocache=" + new Date().getTime();
      }
      function onReady() {
          $('#upload-btn').click(function(evt) {
              evt.preventDefault();
              uploadXML();
          });
          
          
          $('#admin-begin-run').click(function(evt) {			  
              evt.preventDefault();
              beginRun();
          });
          
          $('#admin-end-run').click(function(evt) {
				evt.preventDefault();
				$('#admin-end-run').hide();
				$('#admin-end-run-submitting').show();		  
				$.post('/admin/recruit/end/', {}).always(function () {
					$.get('/admin/info/' + nocache(), function(data) {
					try {
						updateStatus(data,false);
						$('#admin-end-run').show();
						$('#admin-end-run-submitting').hide();
						$('#admin-end-run-original').hide();
						$('#admin-begin-run-original').show();				  
						$('#endRunModal').modal('hide');				  						
					}finally {}});
				});
          });			  						
          
          $('#download-data-btn').click(function(evt) {
              evt.preventDefault();
              window.location.href = '/admin/download/';
          });
          $('#download-bonusinfo-btn').click(function(evt) {
              evt.preventDefault();
              window.location.href = '/admin/bonusinfo/';
          });

$('#addAdmin').click(function(evt) {
	  evt.preventDefault();
	  var new_admin_email = $("#newAdmin").val();
	  $("#newAdmin").val('');
	  $.post('/admin/new', {data : JSON.stringify({email : new_admin_email})}, function() {
	    reloadAdminList();
	  });
});

          $('#openEditModalButton').click(function(evt) {
				$('#editHITparameters').show();
				$('#editHITparameters-submitting').hide();
                $('#editHitPayment').val($('#staticHitPayment').val());
                $('#editBonusPayment').val($('#staticBonusPayment').val());
				$('#editHitTitle').val($('#staticHitTitle').val());
				$('#editHitDescription').val($('#staticHitDescription').val());
				$('#editHitKeywords').val($('#staticHitKeywords').val());
				$('#editHitLifetime').val($('#staticHitLifetime').val());
                if ($('#editHitLifetime').val()==""){
                    $('#editHitLifetime').val(12*3600);
                }                
                $('#editHitLocales').val($('#staticHitLocales').val());                
                if ($('#editHitLocales').val()==""){
                    $('#editHitLocales').val("US");
                }                
				$('#editHitPCapproved').val($('#staticHitPCapproved').val());
                if ($('#editHitPCapproved').val()==""){
                    $('#editHitPCapproved').val(95);
                }                
                $('#editHitMinCompleted').val($('#staticHitMinCompleted').val());
                if ($('#editHitMinCompleted').val()==""){
                    $('#editHitMinCompleted').val(100);
                }           
                $('#editInvalidReplacementIntervalSeconds').val($('#staticInvalidReplacementIntervalSeconds').val());
                if ($('#editInvalidReplacementIntervalSeconds').val()==""){
                    $('#editInvalidReplacementIntervalSeconds').val(100);
                }                                           
				$('#editHitWarning').hide();
                $('#editHitServerWarning').hide();
				$('#beginEditHitModal').modal('show');		
		  });	
				
			
          $('#editHITparameters').click(function(evt) {
              evt.preventDefault();
			  var mturk_info = {hitpayment : parseFloat($('#editHitPayment').val()),
                            title : $('#editHitTitle').val(),
                            description : $('#editHitDescription').val(),
                            keywords : $('#editHitKeywords').val(),
                            bonus : parseFloat($('#editBonusPayment').val()),
                            lifetime:  $('#editHitLifetime').val(),
                            locales : $('#editHitLocales').val(),	
                            pcapproved : $('#editHitPCapproved').val(),	
                            mincompleted : $('#editHitMinCompleted').val(),
                            invalidReplacementIntervalSeconds : $('#editInvalidReplacementIntervalSeconds').val(),
                        };	
			console.log(mturk_info);
			for (var key in mturk_info) {
              if (mturk_info.hasOwnProperty(key) && !mturk_info[key]) {
					$('#editHitWarning').show();
                  return;
              }
            }
			$('#editHitWarning').hide();
			$('#editHitServerWarning').hide();
			$('#editHITparameters').hide();
			$('#editHITparameters-submitting').show();
			$.post('/admin/recruit/',{data : JSON.stringify(mturk_info)}, function(data) {
                    if (data["errors"]){
                        $('#editHitServerWarning').empty();
                        for(var i in data["errors"]){
                            $('#editHitServerWarning').append("<p>"+data["errors"][i]+"</p>")
                        }
                        $('#editHITparameters-submitting').hide();
                        $('#editHITparameters').show();
                        $('#editHitServerWarning').show();
                    }
                    else{
                        $.get('/admin/info/' + nocache(), function(data) {
                        try {
                            updateStatus(data,true);
                            $('#editHITparameters').show();
                            $('#editHITparameters-submitting').hide();
                            $('#beginEditHitModal').modal('hide');		
                        }finally {}});				    
                    }                 
			});
          });



	  // Add the following code if you want the name of the file appear on select
	  $(".custom-file-input").on("change", function() {	
		var fileName = $(this).val().split("\\").pop();
		$(this).siblings(".custom-file-label").addClass("selected").html(fileName);
      });

          
          getStatus(true);
          getHITs();
		  reloadAdminList();
      }
      
      function getHITs() {
          $.get('/admin/hits' + nocache(), function (data) {
              $('#admin-hits').hide();
              $('#admin-hit-tasks').hide();
              if (data.ids !== undefined) {
                  var ids = data.ids.slice();
                  ids.sort();
                  var $d = $('#admin-hits-dest');
                  $d.empty();
                  var sep = "";
                  for (var i = 0, hid; hid = ids[i]; i++) {
                      $d.append(sep);
                      sep = ", ";
                      var $a = $('<a href="#"/>').text(hid).attr('hit-id', hid);
                      (function (hid) {
                          $a.on("click", function (e) {
                              e.preventDefault();
                              showTasks(hid);
                              return false;
                          });
                      })(hid);
                      $d.append($a);
                  }
                  $('#admin-hits').show();
              }
          });
      }
      
      function beginRun(callback) {
          $('#admin-begin-run').hide();
          $('#admin-begin-run-submitting').show();		  
          $.post('/admin/recruit/begin', {}, callback).always(function () {
					$.get('/admin/info/' + nocache(), function(data) {
					try {
						updateStatus(data,false);
						$('#admin-begin-run').show();
						$('#admin-begin-run-submitting').hide();
						$('#admin-begin-run-original').hide();
						$('#admin-end-run-original').show();				  
						$('#beginRunModal').modal('hide');				  
					}finally {}});
              });
      }
      
      function getStatus(updateTurkInfo) {
          $.get('/admin/info/' + nocache(), function(data) {
              try {
				  updateStatus(data,updateTurkInfo);
              } finally {
                  setTimeout(getStatus, 5000);
              }
          }).fail(function () {
              $('#admin-server-info').html('<span class="error">Error updating server information</span>').show();
              setTimeout(getStatus, 5000);
          });
      }
	  
	  function updateStatus(data,updateTurkInfo){
                  if (data.authed) {
                      $('#admin-login-info').text('Logged in as ' + data.full_name + ' (' + data.email + ').');
                      $('#admin-server-info').text('Server is running in '+ data.environment +' mode.');
                      $('#admin-superadmin').toggle(data.superadmin);
                      var taskInfo=data.hitinfo.num_hits + ' HITs ('+ data.hitinfo.num_tasks +' tasks) loaded. ' + data.hitinfo.num_completed_hits + ' HITs ('+ data.hitinfo.num_completed_tasks +' tasks) complete. ';
                      taskInfo=taskInfo+data.hitinfo.num_completed_hits_validation_notpassed +' invalid HITs ';
                      taskInfo=taskInfo+"("+data.num_extra_assignments+" extra assignments created, "+data.num_pending_extra_assignments+" pending assignments).";
                      $('#admin-task-info').html(taskInfo);                      
                      if (!data.turkinfo || !data.turkbalance || data.hitinfo.num_hits==0) {
						  $('#openEditModalButton').attr("disabled", false);
						  if (!data.turkinfo){
							$('#admin-turk-info').html('MTurk HIT parameters need to be defined.');
						  }
						  else{
							if (!data.turkbalance){
								$('#admin-turk-info').html('Could not authenticate with MTurk.');
							}
							else{
								$('#admin-turk-info').html('Survey needs to be uploaded.');
							}
						  }
                          $('#admin-begin-run-original').hide();
                          $('#upload-btn').attr("disabled", false);						  
                          $('#upload-btn-title').attr("title", "");						  
                      } else {
                          $('#admin-turk-info').html('MTurk authenticated. Current balance: ' + data.turkbalance);
                          if (updateTurkInfo) {
								$('#staticHitPayment').val(data.turkinfo.hitpayment);
								$('#staticBonusPayment').val(data.turkinfo.bonus);
								$('#staticHitTitle').val(data.turkinfo.title);
								$('#staticHitDescription').val(data.turkinfo.description);
								$('#staticHitKeywords').val(data.turkinfo.keywords);							  
								$('#staticHitLifetime').val(data.turkinfo.lifetime);							  
								$('#staticHitLocales').val(data.turkinfo.locales);							  
								$('#staticHitPCapproved').val(data.turkinfo.pcapproved);							  
                                $('#staticHitMinCompleted').val(data.turkinfo.mincompleted);
                                $('#staticInvalidReplacementIntervalSeconds').val(data.turkinfo.invalidReplacementIntervalSeconds);                                                            
                          }
                          if (data.turkinfo.running) {
                              var amazonLink = data.turkinfo.admin_host + "/mturk/manageHIT?HITId=" + data.turkinfo.hitid;
                              $('#admin-turk-info').html('HIT id:  <a href="' + amazonLink + '" target="_blank">' + data.turkinfo.hitid + '</a>.');
                              $('#admin-hit-info').show();
                              $('#admin-hit-info').html('<a href="'+data.turkinfo.preview+'" target="_blank">View HIT</a>.');
                              $('#admin-begin-run-original').hide();
                              $('#admin-end-run-original').show();
                              $('#upload-btn').attr("disabled", true);
                              $('#upload-btn-title').attr("title", "An experiment is running.");
                              $('#download-bonusinfo-btn').attr("disabled", true);
                              $('#download-bonusinfo-btn-title').attr("title", "Stop the experiment to ensure MTurk workers are paid their bonuses.");
  							              $('#openEditModalButton').attr("disabled", true);
                          } else {
                              var amazonLink = data.turkinfo.admin_host + "/mturk/manageHITs";
                              $('#admin-turk-info').append('<p> Not currently running. <a href="' + amazonLink + '" target="_blank">Manage HITs</a></p>');
                              $('#admin-hit-info').hide();
                              $('#admin-end-run-original').hide();
                              $('#admin-begin-run-original').show();
                              $('#upload-btn').attr("disabled", false);
                              $('#upload-btn-title').attr("title", "");
                              $('#download-bonusinfo-btn').attr("disabled", false);
                              $('#download-bonusinfo-btn-title').attr("title", "");
  							              $('#openEditModalButton').attr("disabled", false);
                              $('#submit-task-info').html("<strong>Projected Costs: $" + (1.2 * data.hitinfo.num_hits * (data.turkinfo.hitpayment + 0.01)).toFixed(2) + " - $" + (1.2 * data.hitinfo.num_hits * (data.turkinfo.hitpayment + data.turkinfo.bonus)).toFixed(2) + "</strong> (incl. MTurk fees) <br>(" + data.hitinfo.num_hits + " HITs with " + data.turkinfo.hitpayment + " reward and up to " + data.turkinfo.bonus + " bonus per HIT) <br> <strong>Available funds in " + data.environment + " mode: $" +  data.turkbalance + "</strong>");
                          }
                          
                      }
                      $('#admin-xml-upload').show();
                      $('#admin-mturk-cred').show();
                  } else {
                      if (data.reason === 'not_admin') {
                          $('#admin-login-info').html('You are not an admin.  Talk to a superadmin to add you to the admins.');
                      } else if (data.reason === 'no_login') {
                          // Not authenticated. Just redirect to the login page.
                          window.location = "/admin/login";
                      } else {
                          $('#admin-login-info').html('You cannot see this for some unknown reason.');
                      }
                  }

                  var resolvedStatuses = {};
                  var outstanding = data.hitstatus.outstanding || [];
                  for (var i = 0; i < outstanding.length; i++) {
                      resolvedStatuses[outstanding[i]] = 'outstanding';
                  }
                  var completed = data.hitstatus.completed || [];
                  for (var i = 0; i < completed.length; i++) {
                      resolvedStatuses[completed[i]] = 'completed';
                  }
                  $('[hit-id]').each(function () {
                      var hid = $(this).attr('hit-id');
                      var status = "unseen";
                      if (Object.prototype.hasOwnProperty.call(resolvedStatuses, hid)) {
                          status = resolvedStatuses[hid];
                      }
                      var fontweight = 'normal';
                      var fontstyle = 'normal';
                      var color = 'orange';
                      switch (status) {
                      case "outstanding" :
                          fontweight = "bold";
                          color = 'red';
                          break;
                      case "completed" :
                          fontstyle = 'italic';
                          color = 'green';
                          break;
                      case "unseen" :
                          // fallthrough
                      default :
                          break;
                      }
                      $(this).css({
                          'font-weight' : fontweight,
                          'font-style' : fontstyle,
                          'color' : color
                      });
                  });
                  var $aed = $('#admin-events-dest');
                  var events = data.events || [];
                  var newEvents = false;
                  for (var i = 0; i < events.length; i++) {
                      if (!seenEvents.hasOwnProperty(events[i].date)) {
                          seenEvents[events[i].date] = true;
                          newEvents = true;
                          var date = new Date(events[i].date);
                          var $el = $('<div class="event">');
                          $el.append($('<div class="event-date">').text(''+date));
                          $el.append($('<div class="event-text">').text(events[i].event));
                          $aed.append($el);
                      }
                  }
                  if (newEvents) {
                      $aed.scrollTop($aed[0].scrollHeight);
                  }
	  }
      
      function showTasks(hid) {
          var $h = $('#admin-hit-tasks');
          $h.hide().empty();
          $.get('/admin/hits/' + hid + nocache(), function (data) {
              $h.append($('<p/>').text("Tasks for " + hid));
              var $dest = $('<p/>').appendTo($h);
              var sep = "";
              for (var i = 0, tid; tid = data.tasks[i]; i++) {
                  $dest.append(sep);
                  sep = ", ";
                  var $a = $('<a target="_blank"/>').text(tid).attr('href', '/HIT/#task=' + tid);
                  $dest.append($a);
              }
              $h.append($("<p/>").append($("<a/>").text("Show HIT").attr('target', '_blank').attr('href', '/HIT/#id=' + hid)));
              $h.slideDown();
          });
      }
            
      function uploadXML() {
          $('#upload-btn').hide();
          $('#upload-btn-loading').show();		  
          $("#xml-upload-error").hide();
          $("#xml-upload-success").hide();
          var data = new FormData();
          data.append('file', $('#xml-upload-file')[0].files[0]);
          $.ajax({
              url: '/admin/xmlupload/',
              data: data,
              cache: false,
              contentType: false,
              processData: false,
              type: 'POST',
              success: function(data){
				  $('#upload-btn').show();
				  $('#upload-btn-loading').hide();		  
                  if (data.success !== undefined) {
                      var $succ = $("#xml-upload-success");
                      $succ.text("Successfully uploaded.")
                      $succ.fadeIn();
                      //getStatus();
                  } else {
                      var $err = $("#xml-upload-error");
                      $err.text(data.error);
                      $err.fadeIn();
                  }
                  getHITs();
              },
              error: function () {
				  $('#upload-btn').show();
				  $('#upload-btn-loading').hide();		  
              }
          });
      }

function removeAdminHandler(email) {
  return function (e) {
    e.preventDefault();
	  $.post('/admin/remove', {data : JSON.stringify({email : email})}, function () {
	    reloadAdminList();
	  });
  };
}

function reloadAdminList() {
  $.get('/admin/all', function(data) {
	  var adminList = $('#administrator-all-list');
	  adminList.empty();
	  for (var i = 0; i < data.length; i++) {
	    var anchor_holder = $(document.createElement('a')).attr('href', '#').html(data[i]);
      anchor_holder.on("click", function (e) { e.preventDefault(); });
	    var remove_link = $(document.createElement('a')).attr('href', '#').html('&times;');
	    remove_link.on("click", removeAdminHandler(data[i]));
	    anchor_holder.append(" ").append(remove_link);
      adminList.append($(document.createElement('li')).addClass('list-group-item').append(anchor_holder));
	  }
  });
}


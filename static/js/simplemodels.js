/*global jQuery Model _ $*/

"use strict";

jQuery.fn.CType = function(typeGroup, params) {
    return new CType(this[0], typeGroup, params);
};

var CTypeGroup = Model.extend({
    constructor : function () {
	      this.types = [];
    },
    addType : function (ctype) {
	      this.types.push(ctype);
    },
    showType : function (ctype) {
          if (ctype.contentUpdate){
            var iframe=document.getElementById('hit-content-iframe').contentWindow;
            var update=ctype.contentUpdate.split(';');
            iframe[update[0]](update[1]);
          }
	      ctype = ctype || this.types[0];
	      _.each(this.types, function (t) {
	          if (t === ctype) {
		            t.show();
	          } else {
		            t.hide();
	          }
	      });
    },
    serialize : function () {
        return _.invoke(this.types, 'serialize');
    },
    validate : function () {
        function isInvalid(type) {
            return !type.validate();
        }
        var type = _.find(this.types, isInvalid);
        if (type) {
            this.showType(type);
            return false;
        } else {
            return true;
        }
    }
});

var CType = Model.extend({
    constructor : function(el, typeGroup, params) {
	      params = params || {};
	      this.el = $(el);
	      this.typeGroup = typeGroup;
	      typeGroup.addType(this);
	      this.display_template = $('#ctype-display-template').html();
	      this.name = params.name || '';
          this.header = params.header || '';
          this.contentUpdate=params.contentUpdate;
	      this.questionlist = new QuestionList(params.questions || []);
	      this.el.empty();
    },
    renderDisplay : function() {
	      var self = this;
	      var sub_disp = $(document.createElement('div'));
	      sub_disp.html(self.display_template);
	      this.el_display_props = sub_disp.find('[data-prop]');
	      this.question_container = sub_disp.find('.question-display-container:first');
	      this.questionlist.renderDisplay(this.name,this.question_container);
	      this.el.append(sub_disp);
	      this.hide(true); // updatesdisplay, too
	      this.el.find(".ctype-when-hidden").on("click", function () {
	          self.typeGroup.showType(self);
	      });
	      this.el.find("form").on("change", function () {
	          $(".question-invalid").removeClass("question-invalid");
	      });
    },
    objectifyDisplay : function() {
	      return {
	          name : this.name,
	          header : this.header,
	          numQuestions : this.questionlist.numQuestions(),
	          numCompleted : this.questionlist.numCompleted()
	      };
    },
    serialize : function() {
        //console.log(this.questionlist.serialize());
        return {
	          name : this.name,
	          responses : this.questionlist.serialize()
	      };	    
    },
    hide : function (fast) {
	      if (fast) {
	          this.el.find(".ctype-when-visible").hide();
	      } else {
	          this.el.find(".ctype-when-visible").slideUp();
	      }
	      this.el.find(".ctype-when-hidden").show();
	      this.updateDisplay();
    },
    show : function () {
	      this.el.find(".ctype-when-visible").slideDown();
	      this.el.find(".ctype-when-hidden").hide();
	      this.updateDisplay();
    },
    validate : function () {
	      return this.questionlist.validate();
    }
});

var check_condition_single = function (condition, vals, status) {
    if (condition.op === "NOTINSET") {
        status.error = true;
        return true;
    }
    if (condition.op=="EXISTS"){
        if (condition.variables[0].slice(-1)==="*"){
            var prefix=condition.variables[0].substring(0,condition.variables[0].length-1);
            for(var v in vals){
                if (v.startsWith(prefix) && vals[v]!=""){
                    return true;
                }
            }
            return false;
        }
        if (vals[condition.variables[0]]!==undefined){
            return true;
        }
        return false;
    }
    condition.variables.forEach(function (v) {
        if (!(v in vals)) {
            status.error = true;
        }
    });
    if (status.error) { return true; }
    var LHS_sum = 0;
    var LHS = ""
    if (condition.values_integers.length > 0) {
        condition.variables.forEach(function (v) {
            var parsed = parseInt(vals[v]);
            if (isNaN(parsed)) {
                status.error = true;
            }
            else
            {
                LHS_sum = LHS_sum + parsed;
            }
        });
    }
    else {
        LHS = vals[condition.variables[0]];
    }
    switch (condition.op) {
        case ("EQUAL"):
            if (condition.values_integers.length > 0) {
                return LHS_sum == condition.values_integers[0];
            }
            else {
                return LHS == condition.values_string[0];
            }
        case ("NOTEQUAL"):
            if (condition.values_integers.length > 0) {
                return LHS_sum != condition.values_integers[0];
            }
            else {
                return LHS != condition.values_string[0];
            }
        case ("GREATEREQUAL"):
            if (condition.values_integers.length > 0) {
                return LHS_sum >= condition.values_integers[0];
            }
            break;
        case ("LESSEQUAL"):
            if (condition.values_integers.length > 0) {
                return LHS_sum <= condition.values_integers[0];
            }
            break;
        case ("EXISTS"):

            break;
    }
    return true;
}

var checkLexer = function (lex, vals, status) {
    var condition_values = [];
    lex.conditions.forEach(function (c) {
        condition_values.push(check_condition_single(c, vals, status));
    });
    lex.fragments.forEach(function (f) {
        condition_values.push(checkLexer(f, vals, status));
    });
    switch (lex.logical) {
        case "NONE":
            return condition_values[0];
        case "AND":
            var sum = true;
            condition_values.forEach(function (p) {
                sum = sum & p;
            });
            return sum;
        case "OR":
            sum = false;
            condition_values.forEach(function (p) {
                sum = sum | p;
            });
            return sum;
    }
    return true;
}

var checkSingleCondition = function (vals, condition) {
    if (condition == null) { return true; }
    //parse lexed condition
    var lex = JSON.parse(condition);
    var status = { error: false };
    var evaluatedLexer = checkLexer(lex, vals, status);
    if (status.error) {
        return false;
    }
    return evaluatedLexer;
};

var checkConditions = function (renderedquestions, holders) {
    //collect question values
    var vals = {};
    for (var i = 0; i < renderedquestions.length; i++) {
        vals[renderedquestions[i].varname] = renderedquestions[i].response();
    }
    for (var i = 0; i < renderedquestions.length; i++) {
        //console.log(renderedquestions[i]);
        if (checkSingleCondition(vals, renderedquestions[i].condition)) {
            holders[i].show();
        }
        else {
            holders[i].hide();
        }
    }
}

var QuestionList = Model.extend({
    constructor : function(questions) {
	      this.questions = questions || [];
	      this.display_template = $('#questionlist-display-template').html();
	      this.renderedquestions = [];
	      this.holders = [];
    },
    renderDisplay : function(moduleName,el) {
        this.el = $(el);
	    this.el.empty();
	    var rendered_ref = this.renderedquestions;
	    var holders_ref = this.holders;
	    _.each(this.questions, function (q) {
              var question_holder = $(document.createElement('li'));
              question_holder.change(function () {
                  checkConditions(rendered_ref, holders_ref);
              });
              var question = new Question(question_holder, q, moduleName);
	          question.renderDisplay();
	          this.el.append(question_holder);
	          this.holders.push(question_holder);
	          this.renderedquestions.push(question);
        }, this);
	    checkConditions(rendered_ref, holders_ref);
    },
    serialize : function() {
        return _.invoke(this.renderedquestions, 'serialize');
    },
    numQuestions : function () {
	      return this.renderedquestions.length;
    },
    numCompleted : function () {
        return _.chain(this.renderedquestions)
                .invoke('validate')
                .filter(_.identity) // keep true ones
                .size()
                .value();
    },
    validate : function () {
        //collect question values
        var vals = {};
        for (var i = 0; i < this.renderedquestions.length; i++) {
            vals[this.renderedquestions[i].varname] = this.renderedquestions[i].response();
        }
        for (var i = 0; i < this.renderedquestions.length; i++) {
            if (checkSingleCondition(vals, this.renderedquestions[i].condition) && !this.renderedquestions[i].validate()){
		            this.holders[i].addClass("question-invalid");
		            return false;
	        }
	    }
	    return true;
    }
});

var Question = Model.extend({
    constructor : function(el, question, moduleName) {
          var new_question = undefined;
          question.fullVarname=moduleName+":"+question.varname;
	      switch (question.valuetype) {
	      case 'numeric':
              new_question = new NumericQuestion(el, question);
	          break;
	      case 'categorical':
	    	  new_question = new CategoricalQuestion(el, question);
	          break;
	      case 'text':
	          new_question = new TextQuestion(el, question);
	          break;
          case 'autocomplete':
              new_question = new AutoCompleteQuestion(el, question);
              break;
          case 'approximatetext':
              new_question = new ApproximateTextQuestion(el, question);
              break;
          case 'url':
	          new_question = new URLQuestion(el, question);
	          break;
	      case 'comment':
	          new_question = new CommentQuestion(el, question);
	          break;
	      case 'imageupload':
	          new_question = new UploadQuestion(el, question);
	          break;
	      }

	      if (new_question === undefined)
          throw "Error: could not find type " + question.valuetype;

	      new_question.valuetype = question.valuetype;
	      new_question.questiontext = question.questiontext;
	      new_question.helptext = question.helptext;
	      new_question.fullVarname = question.fullVarname;
	      new_question.varname = question.varname;
          new_question.condition = question.condition;
	      new_question.content = question.content;
	      new_question.options = question.options;
	      return new_question;
    },
    serialize : function() {
	      return { 
	          varname : this.varname,
	          response : this.response()
	      };
    },
    serializeForDisplay : function() {
	      return {
	          questiontext : this.questiontext,
	          valuetype : this.valuetype,
              varname : this.varname,
              fullVarname : this.fullVarname,
	          content : this.content,
	          helptext : this.helptext,
	          options : this.options
	      };
    },
    validate : function () {
	      if (this.response() === undefined) {
	          return false;
	      } else {
	          return true;
	      }
    },
    renderHelpText : function() {
	      var self = this;
	      if (this.helptext) {
	          this.el.find('.help:first').popover({ placement : 'bottom',
						                                      title : undefined,
						                                      content : self.helptext,
						                                      trigger : 'manual',
						                                      html: true });
	          this.el.find('.help:first').click(function() {
		            $(this).popover('toggle');
	          });
	      }
    }
});

var TextQuestion = Question.extend({
    constructor : function(el, question) {
        this.el = $(el);
	      this.display_template = $('#textquestion-display-template').html();
    },
    renderDisplay : function() {
        this.el.empty();
        var q = this.el.html(_.template(this.display_template, this.serializeForDisplay()));
	      this.renderHelpText();
    },
    validate : function () {
        return this.response() != "";
    },
    response : function() {
	      return this.el.find('textarea:first').val();
    }
});

var AutoCompleteQuestion = Question.extend({
    constructor : function(el, question) {
        this.el = $(el);
	      this.display_template = $('#autocompletequestion-display-template').html();
    },
    renderDisplay : function() {
        this.el.empty();
        var q = this.el.html(_.template(this.display_template, this.serializeForDisplay()));
	      this.renderHelpText();
    },
    validate : function () {
        return this.response() != "";
    },
    response : function() {
        var radioValue=this.el.find('input:not([value=""]):checked').val();
        if (radioValue=="unsureLabel"){
            return "unsure";
        }
        var specificInput=this.el.find('input[type=text]').val()
        if (radioValue=="sureLabel" & specificInput!=""){
            return "sure:"+specificInput;
        }
        return "";
    }
});

var ApproximateTextQuestion = Question.extend({
    constructor : function(el, question) {
        this.el = $(el);
	      this.display_template = $('#textquestion-display-template').html();
    },
    renderDisplay : function() {
        this.el.empty();
        var q = this.el.html(_.template(this.display_template, this.serializeForDisplay()));
	      this.renderHelpText();
    },
    validate : function () {
        return this.response() != "";
    },
    response : function() {
	      return this.el.find('textarea:first').val();
    }
});

var URLQuestion = TextQuestion.extend({
    validate : function () {
    	if(this.response() == "") {
    		return false;
    	} else{
    		return /^(?:(?:(?:https?|ftp):)?\/\/)(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})).?)(?::\d{2,5})?(?:[/?#]\S*)?$/i.test( this.response() );
    	}
    }
});

var CommentQuestion = TextQuestion.extend({
    validate : function () {
    	return true;
    }
});


var UploadQuestion = Question.extend({
    constructor : function(el, question) {
        this.el = $(el);
	      this.display_template = $('#imageuploadquestion-display-template').html();
    },
    renderDisplay : function() {
        this.el.empty();
        this.el.html(_.template(this.display_template, this.serializeForDisplay()));
	      this.renderHelpText();
    },
    validate : function () {
    	if(this.response() == "") {
    		return false;
    	} else{
            if (this.response().length>16*1024*1024){
                return false;
            }
            return true;
    	}
    },
    response : function() {
	      return this.el.find('input:eq(1)').val();
    }
});


var NumericQuestion = Question.extend({
    constructor : function(el, question) {
        this.el = $(el);
	      this.display_template = $('#numericquestion-display-template').html();
    },
    renderDisplay : function() {
        this.el.empty();
        this.el.html(_.template(this.display_template, this.serializeForDisplay()));
	      this.renderHelpText();
    },
    validate : function () {
        return this.response() && !isNaN(+this.response());
    },
    response : function() {
	      return this.el.find('input:first').val();
    }
});

var CategoricalQuestion = Question.extend({
    constructor : function(el, question) {
        this.el = $(el);
	      this.display_template = $('#catquestion-display-template').html();
	      this.display_template_sideways = $('#catquestionsideways-display-template').html();
        this.display_template_dropdown = $('#catquestiondropdown-display-template').html();
	      this.nested_display_template = $('#catquestionsnested-display-template').html();
	      this.nesting_delimiter = '|';
    },
    shouldBeSideways : function () {
	      return this.options.layout === 'horizontal' || (this.content.length >= 5
		                                                    && _.all(this.content, function (choice) { return choice.text.length <= 2; }));
    },
    shouldBeDropdown: function () {
        return this.options.layout === 'dropdown';
    },
    renderDisplay : function() {
        this.el.empty();
	      var self = this;
	      if (this.nest === undefined && this.isNested()) {
	          this.constructNesting();
	      } else {
	          this.nest = false;
	      }
	      if (this.nest) {
	          var rendered_nest = $(this.drawNesting(this.nest, 
						                                       this.nested_display_template, 
						                                       0, 
						                                       this.questiontext, 
						                                       this.fullVarname));
	          rendered_nest
		            .find('input[type="radio"]')
		            .change(function() {
		                self.expandNest($(this), rendered_nest);
		            });
	          this.el.html(rendered_nest);
	      } else {
              var t = this.shouldBeSideways() ? this.display_template_sideways : this.display_template;
              if (this.shouldBeDropdown()) {
                  t = this.display_template_dropdown;
              }
            this.el.html(_.template(t, this.serializeForDisplay()));
	      }
	      this.renderHelpText();
    },
    isNested : function() {
	      return _.some(this.content, function(c) {
          return _.contains(c.text, this.nesting_delimiter);
        }, this);
    },
    constructNesting : function() {
	      this.nest = {};
	      var nest = {};
	      _.each(this.content, function(c) {
	          var n_pointer = this.nest;
	          _.each(c.text.split(/\s*\|\s*/), function(ordered_token) {
		            n_pointer = n_pointer[ordered_token] || (n_pointer[ordered_token] = {});
	          });
	          n_pointer['__val__'] = c.value;
	      }, this);
    },
    expandNest : function(el, top_el) {
	      var el_num = parseInt(el.attr('nesting-level'), 10);
	      // eliminate selections on all descendant radio buttons
	      el.find('input[type="radio"]').prop('checked', false);
	      // eliminate selections on all terminal radio buttons
	      top_el.find('input[type="radio"]').each(function() {
	          if ($(this).val() && $(this).val() !== el.val()) { $(this).prop('checked', false); }
	      });
	      top_el
	          .find('div.form-group')
	          .each(function() {
		            if (parseInt($(this).attr('nesting-level'), 10) > el_num) {
		                $(this).slideUp();
		            }
	          });
	      el.parent().siblings('div.form-group').slideDown();
    },
    drawNesting : function() {
	      return nestedTemplate(this.nest, this.nested_display_template, 0, this.questiontext, this.fullVarname);
    },
    validate: function () {
        var resp = this.response();
        return !(resp == "" | resp===undefined);
    },
    response : function() {
	      // darn selectors... (gross)
        if (this.shouldBeDropdown()) {
            return this.el.find('select:not([value=""])').val();
        }
        return this.el.find('input:not([value=""]):checked').val();
    } 
});

function nestedTemplate(nest, template, n, questiontext, fullVarname) {
    if (nest === undefined) return '';

    return _.template(template, { fullVarname : fullVarname,
				                          questiontext : questiontext,
				                          content : nest,
				                          generator : nestedTemplate,
				                          template : template,
				                          n : ++n });
}
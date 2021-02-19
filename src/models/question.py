import re
import validators
from helpers import CustomEncoder, Lexer, Status
import jsonpickle
from PIL import Image
import imagehash
import base64
import io
from helpers import jaccard_machine

class Question(object) :
    def __init__(self, varname=None, condition=None, questiontext=None, helptext=None, options=None, valuetype=None, bonus=None, bonuspoints=None):
        def validate_bonus(bonus) :
            if bonus == None or bonus == 'linear':
                return bonus
            else :
                try :
                    split_bonus = bonus.split(':')
                    bthresh = int(split_bonus[1])
                    if bthresh > 100 or bthresh < 0 or split_bonus[0] != 'threshold':
                        raise Exception('bthresh')
                    else :
                        return bonus
                except:
                    raise Exception('Question bonus string %s improperly formatted.' % bonus)

        def validate_bonuspoints(bonuspoints, bonus=bonus):
            try:
                bonuspoints = float(bonuspoints)
            except:
                raise Exception('bonus points for question %s must be coercible to float' % self.varname)

            if bonus is None:
                return 0.0

            if not bonuspoints >= 0:
                raise Exception('bonus points for question %s must be larger than 0' % self.varname)
            else:
                return bonuspoints

        self.varname = varname
        self.questiontext = questiontext
        self.helptext = helptext
        self.options = options
        self.bonus = validate_bonus(bonus)
        self.bonuspoints = validate_bonuspoints(bonuspoints)
        self.condition = condition
        self.valuetype = valuetype
    @classmethod
    def deserialize(cls, d) :
        if d['valuetype']=="categorical":
           return CategoricalQuestion.deserialize(d)
        if d['valuetype']=="numeric":
           return NumericQuestion.deserialize(d)
        if d['valuetype']=="text":
           return TextQuestion.deserialize(d)
        if d['valuetype']=="autocomplete":
           return AutoCompleteQuestion.deserialize(d)
        if d['valuetype']=="approximatetext":
           return ApproximateTextQuestion.deserialize(d)
        if d['valuetype']=="url":
           return URLQuestion.deserialize(d)
        if d['valuetype']=="comment":
           return CommentQuestion.deserialize(d)
        if d['valuetype']=="imageupload":
           return ImageUploadQuestion.deserialize(d)
    def serialize(self) :
        return {'valuetype' : self.valuetype,
                'varname' : self.varname,
				'condition' : self.condition,
				'bonuspoints' : self.bonuspoints,
                'questiontext' : self.questiontext,
                'helptext' : self.helptext,
                'options' : self.options,
                'content' : self.content,
                'bonus' : self.bonus}
    def get_bonus(self):
        if not self.bonus:
            return None
        elif self.bonus == 'linear':
            bonus_dict = { 'type' : 'linear' }
        else:
            split_bonus = self.bonus.split(':')
            bonus_dict =  { 'type' : 'threshold',
                            'threshold' : int(split_bonus[1]) }

        bonus_dict['bonuspoints'] = self.bonuspoints
        return bonus_dict

    def satisfies_condition(self, module_responses,varnameValuetype=None):
        if (self.condition==None):
            return True
        lex=jsonpickle.decode(self.condition)
        if varnameValuetype!=None:
            #check whether this variable was reachable
            for v in lex.varlist:
                for r in module_responses:
                    if v==r['varname']:
                        if r["response"] not in varnameValuetype[r["varname"]]["aprioripermissable"]:
                            return True
        allVariables=dict()
        has_error=False
        for r in module_responses:
            if "response" in r:
                allVariables[r["varname"]]=r["response"]
        status=Status()
        evaluatedLexer=lex.check_conditions(allVariables, dict(), status)
        if status.error!=None:
            return False
        return evaluatedLexer

    def sanitize_response(self, response):
        return response
    def valid_response(self, response):
        return True
    def validate(self, response, module_responses) :
        """Takes a question response as transmitted via JSON and validates it 
           given its own response and that to the rest of the question list.
           The method calls satisfies_condition(), which checks whether the
           display condition for the question is met and valid_response(), which
           checks that the response to the question itself is valid. The latter
           method can be overridden in classes that inherit from Question."""

        if not self.satisfies_condition(module_responses):
            return True
        else:
            return self.valid_response(response)
    def getBonusValue(self,response):
        #transforms the text into something that can be used for bonus calculations        
        return response

    # Parses XML to get question 'content' (returns list).
    # Currently only used for categorical questions.
    @classmethod
    def parse_content_from_xml(cls, question_type, question_content):
        if question_type=="categorical":
           return CategoricalQuestion.parse_content_from_xml(question_content)
        if question_type=="numeric":
           return NumericQuestion.parse_content_from_xml(question_content)
        if question_type=="text":
           return TextQuestion.parse_content_from_xml(question_content)
        if question_type=="approximatetext":
           return ApproximateTextQuestion.parse_content_from_xml(question_content)
        if question_type=="url":
           return URLQuestion.parse_content_from_xml(question_content)
        if question_type=="comment":
           return CommentQuestion.parse_content_from_xml(question_content)
        if question_type=="imageupload":
           return ImageUploadQuestion.parse_content_from_xml(question_content)

# Allows question-specific deserialization (not currently used).
# Otherwise unnecessary.
class AbstractQuestion(Question):
    def __init__(self, content=[], **kwargs) :
        Question.__init__(self, **kwargs)
        self.content = content
    @classmethod
    def deserialize(cls, d):
        return cls(**d)

class CategoricalQuestion(AbstractQuestion):
    typeName = 'categorical'
    @staticmethod
    def parse_content_from_xml(question_content):
        return [{'text' : category.find('text').text,
                 'value' : category.find('value').text,
                 'aprioripermissable': category.find('aprioripermissable').text=="true" if category.find('aprioripermissable') != None else False}
                for category in question_content.find('categories').iter('category')]
    def valid_response(self, response) :
        return response.get('response', False)

class NumericQuestion(AbstractQuestion):
    typeName = 'numeric'
    @staticmethod
    def parse_content_from_xml(question_content=None):
        return []
    def valid_response(self, response) :
        try :
            v = float(response.get('response', False))
            return True
        except ValueError :
            return False
    
class TextQuestion(AbstractQuestion) :
    typeName = 'text'
    @staticmethod
    def parse_content_from_xml(question_content=None):
        return []
    def sanitize_response(self, response):
        response['response'] = response['response'].strip()
        return response
    def valid_response(self, response) :
        return response.get('response', False)

class AutoCompleteQuestion(AbstractQuestion) :
    typeName = 'autocomplete'
    @staticmethod
    def parse_content_from_xml(question_content=None):
        return {'surelabel' : question_content.find('surelabel').text, 'unsurelabel' : question_content.find('unsurelabel').text, 'autoCompleteUrl':question_content.find('autoCompleteUrl').text}
    def valid_response(self, response) :
        return response.get('response', False)


class ApproximateTextQuestion(AbstractQuestion) :
    typeName = 'approximatetext'
    @staticmethod
    def parse_content_from_xml(question_content=None):
        return []
    def sanitize_response(self, response):
        response['response'] = "approximatetext:"+response['response'].strip()
        return response
    def valid_response(self, response) :
        return response.get('response', False)
    def getBonusValue(self,response):
        #get tokens
        jaccard=jaccard_machine.getJaccard()
        return  jaccard.getTokens(response[len("approximatetext:"):])

class URLQuestion(TextQuestion) :
    typeName = 'url'
    @staticmethod
    def stem_url(url):
        # if it's an academic link take the part before /publication
        if "academic" in url:
            url = url.split("/publication")[0]
        # strip protocols and 'www'
        url = re.sub(r"^https?:\/\/(www.)?", "", url)
        # strip trailing slashes
        url = re.sub(r"\/$", "", url)
        return url
    def sanitize_response(self, response):
        # run all the standard text response cleaning before stripping the URL down
        response['response'] = super(TextQuestion, self).sanitize_response(response['response'])
        response['response'] = response['response'].lower()
        response['response'] = self.stem_url(response['response'])
        return response
    def valid_response(self, response) :
        if not response.get('response', False):
            return False
        return validators.url(response.get('response', False), public = True)

class CommentQuestion(TextQuestion) :
    typeName = 'comment'
    def validate(self, response, module_responses):
        return True

class ImageUploadQuestion(TextQuestion) :
    typeName = 'imageupload'
    def sanitize_response(self, response):
        resp=response['response']
        try:
            image=resp[resp.index('base64,')+7:]
            decoded = io.BytesIO(base64.b64decode(image))
            response['response']="imagehash:"+str(imagehash.average_hash(Image.open(decoded)))
            response['response_raw']=resp
        except:            
            print('Could not decode image %s' % response['varname'])
        return response
    def validate(self, response, module_responses):
        resp=response['response']
        try:
            image=resp[resp.index('base64,')+7:]
            decoded = io.BytesIO(base64.b64decode(image))
        except:            
            return False
        return True
    def getBonusValue(self,response):
        #get image hash       
        return imagehash.hex_to_hash(response[len("imagehash:"):])


"""
class AbstractMultiQType(Question) :
    def __init__(self, varname=None, text=None, valuetype=None, options=[]) :
        Question.__init__(self, varname, text, valuetype)
        self.options = options
    @classmethod
    def from_dict(cls, text, d) :
        return cls(text, d['options'])
    def to_dict(self) :
        return {'options' : self.options}

class RadioQType(AbstractMultiQType) :
    typeName = "radio"
class CheckboxQType(AbstractMultiQType) :
    typeName = "checkbox"
class SelectQType(AbstractMultiQType) :
    typeName = "select"

class ScaleQType(Question) :
    typeName = "scale"
    def __init__(self, text, scalecont, scalemin, scalemax, scalestep):
        Question.__init__(self, text)
        self.scalecont = scalecont
        self.scalemin = scalemin
        self.scalemax = scalemax
        self.scalestep = scalestep
    @classmethod
    def from_dict(cls, text, d) :
        return cls(text,
                   scalecont=d['scalecont'],
                   scalemin=d['scalemin'],
                   scalemax=d['scalemax'],
                   scalestep=d['scalestep'])
    def to_dict(self) :
        return { 'scalecont' : self.scalecont,
                 'scalemin' : self.scalemin,
                 'scalemax' : self.scalemax,
                 'scalestep' : self.scalestep }

class TextQType(Question) :
    typeName = "text"
    def __init__(self, text, textlength):
        Question.__init__(self, text)
        self.textlength = textlength
    @classmethod
    def from_dict(cls, text, d) :
        return cls(text,
                   textlength=d['textlength'])
    def to_dict(self) :
        return { 'textlength' : self.textlength }

class GridQType(Question) :
    typeName = "grid"
    def __init__(self, text, rowoptions, coloptions):
        Question.__init__(self, text)
        self.rowoptions = rowoptions
        self.coloptions = coloptions
    @classmethod
    def from_dict(cls, text, d) :
        return cls(text,
                   rowoptions=d['rowoptions'],
                   coloptions=d['coloptions'])
    def to_dict(self) :
        return { 'rowoptions' : self.rowoptions,
                 'coloptions' : self.coloptions }

"""

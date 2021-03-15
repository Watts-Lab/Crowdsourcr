from .question import Question

class CType(object) :
    def __init__(self, name=None, header=None, contentUpdate=None,isomorphicModule=None, questions=[]) :
        self.name = name
        self.header = header
        self.contentUpdate=contentUpdate
        self.isomorphicModule = isomorphicModule
        self.questions = questions
    @classmethod
    def from_dict(cls, d) :       
        return CType(d['name'], d['header'], d['contentUpdate'],d['isomorphicModule'],[Question.deserialize(q) for q in d['questions']])
    def to_dict(self) :
        return {'name' : self.name,
                'header' : self.header,
                'contentUpdate': self.contentUpdate,
                'isomorphicModule' : self.isomorphicModule,
                'questions' : [q.serialize() for q in self.questions]}
    def evaluate_conditions(self, response_info={}):
        worker_conditions = {}
        for workerid, responses in response_info.items():
            worker_conditions[workerid] = {q.varname : q.satisfies_condition(responses) for q in self.questions}
        return worker_conditions

    def sanitize_response(self, response) :
        questions = {q.varname : q for q in self.questions}

        sanitize_response = response
        module_responses = sanitize_response['responses']
        extra_responses=[]
        for r in module_responses :
            r = questions[r['varname']].sanitize_response(r) 
            if "response_raw" in r:
                extra_responses.append({'varname':r['varname']+'_raw','response':r['response_raw']})
        for extra in extra_responses:
            sanitize_response['responses'].append(extra)         
        return sanitize_response
                
    def validate(self, response) :
        """Validates a response for this module as given by JSON from the client."""
        questions = {q.varname : q for q in self.questions}
        valids = set()
        module_responses = response['responses']
        for r in module_responses :
            if r.get('varname', None) not in questions :
                return False
            if not questions[r['varname']].validate(r, module_responses) :
                return False
            valids.add(r['varname'])
        if valids != set(questions.keys()) :
            return False
        return True


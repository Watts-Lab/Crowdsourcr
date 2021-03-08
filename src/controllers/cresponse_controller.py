import tornado.escape
import pymongo
from models import CResponse, CType, SET
from helpers import CustomEncoder, Lexer, Status
import jsonpickle

class CResponseController(object):
    def __init__(self, db):
        self.db = db
        #self.db.cresponses.ensure_index([('taskid', 1), ('workerid', 1)],
        #                                unique=True)
    def create(self, d):
        cresponse = CResponse.deserialize(d)
        self.db.cresponses.insert(cresponse.serialize())
        return cresponse
    def append_completed_task_info(self, **d) :
        d['num_completed_tasks'] = self.db.cresponses.count()
        return d
    def get_reponse_info_by_worker(self, workerid):
        d = self.db.cresponses.find({'workerid' : workerid})
        return {'count' : len(d) }
    def get_hits_for_worker(self, workerid):
        d = self.db.cresponses.find({'workerid' : workerid}, {'hitid' : 1})
        return [r['hitid'] for r in d]
    def write_response_to_csv(self, csvwriter, completed_workers=[]) :
        for d in self.db.cresponses.find() :
            if d['workerid'] in completed_workers :
                csvwriter.writerow([d['hitid'], d['taskid'], d['workerid'], str(d['submitted']),
                                    tornado.escape.json_encode(d['response'])])
    def write_task_submission_times_to_csv(self, csvwriter, completed_workers=[]) :
        csvwriter.writerow(['hitid', 'taskid', 'workerid', 'submitted_at'])
        #for d in self.db.cresponses.find().sort("submitted",pymongo.ASCENDING) :
        for d in self.db.cresponses.find() :
            if d['workerid'] in completed_workers :
                csvwriter.writerow([d['hitid'], d['taskid'], d['workerid'], str(d['submitted'])])
    def write_question_responses_to_csv(self, csvwriter, completed_workers=[]) :
        csvwriter.writerow(['hitid', 'taskid', 'workerid', 'module', 'varname', 'response'])
        #for d in self.db.cresponses.find().sort("submitted",pymongo.ASCENDING) :
        for d in self.db.cresponses.find() :
            if d['workerid'] in completed_workers :
                for module in d['response']:
                    for question_response in module['responses']:
                        response_string = question_response.get('response', None)
                        if response_string is not None:
                            response_string = response_string.encode("utf8")
                        csvwriter.writerow([d['hitid'], d['taskid'], d['workerid'], module['name'],
                                            question_response['varname'],
                                            response_string])

    def getBonusDetails(self,moduleVarnameValuetype={}):
        #cycle through hits
        crosswalk={} # format taskid -> module -> varname -> {"possibleWorkers":set(),"actualWorkers":dict(),"bonus":{}}
        d=self.db.chits.find({},{'tasks':1,'taskconditions':1,'completed_hits':1,'hitid':1})
        for row in d:
            hitid=row['hitid']
            tasks=row['tasks']
            taskconditions=row['taskconditions']
            for completed_hit in row['completed_hits']:
                workerid=completed_hit["worker_id"]
                #now we cycle through tasks
                for i,task in enumerate(tasks):
                    includeTask=False
                    couldBeReached=False
                    if taskconditions[i]==None:
                        includeTask=True
                    else:
                        #check the task condition
                        condition=jsonpickle.decode(taskconditions[i])
                        allVariables=dict()
                        has_error=False
                        for v in condition.varlist:
                            if v=="$workerid":
                                allVariables["$workerid"]=workerid
                            else:
                                frags=v.split('*')
                                if len(frags)!=3:
                                    has_error=True
                                else:
                                    docs = self.db.cresponses.find({"$and":[{'workerid' : workerid},{'hitid' : hitid},{'taskid':frags[0]}]}).sort('submitted')
                                    lastDoc=None
                                    for d in docs:
                                        lastDoc=d
                                    if lastDoc!=None:
                                        response=lastDoc["response"]
                                        for module in response:
                                            if module["name"]==frags[1]:
                                                for q in module["responses"]:
                                                    if q["varname"]==frags[2] and ("response" in q):
                                                        allVariables[v]=q["response"]
                                                        if q["response"] not in moduleVarnameValuetype[module["name"]][q["varname"]]["aprioripermissable"]:
                                                            couldBeReached=True
                        allSets=dict()
                        for s in condition.setlist:
                            allSets[s]=SET(self.db,s)
                        if has_error:
                            continue
                        else:
                            status=Status()
                            if condition.check_conditions(allVariables, allSets, status):
                                #this task was shown to the worker
                                includeTask=True
                    #check if task was reached or could have been reached
                    if includeTask or couldBeReached:
                        if task not in crosswalk:
                            crosswalk[task]={}
                        #now cycle through the modules and variables
                        m=self.db.ctasks.find_one({'taskid':task},{'modules':1})
                        r=self.db.cresponses.find_one({'taskid':task,'hitid':hitid,'workerid':workerid},{'response':1})
                        for module in m["modules"]:
                            if module not in crosswalk[task]:
                                crosswalk[task][module]={}
                            #now find questions for this module
                            d = self.db.ctypes.find_one({'name' : module})
                            mod=CType.from_dict(d)
                            for q in mod.questions:
                                if q.bonuspoints==0:
                                    continue
                                includedQuestionOrReachable=False
                                if q.varname not in crosswalk[task][module]:
                                    crosswalk[task][module][q.varname]={'possibleWorkers':set(),'actualWorkers':{},'bonus':q.get_bonus()}
                                if r!=None and ('response' in r):
                                    #find the correct module
                                    for qr in r['response']:
                                        if qr['name']==module:
                                            if q.satisfies_condition(qr['responses']):
                                                for vr in qr['responses']:
                                                    if vr['varname']==q.varname:
                                                        crosswalk[task][module][q.varname]['actualWorkers'][workerid]=q.getBonusValue(vr['response'])
                                            includedQuestionOrReachable=q.satisfies_condition(qr['responses'],moduleVarnameValuetype[module])
                                else:
                                    includedQuestionOrReachable=True
                                if includedQuestionOrReachable:
                                    crosswalk[task][module][q.varname]['possibleWorkers'].add(workerid)
        return crosswalk

    def sanitize_response(self, taskid, response, task_controller, module_controller):
        task = task_controller.get_task_by_id(taskid)

        cleaned_responses = []
        for m in response :
            module = module_controller.get_by_name(m['name'])
            cleaned_responses.append(module.sanitize_response(m))
        return cleaned_responses

    def validate(self, taskid, response, task_controller, module_controller) :
        task = task_controller.get_task_by_id(taskid)

        received_modules = set(m['name'] for m in response)
        required_modules = set(task.modules)
        if received_modules != required_modules :
            return False

        for m in response :
            module = module_controller.get_by_name(m['name'])
            if not module.validate(m) :
                return False
        return True

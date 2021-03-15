import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import datetime
import calendar
import email.utils
import os
import uuid
import pymongo
import Settings
import models
import controllers
import json
import helpers
import urllib
import csv
import io
import app_config
from io import BytesIO
from zipfile import ZipFile
from helpers import CountryTools


from tornado.options import define, options
from helpers import CustomEncoder, Lexer, Status
import jsonpickle

class BaseHandler(tornado.web.RequestHandler):

    @property
    def logging(self) :
        return self.application.logging
    @property
    def db(self) :
        return self.application.db
    @property
    def currentstatus_controller(self):
        return self.application.currentstatus_controller
    @property
    def ctype_controller(self):
        return self.application.ctype_controller
    @property
    def ctask_controller(self):
        return self.application.ctask_controller
    @property
    def admin_controller(self) :
        return self.application.admin_controller
    @property
    def chit_controller(self):
        return self.application.chit_controller
    @property
    def set_controller(self):
        return self.application.set_controller
    @property
    def cdocument_controller(self):
        return self.application.cdocument_controller
    @property
    def xmltask_controller(self):
        return self.application.xmltask_controller
    @property
    def cresponse_controller(self):
        return self.application.cresponse_controller
    @property
    def mturkconnection_controller(self):
        return self.application.mturkconnection_controller
    @property
    def event_controller(self):
        return self.application.event_controller
    @property
    def main_hit_url(self) :
        return "http://" + self.request.host + "/HIT"
    def is_super_admin(self):
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        return admin_email in app_config.superadmins
    def get_current_admin(self):
        admin = self.admin_controller.get_by_email(tornado.escape.to_unicode(self.get_secure_cookie("admin_email")))
    def return_json(self, data):
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps(data, indent = 4, sort_keys = True))

class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html")

class CTypeViewHandler(BaseHandler):
    def get(self, type_name):
        ctype_info = self.ctype_controller.get_by_name(type_name).to_dict()
        self.return_json(ctype_info)

class CTypeAllHandler(BaseHandler):
    def get(self):
        self.return_json(self.ctype_controller.get_names())

class CTypeCreateHandler(BaseHandler):
    def post(self):
        ctype = self.ctype_controller.create(json.loads(self.get_argument("ctype", "{}")))

class CTaskViewHandler(BaseHandler):
    def get(self):
        self.return_json(self.ctask_controller.get_by_name('', ''))

class AdminCreateHandler(BaseHandler) :
    def post(self):
        if self.is_super_admin():
            admin = self.admin_controller.create(json.loads(self.get_argument("data", "{}")))
            self.return_json(admin.to_dict())
        else:
            self.write("error: unauthorized")

class AdminRemoveHandler(BaseHandler) :
    def post(self):
        if self.is_super_admin():
            self.admin_controller.remove(json.loads(self.get_argument("data", "{}")))
            self.return_json({"success" : True})
        else:
            self.write("error: unauthorized")

class AdminAllHandler(BaseHandler) :
    def get(self):
        if self.is_super_admin():
            self.return_json(self.admin_controller.get_emails())
        else:
            self.write("error")

class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
    async def get(self):
        protocol="http"
        if ('X-Forwarded-Proto' in self.request.headers):
            protocol=self.request.headers['X-Forwarded-Proto']
        if self.get_argument('code', False):
            redirect_uri=protocol+"://"+self.request.host+self.application.settings['login_url']
            access = await self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'))
            user = await self.oauth2_request("https://www.googleapis.com/oauth2/v1/userinfo", access_token=access["access_token"])
            if self.admin_controller.get_by_email(user['email']):
                self.set_secure_cookie('admin_email', user['email'])
                self.set_secure_cookie('admin_name', user['name'])
            self.redirect('/admin/')
        else:
            redirect_uri=protocol+"://"+self.request.host+self.application.settings['login_url']
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=app_config.google['client_id'],
                client_secret=app_config.google['client_secret'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'prompt': 'select_account'})

class LogoutHandler(BaseHandler) :
    def get(self):
        self.clear_cookie('admin_email')
        self.clear_cookie('admin_name')
        self.redirect('/admin/')

class XMLUploadHandler(BaseHandler):
    def post(self):
        if not self.request.files :
            self.return_json({'error' : "Error: No file selected."});
            return
        try :
            with open(os.path.join(Settings.TMP_PATH, uuid.uuid4().hex + '.upload'), 'wb') as temp:
                temp.write(self.request.files['file'][0]['body'])
                temp.flush()
                uploadedFilename = self.request.files['file'][0]['filename']
                xmltask = self.xmltask_controller.xml_process(temp.name)
                if len(list(xmltask.get_modules()))==0:
                    self.return_json({'error' : "Error: Survey has no modules."})
                    return
                if len(list(xmltask.get_tasks()))==0:
                    self.return_json({'error' : "Error: Survey has no tasks."})
                    return
                if len(list(xmltask.get_hits()))==0:
                    self.return_json({'error' : "Error: Survey has no cHits."})
                    return
                if len(list(xmltask.docs.items()))==0:
                    self.return_json({'error' : "Error: Survey has no docs."})
                    return
                self.xmltask_controller.dropDB()
                self.event_controller.add_event("Uploaded: " + uploadedFilename)
                #keep a list of isomorphic modules and tasks
                isoModules=dict()
                isoTasks=dict()
                isoTaskModules=dict()
                for module in xmltask.get_modules():
                    if "isomorphicModule" in module:
                        if module["isomorphicModule"]!=None:
                            m1=module["name"]
                            m2=module["isomorphicModule"]
                            if m1 not in isoModules:
                                isoModules[m1]=set()
                            if m2 not in isoModules:
                                isoModules[m2]=set()
                            isoModules[m1].add(m2)
                            isoModules[m2].add(m1)
                    self.ctype_controller.create(module)
                for task in xmltask.get_tasks():
                    if "isomorphicTask" in task:
                        if task["isomorphicTask"]!=None:
                            isoTasks[task["taskid"]]=task["isomorphicTask"]
                    isoTaskModules[task["taskid"]]=task["modules"]
                    self.ctask_controller.create(task)
                for hit in xmltask.get_hits():
                    self.chit_controller.create(hit)
                for sset in xmltask.get_sets():
                    self.set_controller.create(sset)
                for name, doc in xmltask.docs.items():
                    self.cdocument_controller.create(name, doc)
                #now check if isomorphic tasks make sense
                for taskid in isoTaskModules:
                    if taskid in isoTasks:
                        mappedTaskId=isoTasks[taskid]
                        if len(isoTaskModules[taskid])!=len(isoTaskModules[mappedTaskId]):
                            raise Exception("task "+taskid+ " is not isomorphic to task "+mappedTaskId+" : different module count")
                        for i in range(len(isoTaskModules[taskid])):
                            m1=isoTaskModules[taskid][i]
                            m2=isoTaskModules[mappedTaskId][i]
                            #make sure m1 and m2 are isomorphic
                            lastTouched={m1}
                            alreadyTouched={m1}
                            mappedModule=False
                            while True:
                                nextLastTouched=set()
                                for m3 in lastTouched:                                    
                                    if m3 not in isoModules:
                                        continue
                                    if m2 in isoModules[m3]:
                                        mappedModule=True
                                        break
                                    for m4 in isoModules[m3]:
                                        if m4 not in alreadyTouched:
                                            alreadyTouched.add(m4)
                                            nextLastTouched.add(m4)
                                if mappedModule:
                                    break
                                if len(nextLastTouched)==0:
                                    break
                                lastTouched=nextLastTouched
                            if not mappedModule:
                                raise Exception("task "+taskid+ " is not isomorphic to task "+mappedTaskId+" : module "+m1+" is not isomorphic with module "+m2)
            self.return_json({'success' : True})
        except Exception as x :
            self.return_json({'error' : type(x).__name__ + ": " + str(x)})
            raise

class DocumentViewHandler(BaseHandler):
    def get(self, name):
        try :
            self.finish(self.cdocument_controller.get_document_by_name(name))
        except :
            raise tornado.web.HTTPError(404)

class RecruitingBeginHandler(BaseHandler):
    async def post(self):
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        max_assignments = self.chit_controller.get_agg_hit_info()['num_hits']
        if admin_email:
            self.event_controller.add_event(admin_email + " began run")
            await self.mturkconnection_controller.begin_run_async(email=admin_email,
                                                      max_assignments=max_assignments,
                                                      url=self.main_hit_url,
                                                      environment=self.settings['environment'])
        self.finish()

class RecruitingEndHandler(BaseHandler):
    async def post(self):
        #TODO: validate experimenter
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        if not admin_email :
            return
        tkconn = self.mturkconnection_controller.get_by_email(admin_email)
        if tkconn :
            if hasattr(tkconn,"hitid"):
                self.event_controller.add_event(admin_email + " ending run " + tkconn.hitid)
            else:
                self.event_controller.add_event(admin_email + " ending run")
            #create crosswalk: module/varname/valuetype
            moduleVarnameValuetype=self.ctype_controller.getModuleVarnameValuetype()
            #find isoTasks
            isoTasks=self.ctask_controller.getIsoTasks()
            #find isoModules
            isoModules=self.ctype_controller.getIsoModules()
            #create crosswalk: task/module/variable/workers
            bonusDetails=self.cresponse_controller.getBonusDetails(moduleVarnameValuetype,isoTasks,isoModules)
            #worker/possible bonus points
            possible_bonus_points = self.chit_controller.getMaxBonusPoints()
            #now calculate raw bonus points
            worker_bonus_info =  helpers.calculate_worker_bonus_info(possible_bonus_points, bonusDetails, moduleVarnameValuetype)
            self.db.bonus_info.drop()
            for wid, info in worker_bonus_info.items() :
                self.db.bonus_info.insert({'workerid' : wid,
                                           'percent' : info['pct'],
                                           'explanation' : info['exp'],
                                           'possible' : info['poss'],
                                           'earned' : info['earn'],
                                           'rawpct' : info['rawpct'],
                                           'best' : info['best']})
            # if the following is set to True crowdsourcer will normalize the
            # bonus of the best performer for 100% and scale up all other
            # bonuses proportionally
            grade_on_a_curve = False
            if grade_on_a_curve:
                bonus_pct = 'pct'
            else:
                bonus_pct = 'rawpct'
            worker_bonus_percent = { wid : info[bonus_pct]
                                     for wid, info in worker_bonus_info.items() }
            await self.mturkconnection_controller.end_run_async(email=admin_email,
                                                    bonus=worker_bonus_percent,
                                                    environment=self.settings['environment'])
            self.event_controller.add_event("Run ended")
            self.finish()

class BonusInfoHandler(BaseHandler) :
    ''' Quick hack put together to serve bonus info. '''
    def get(self) :
        self.set_header ('Content-Type', 'text/json')
        self.set_header ('Content-Disposition', 'attachment; filename=bonusinfo.json')
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        if admin_email and self.admin_controller.get_by_email(admin_email) :
            bi = self.db.bonus_info.find()
            pb = self.db.paid_bonus.find()
            resp = {d['workerid'] :
                    {'percent' : d['percent'],
                     'explanation' : d['explanation'],
                     'possible' : d['possible'],
                     'earned' : d['earned'],
                     'raw percent' : d['rawpct'],
                     'best percent' : d['best'],
                     'paid on mturk' : False,
                     'payment info' : {}}
                    for d in bi}
            total_workers = 0
            total_bonuses = 0
            connection_info = self.db.mturkconnections.find()[0]
            for d in pb :
                total_workers += 1
                total_bonuses += d['amount']
                wrk_info = resp.setdefault(d['workerid'], {})
                wrk_info['paid on mturk'] = True
                wrk_info['payment info'] = {'percent' : d['percent'],
                                            'amount' : d['amount'],
                                            'assignmentid' : d['assignmentid']}

            resp['Payment summary'] = {'Title': connection_info['title'],
                                        'HITID': connection_info['hitid'],
                                        'HIT Payment': connection_info['hitpayment'],
                                        'Bonus Payment': connection_info['bonus'],
                                        'Workers paid': total_workers,
                                        'Total task payments:': total_workers * connection_info['hitpayment'],
                                        'Total bonus payments:': total_bonuses,
                                        'Total overall payments:': total_bonuses + total_workers * connection_info['hitpayment']}
            self.return_json(resp)
        else :
            self.return_json([])

class RecruitingInfoHandler(BaseHandler):
    def post(self):
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        errorList=[]
        if admin_email:
            recruiting_info = json.loads(self.get_argument('data', '{}'))
            recruiting_info['email'] = admin_email
            recruiting_info['environment'] = self.settings['environment']
            #check locales
            ct=CountryTools()
            locales_check=ct.checkList(recruiting_info['locales'])
            if locales_check!=None:
                errorList.append(locales_check)
            try:
                lt=int(recruiting_info['lifetime'])
                if lt<2*3600:
                    errorList.append("HIT lifetime has to be at least 2 hours.")
            except ValueError:
                errorList.append("Workers min. percent approved has to be an integer between 0 and 100.")
            try:
                pc=int(recruiting_info['pcapproved'])
                if pc<0 or pc>100:
                    errorList.append("Workers min. percent approved has to be an integer between 0 and 100.")
            except ValueError:
                errorList.append("Workers min. percent approved has to be an integer between 0 and 100.")
            try:
                mincompleted=int(recruiting_info['mincompleted'])
                if mincompleted<0:
                    errorList.append("Workers min. completed HITs has to be a non-negative integer.")
            except ValueError:
                errorList.append("Workers min. completed HITs has to be a non-negative integer.")
            if len(errorList)==0:
                mtconn = self.mturkconnection_controller.create(recruiting_info)
        if len(errorList)==0:
            self.finish()
        else:
            self.finish({"errors":errorList})

class AdminInfoHandler(BaseHandler):
    async def get(self):
        admin_email= tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        if not admin_email:
            self.return_json({'authed' : False, 'reason' : 'no_login'})
        if not self.admin_controller.get_by_email(admin_email):
            self.return_json({'authed' : False, 'reason' : 'not_admin'})
        else :
            turk_conn = self.mturkconnection_controller.get_by_email(email=admin_email,
                                                                     environment=self.settings['environment'])
            turk_info = False
            turk_balance = False
            hit_info = self.chit_controller.get_agg_hit_info()
            hit_info = self.cresponse_controller.append_completed_task_info(**hit_info)
            if turk_conn:
                balance = await turk_conn.get_balance_async()
                turk_balance = str(balance or '')
                turk_info = turk_conn.serialize()
                self._send_json(hit_info, turk_info, turk_balance)
            else :
                self._send_json(hit_info, turk_info, turk_balance)
    def _send_json(self, hit_info, turk_info, turk_balance) :
        completed_hits = self.chit_controller.get_completed_hits()
        outstanding_hits = self.currentstatus_controller.outstanding_hits()
        self.return_json({'authed' : True,
                          'environment' : self.settings['environment'],
                          'email' : tornado.escape.to_unicode(self.get_secure_cookie('admin_email')),
                          'full_name' : tornado.escape.to_unicode(self.get_secure_cookie('admin_name')),
                          'superadmin' : self.is_super_admin(),
                          'hitinfo' : hit_info,
                          'hitstatus' : {'outstanding' : outstanding_hits,
                                         'completed' : completed_hits},
                          'events' : [{'date' : email.utils.formatdate(calendar.timegm(e['date'].utctimetuple()),
                                                                       usegmt=True),
                                       'event' : e['event']}
                                      for e in self.event_controller.get_events()[-8:]],
                          'turkinfo' : turk_info,
                          'turkbalance' : turk_balance})

class AdminHitInfoHandler(BaseHandler):
    def get(self, id=None) :
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        if admin_email and self.admin_controller.get_by_email(admin_email):
            if id == None :
                ids = self.chit_controller.get_chit_ids()
                self.return_json({'ids' : ids})
            else :
                chit = self.chit_controller.get_chit_by_id(id)
                self.return_json({'tasks' : chit.tasks})
        else :
            self.return_json({'authed' : False})

class AdminTaskInfoHandler(BaseHandler):
    def get(self, tid) :
        admin_email = tornado.escape.to_unicode(self.get_secure_cookie('admin_email'))
        if admin_email and self.admin_controller.get_by_email(admin_email):
            task = self.ctask_controller.get_task_by_id(tid)
            modules = self.ctype_controller.get_by_names(task.modules)
            self.return_json({
                "task" : task.serialize(),
                "modules" : {name : module.to_dict() for name, module in modules.items()}
            })
        else :
            self.return_json(False)

class WorkerLoginHandler(BaseHandler):
    def post(self):
        self.set_secure_cookie('workerid', self.get_argument('workerid', '').strip().upper())
        self.finish()

class CHITViewHandler(BaseHandler):
    def post(self):
        forced = False
        workerid = tornado.escape.to_unicode(self.get_secure_cookie('workerid'))
        if self.get_argument('force', False) : # for letting admin see a particular hit
            forced = True
            hitid = self.get_argument('hitid', None)
            workerid = self.get_argument('workerid', None)
            self.set_secure_cookie('workerid', workerid)
            self.currentstatus_controller.create_or_update(workerid=workerid,
                                                           hitid=hitid,
                                                           taskindex=0)
        if not workerid :
            if forced :
                self.return_json({'needs_login' : True, 'reforce' : True})
            elif self.chit_controller.get_next_chit_id() == None :
                self.return_json({'no_hits' : True})
            else:
                self.return_json({'needs_login' : True})
        else :
            existing_status = self.currentstatus_controller.get_current_status(workerid)
            chit = self.chit_controller.get_chit_by_id(existing_status['hitid']) if existing_status != None else None
            if chit:
                taskindex = existing_status['taskindex']
                hitid = existing_status['hitid']
                if taskindex >= len(chit.tasks):
                    self.clear_cookie('workerid')
                    completed_chit_info = self.chit_controller.add_completed_hit(chit=chit, worker_id=workerid)
                    self.currentstatus_controller.remove(workerid)
                    self.return_json({'completed_hit':True,
                                      'verify_code' : completed_chit_info['turk_verify_code']})
                else:
                    task = self.ctask_controller.get_task_by_id(chit.tasks[taskindex])
                    modules = self.ctype_controller.get_by_names(task.modules)
                    self.currentstatus_controller.create_or_update(workerid=workerid,
                                                                   hitid=hitid,
                                                                   taskindex = taskindex)
                    self.return_json({"task" : task.serialize(),
                                      "modules" : {name : module.to_dict() for name, module in modules.items()},
                                      "task_num" : taskindex,
                                      "num_tasks" : len(chit.tasks)})
            else:
                completed_hits = self.cresponse_controller.get_hits_for_worker(workerid)
                outstanding_hits = self.currentstatus_controller.outstanding_hits()
                sh = self.db.workerpings.find().sort([('lastping',1)])
                stale_hits = [s for s in sh if self.chit_controller.get_chit_by_id(s['hitid'])]
                nexthit = self.chit_controller.get_next_chit_id(exclusions=completed_hits, workerid=workerid, outstanding_hits=outstanding_hits, stale_hits=stale_hits)
                if nexthit == None :
                    self.logging.info('no next hit')
                    #self.clear_cookie('workerid')
                    self.return_json({'no_hits' : True,
                                      'unfinished_hits' : self.chit_controller.has_available_hits()})
                else :
                    self.currentstatus_controller.create_or_update(workerid=workerid,
                                                                   hitid=nexthit,
                                                                   taskindex=0)
                    self.return_json({'reload_for_first_task':True})

class WorkerPingHandler(BaseHandler) :
    def post(self) :
        workerid = tornado.escape.to_unicode(self.get_secure_cookie('workerid'))
        existing_status = self.currentstatus_controller.get_current_status(workerid)
        if existing_status :
            self.db.workerpings.update({'hitid' : existing_status['hitid']},
                                       {'hitid' : existing_status['hitid'],
                                        'lastping' : datetime.datetime.utcnow()},
                                       True)
        self.finish()

# https://workersandbox.mturk.com/mturk/continue?hitId=2CQU98JHSTLB3ZGMPO0IRBJEK6HQEE
class CHITReturnHandler(BaseHandler):
    def get(self):
        workerid = tornado.escape.to_unicode(self.get_secure_cookie('workerid'))
        mthitid = self.mturkconnection_controller.get_hit_id()
        if workerid :
            self.currentstatus_controller.remove(workerid)
        redir_subdomain = 'www' if self.settings['environment'] == 'production' else 'workersandbox'
        redir_url = 'https://%s.mturk.com/mturk/myhits' % redir_subdomain
        self.clear_cookie('workerid')
        self.redirect(redir_url)

class Set():
    def __init__(self,db,name):
        self.db=db
        self.name=name

    def hasMember(self,value):
        rows = self.db.sets.find({"$and":[{'name' : self.name},{'member' : str(value)}]})
        member=None
        for m in rows:
            member=m
        if member==None:
            return False
        else:
            return True

class CResponseHandler(BaseHandler):
    def post(self):
        worker_id = tornado.escape.to_unicode(self.get_secure_cookie('workerid'))
        existing_status = self.currentstatus_controller.get_current_status(worker_id)
        if not existing_status:
            if not worker_id :
                return self.return_json({'error' : True,
                                         'explanation' : 'no_cookies'})
            else :
                return self.return_json({'error' : True,
                                         'explanation' : 'not_logged_in'})
        else:
            response = json.loads(self.get_argument('data', '{}'))

            hitid = existing_status['hitid']
            chit = self.chit_controller.get_chit_by_id(hitid)
            #print(chit.serialize())
            taskindex = existing_status['taskindex']
            taskid = chit.tasks[taskindex]
            #task = self.ctask_controller.get_task_by_id(taskid)

            valid = self.cresponse_controller.validate(taskid, response,
                                                       self.ctask_controller,
                                                       self.ctype_controller)
            if not valid :
                return self.return_json({'error' : True,
                                         'explanation' : 'invalid_response'})

            # sanitize the response
            response = self.cresponse_controller.sanitize_response(taskid, response,
                                                                   self.ctask_controller,
                                                                   self.ctype_controller)


            self.logging.info("%s submitted response for task_index %d on HIT %s" % (worker_id, taskindex, hitid))
            self.cresponse_controller.create({'submitted' : datetime.datetime.utcnow(),
                                              'response' : response,
                                              'workerid' : worker_id,
                                              'hitid' : chit.hitid,
                                              'taskid' : taskid})
            #check if there is a taskcondition set
            skip=1
            while taskindex+skip<len(chit.taskconditions):
                oldSkip=skip
                if chit.taskconditions[taskindex+skip]!=None:
                    #let's check the condition
                    condition=jsonpickle.decode(chit.taskconditions[taskindex+skip])
                    allVariables=dict()
                    has_error=False
                    for v in condition.varlist:
                        if v=="$workerid":
                            allVariables["$workerid"]=worker_id
                        else:
                            frags=v.split('*')
                            if len(frags)!=3:
                                has_error=True
                            else:
                                docs = self.db.cresponses.find({"$and":[{'workerid' : worker_id},{'hitid' : chit.hitid},{'taskid':frags[0]}]}).sort('submitted')
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

                    allSets=dict()
                    for s in condition.setlist:
                        allSets[s]=self.set_controller.get_set_members(s)
                    if has_error:
                        skip+=1
                    else:
                        status=Status()
                        if not condition.check_conditions(allVariables, allSets, status):
                            skip+=1
                if skip==oldSkip:
                   break;
            self.currentstatus_controller.create_or_update(workerid=worker_id,
                                                           hitid=hitid,
                                                           taskindex=taskindex+skip)
            self.finish()

class CSVDownloadHandler(BaseHandler):
    def get(self):
        """
        takes all completed hits and puts together two tab-separated files:
        - task_submission_times.tsv: contains timestamps at which tasks were submitted
        - question_responses.tsv: contains the responses to all questions
        """
        completed_workers = self.chit_controller.get_workers_with_completed_hits()

        task_submission_times_output = io.StringIO()
        task_submission_times_csvwriter = csv.writer(task_submission_times_output, delimiter='\t')
        self.cresponse_controller.write_task_submission_times_to_csv(task_submission_times_csvwriter, completed_workers=completed_workers)

        question_responses_output = io.StringIO()
        question_responses_csvwriter = csv.writer(question_responses_output, delimiter='\t')
        self.cresponse_controller.write_question_responses_to_csv(question_responses_csvwriter, completed_workers=completed_workers)

        zip_name = "data.zip"
        f = BytesIO()
        with ZipFile(f, "w") as zf:
            zf.writestr('task_submission_times.tsv', task_submission_times_output.getvalue())
            zf.writestr('question_responses.tsv', question_responses_output.getvalue())

        self.set_header('Content-Type', 'application/zip')
        self.set_header("Content-Disposition", "attachment; filename={}".format(zip_name))

        self.finish(f.getvalue())

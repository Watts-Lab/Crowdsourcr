import uuid
from models import CHIT
import bson.code
import datetime

class CHITController(object):
    sum_map = bson.code.Code("function() { emit(1, this.num_completed_hits); }")
    sum_reduce = bson.code.Code("function(key, vals) { return Array.sum(vals); }")
    task_sum_map = bson.code.Code("function() { emit(1, this.tasks.length); }")

    def __init__(self, db):
        self.db = db
        self.db.chits.ensure_index('hitid', unique=True)
    def create(self, d):
        chit = CHIT.deserialize(d)
        self.db.chits.insert(chit.serialize())
        return chit
    def get_chit_by_id(self, hitid):
        d = self.db.chits.find_one({'hitid' : hitid})
        return CHIT.deserialize(d) if d else None
    def has_available_hits(self) :
        d = self.db.chits.find_one({'num_completed_hits' : {'$lt' : 1}})
        return True if d else False
    def get_next_chit_id(self, exclusions=[], workerid=None, outstanding_hits=[], stale_hits=[]):
        #cl = self.db.chitloads.find({'hitid' : {'$exists' : True}}, {'hitid' : 1})
        #loaded_chits = [c['hitid'] for c in cl] if cl else []
        ct = datetime.datetime.utcnow()
        min_seconds = 30.0
        print outstanding_hits
        d = self.db.chits.find_one({'$and' : 
                                    [{ 'num_completed_hits' : {'$lt' : 1} },
                                     { 'exclusions' : {'$nin' : exclusions}},
                                     { 'hitid' : {'$nin' : outstanding_hits} } ] },
                                   {'hitid' : 1})
        if not d:
            for sh in stale_hits :
                if (ct - sh['lastping']).total_seconds() > min_seconds : 
                    d = self.db.chits.find_one({'$and' : 
                                                [{ 'num_completed_hits' : {'$lt' : 1} },
                                                 { 'exclusions' : {'$nin' : exclusions}},
                                                 { 'hitid' : sh['hitid']} ]},
                                               {'hitid' : 1})
                    if d :
                        break
                
                
                
        if d and workerid :
            self.db.chitloads.insert({'workerid' : workerid,
                                      'time' : datetime.datetime.utcnow(),
                                      'hitid' : d['hitid']})

        return d['hitid'] if d else None
    def get_chit_ids(self) :
        ds = self.db.chits.find({}, {'hitid' : True})
        return [d['hitid'] for d in ds]
    def get_agg_hit_info(self):
        completed_hits_mr = self.db.chits.map_reduce(self.sum_map, self.sum_reduce, "chit_mapreducesum_results")
        num_completed_hits = completed_hits_mr.find_one()
        all_tasks_mr = self.db.chits.map_reduce(self.task_sum_map, self.sum_reduce, "chit_task_mapreducesum_results")
        num_tasks = all_tasks_mr.find_one()
        num_total_hits = self.db.chits.count()
        return {'num_completed_hits' : num_completed_hits['value'] if num_completed_hits else 0,
                'num_hits' : num_total_hits,
                'num_tasks' : num_tasks['value'] if num_tasks else 0}
    def add_completed_hit(self,chit=None, worker_id=None):
        hit_info = {'worker_id' : worker_id,
                    'turk_verify_code' : uuid.uuid4().hex[:16]}
        self.db.chits.update({'hitid' : chit.hitid},
                             {'$push' : {'completed_hits' : hit_info},
                              '$inc' : {'num_completed_hits' : 1}})
        return hit_info
    def get_completed_hits(self) :
        d = self.db.chits.find({'num_completed_hits' : {'$gte' : 1}}, {'hitid' : 1})
        return [r['hitid'] for r in d]
    def get_workers_with_completed_hits(self) :
        d = self.db.chits.find({'num_completed_hits' : {'$gte' : 1}}, {'completed_hits' : 1})
        worker_ids = set()
        for r in d:
            for hit in r['completed_hits']:
                worker_ids.add(hit['worker_id'])
        return worker_ids
    # static wasn't working ... ?
    # utility method called by MTurkConnecitonController.make_payments
    @classmethod
    def secret_code_matches(cls, db=None, worker_id=None, secret_code=None):
        hit_info = {'worker_id' : worker_id,
                    'turk_verify_code' : secret_code}
        lower_hit_info = {'worker_id' : worker_id.lower(),
                          'turk_verify_code' : secret_code}
        either_hit_info = [hit_info, lower_hit_info]
        #ugly hack. TODO: improve storage struture for easier searching
        d = db.chits.find_one({'$and' : 
                               [{'num_completed_hits' : {"$gte" : 1}},
                                {'completed_hits' : {'$in' : either_hit_info}}]})
        return True if d else False

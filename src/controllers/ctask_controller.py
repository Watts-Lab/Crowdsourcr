from models import CTask

class CTaskController(object):
    def __init__(self, db):
        self.db = db
        self.db.ctasks.ensure_index('taskid', unique=True)
    def create(self, d):
        ctask = CTask.deserialize(d)
        self.db.ctasks.insert(ctask.serialize())
        return ctask
    def get_task_ids(self) :
        return [r['taskid'] for r in self.db.ctasks.find({}, {'taskid' : 1})]
    def get_task_count(self) :
        return self.db.ctasks.count()
    def get_task_by_id(self, taskid):
        d = self.db.ctasks.find_one({'taskid' : taskid})
        ctask = CTask.deserialize(d)
        return ctask
    def getIsoTasks(self):
        isoTasks=dict()
        d=self.db.ctasks.find({},{'taskid':1,'isomorphicTask':1})
        for row in d:
            if "isomorphicTask" in row:
                if row["isomorphicTask"]!=None:
                    t1=row["taskid"]
                    t2=row["isomorphicTask"]
                    if t1 not in isoTasks:
                        isoTasks[t1]=set()
                    if t2 not in isoTasks:
                        isoTasks[t2]=set()
                    isoTasks[t1].add(t2)
                    isoTasks[t2].add(t1)
        #now we augment tasks to make sets complete (including indirect maps)
        augmentedIsoTasks=dict()
        for task in isoTasks:
            augmentedIsoTasks[task]=set()
            alreadyTouched={task}
            lastTouched={task}
            while True:
                newLastTouched=set()
                for lastT in lastTouched:
                    for nextT in isoTasks[lastT]:
                        if nextT not in alreadyTouched:
                            augmentedIsoTasks[task].add(nextT)
                            newLastTouched.add(nextT)
                            alreadyTouched.add(nextT)
                if len(newLastTouched)==0:
                    break
                lastTouched=newLastTouched
        return augmentedIsoTasks


"""
class CTaskController(object) :
    def __init__(self, db) :
        self.db = db
        self.db.ctasks.ensure_index([('type_name', 1), ('name', 1)],
                                    unique=True)
    def get_names(self, type_name) :
        res = self.db.ctasks.find({'type_name' : type_name}, {'name' : True})
        return [r['name'] for r in res]
    def get_by_name(self, type_name, name) :
        d = self.db.ctasks.find_one({'type_name' : type_name,
                                     'name' : name})
        return CTask.from_dict(d)
    def set_live(self, task, is_live) :
        task.live = is_live
        self.db.ctasks.update({'type_name' : task.type_name,
                               'name' : task.name},
                              {'$set' : {'live' : task.live}})
        return task
    def create(self, ctype, name, content, live=False) :
        c = CTask(type_name=ctype.name,
                  created=datetime.datetime.now(),
                  responses=[],
                  name=name,
                  content=content,
                  live=live)
        self.db.ctasks.insert(c.to_dict())
        return c
    def add_response(self, task, worker_name, response) :
        r = CResponse(submitted=datetime.datetime.now(),
                     response=response,
                     worker_name=worker_name)
        self.db.ctasks.update({'type_name' : task.type_name,
                               'name' : task.name},
                              {'$push' : {'responses' : r.to_dict()}})
        return r
"""

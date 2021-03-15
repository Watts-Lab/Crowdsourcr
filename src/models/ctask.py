
class CTask(object):
    def __init__(self, taskid=None, content=None,isomorphicTask=None, modules=[]):
        self.taskid = taskid
        self.content = content
        self.isomorphicTask=isomorphicTask
        self.modules = modules
    @classmethod
    def deserialize(cls, d):
        return cls(d['taskid'], d['content'],d['isomorphicTask'], d['modules'])
    def serialize(self):
        return {'taskid' : self.taskid,
                'content' : self.content,
                'isomorphicTask':self.isomorphicTask,
                'modules' : self.modules}




"""
class CTask(object) :
    def __init__(self, type_name=None, created=None, responses=None, name=None, content=None, live=False) :
        self.type_name = type_name
        self.created = created
        self.responses = responses
        self.name = name
        self.content = content
        self.live = live
    @classmethod
    def from_dict(cls, d) :
        return CTask(type_name=d['type_name'],
                     created=d['created'],
                     responses=d.get('responses', None),
                     name=d['name'],
                     content=d['content'],
                     live=d['live'])
    def to_dict(self) :
        return {'type_name' : self.type_name,
                'created' : self.created,
                'responses' : self.responses or [],
                'name' : self.name,
                'content' : self.content,
                'live' : self.live}

"""

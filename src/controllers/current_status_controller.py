
class CurrentStatusController(object):
    def __init__(self, db):
        self.db = db
        self.db.currentstatus.create_index('workerid', unique=True)
    def outstanding_hits(self) :
        d = self.db.currentstatus.find({}, {'hitid' : 1})
        return [r['hitid'] for r in d]
    def create_or_update(self, workerid=None, hitid=None, taskindex=None) :
        self.db.currentstatus.update({'workerid' : workerid},
                                     {'workerid' : workerid,
                                      'hitid' : hitid,
                                      'taskindex' : taskindex},
                                     True)
    def remove(self, workerid=None):
        self.db.currentstatus.remove({'workerid' : workerid})
    def get_current_status(self, workerid=None):
        if not workerid :
            return None
        d = self.db.currentstatus.find_one({'workerid' : workerid})
        return d if d else None

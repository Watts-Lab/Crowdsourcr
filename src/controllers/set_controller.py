from models import SET

class SetController(object):
    def __init__(self, db):
        self.db = db
        self.db.sets.create_index('name', unique=False)
    def create(self, d):
        set = SET.deserialize(d)
        self.db.sets.insert_one(set.serialize())
        return set
    def get_sets_names(self) :
        return [r['name'] for r in self.db.sets.find({}, {'name' : 1})]
    def get_set_count(self) :
        return self.db.sets.count()
    def get_set_by_name(self, name):
        d = self.db.ctasks.find_one({'name' : name})
        set = SET.deserialize(d)
        return set
    def get_set_members(self,name):
        return [r['member'] for r in self.db.sets.find({'name':name})]

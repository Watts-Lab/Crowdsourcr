
class SET(object):
    def __init__(self, name=None, member=None):
        self.name = name
        self.member = member
    @classmethod
    def deserialize(cls, d):
        return cls(**d);
    def serialize(self):
        return {'name' : self.name,
                'member' : self.member}
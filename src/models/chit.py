
class CHIT(object):
    def __init__(
        self,
        hitid=None,
        exclusions=[],
        tasks=[],
        validCondition=None,
        invalidRetries=0,
        taskconditions=[],
        completed_hits=[],
        completed_hits_validation_notpassed=[],
        num_completed_hits=0,
        num_completed_hits_validation_notpassed=0,
        num_extra_assignments=0,
        num_pending_extra_assignments=0,
        pending_extra_assignments=[],
        **kwargs
    ):
        self.hitid = hitid
        self.tasks = tasks
        self.validCondition=validCondition
        self.invalidRetries=invalidRetries
        self.taskconditions=taskconditions
        self.completed_hits = completed_hits
        self.completed_hits_validation_notpassed=completed_hits_validation_notpassed
        self.exclusions = exclusions
        self.num_completed_hits = num_completed_hits
        self.num_completed_hits_validation_notpassed = num_completed_hits_validation_notpassed
        self.num_extra_assignments = num_extra_assignments
        self.num_pending_extra_assignments = num_pending_extra_assignments
        self.pending_extra_assignments = pending_extra_assignments
    @classmethod
    def deserialize(cls, d):
        return cls(**d)
    def serialize(self):
        return {'hitid' : self.hitid,
                'tasks' : self.tasks,
                'validCondition':self.validCondition,
                'invalidRetries':self.invalidRetries,
				'taskconditions': self.taskconditions,
                'exclusions' : self.exclusions,
                'completed_hits' : self.completed_hits,
                'completed_hits_validation_notpassed':self.completed_hits_validation_notpassed,
                'num_completed_hits' : len(self.completed_hits),
                'num_completed_hits_validation_notpassed' : len(self.completed_hits_validation_notpassed),
                'num_extra_assignments': self.num_extra_assignments,
                'num_pending_extra_assignments': self.num_pending_extra_assignments,
                'pending_extra_assignments': self.pending_extra_assignments}

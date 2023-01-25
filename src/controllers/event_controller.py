import datetime

class EventController(object):
    """Keeps track of a basic event log."""
    def __init__(self, db):
        self.db = db
    def add_event(self, event) :
        """'Event' is just a string."""
        event = str(event)
        self.db.events.insert_one({'date' : datetime.datetime.utcnow(),
                               'event' : event})
    def get_events(self) :
        return list(self.db.events.find().sort("date"))

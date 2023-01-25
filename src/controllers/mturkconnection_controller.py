from models import MTurkConnection


class MTurkConnectionController(object):
    def __init__(self, db):
        self.db = db
        self.db.mturkconnections.create_index('email', unique=True)

    def create(self, d):
        mtconn = MTurkConnection(**d)
        self.update(mtconn)
        return mtconn
        
    def update(self, mtconn):
        # self.db.mturkconnections.update({'email' : mtconn.email}, 
        #                                 {'$set' : mtconn.serialize()},
        #                                 upsert=True )
        self.db.mturkconnections.update({}, 
                                        {'$set' : mtconn.serialize()},
                                        upsert=True )
        print(mtconn.serialize())

    def get_hit_id(self) :
        d = self.db.mturkconnections.find_one({})
        return d['hitid'] if d else None

    def get_by_email(self, email=None, environment="development"):
        #d = self.db.mturkconnections.find_one({'email' : email})
        d = self.db.mturkconnections.find_one({})
        if not d:
            return None
        else:
            d['email'] = email
            d['environment']=environment
            return MTurkConnection.deserialize(d)

    async def begin_run_async(self, email=None, max_assignments=1, url="", environment="development"):
        mt_conn = self.get_by_email(email=email, environment=environment)
        is_authed = await mt_conn.try_auth() if mt_conn else False
        if is_authed and await mt_conn.begin_run_async(max_assignments=max_assignments, url=url):
            self.update(mt_conn)

    async def end_run_async(self, email=None, bonus={}, environment="development") :
        mt_conn = self.get_by_email(email=email, environment=environment)
        ap_sel = self.db.paid_bonus.find()
        already_paid = [a['workerid'] for a in ap_sel]
        paid_bonus = await mt_conn.end_run_async(bonus=bonus, already_paid=already_paid)
        for pb_info in paid_bonus :
            self.db.paid_bonus.insert_one(pb_info)
        self.update(mt_conn)

    def get_all(self, environment="development"):
        d = self.db.mturkconnections.find()
        if d :
            for c in d:
                c['environment']=environment
                mtconn = MTurkConnection.deserialize(c)
                yield mtconn
        
    def make_payments(self, email=None, environment="development"):
        from controllers import CHITController
        if email != None:
            mt_conn = self.get_by_email(email=email,
                                        environment=environment)
            submitted_assignments = mt_conn.get_payments_to_make()
            mt_conn.make_payments(assignment_ids=[a[0] for a in submitted_assignments if CHITController.secret_code_matches(db=self.db,worker_id=a[1], secret_code=a[2])])
        else:
            for mt_conn in self.get_all(environment=environment):
                submitted_assignments = mt_conn.get_payments_to_make()
                mt_conn.make_payments(assignment_ids=[a[0] for a in submitted_assignments if CHITController.secret_code_matches(db=self.db,worker_id=a[1], secret_code=a[2].strip())])

    def add_assignment(self, extra_assignments=0, email=None, environment="development"):
        mt_conn = self.get_by_email(email=email, environment=environment)
        mt_conn.add_assignment(extra_assignments=extra_assignments)
            

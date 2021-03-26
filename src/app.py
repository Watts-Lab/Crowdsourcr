import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import pymongo
import uuid
import base64
import hashlib
import os
import sys
import traceback
import asyncio

import Settings

from tornado.options import define, options
 
define('config', default="config.json", help="JSON file with config parameters such as Google authentication, AWS mTurl parameters, port, environ., and database", type=str)
define('environment', default="development", help="server environment", type=str)
define('drop', default="", help="pass REALLYREALLY to drop the db", type=str)
define('daemonize', default=False, help="set whether this process should run as a daemon (linux/unix-only)", type=bool)

sys.path.insert(0, Settings.CONFIG_PATH)
import app_config
sys.path.pop(0)

import controllers
import handlers

def random256() :
    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
 
class Application(tornado.web.Application):
    def __init__(self, drop):
        self.db = pymongo.MongoClient()[app_config.db_name]
        if drop == "REALLYREALLY" :
            pymongo.MongoClient().drop_database(app_config.db_name)        
            print("Cleared.")
            sys.exit(0)

        settings = {
            "template_path":Settings.TEMPLATE_PATH,
            "static_path":Settings.STATIC_PATH,
            "doc_path":Settings.DOC_PATH,
            "debug":Settings.DEBUG,
            "cookie_secret": Settings.COOKIE_SECRET,
            "root_path": Settings.ROOT_PATH,
            "login_url": "/admin/login/",
            "environment" : app_config.environment,
            "google_oauth" :{"key": app_config.google['client_id'], "secret": app_config.google['client_secret']}           
        }

        app_handlers = [
            #(r'/', handlers.MainHandler),
            (r'/', tornado.web.RedirectHandler, {"url" : "/doc"}),
            (r'/doc/(.*)', tornado.web.StaticFileHandler, dict(path=settings['doc_path'], default_filename='index.html')),
#            (r'/help/(README.md)', tornado.web.StaticFileHandler, dict(path=settings['root_path'], default_filename='README.md')),
#            (r'/types/?()', tornado.web.StaticFileHandler, dict(path=settings['static_path'], default_filename='types.html')),
#            (r'/types/new/?', handlers.CTypeCreateHandler),
#            (r'/types/all/?', handlers.CTypeAllHandler),
            (r'/types/view/(.*)', handlers.CTypeViewHandler),
            (r'/admin/?()', tornado.web.StaticFileHandler, dict(path=settings['static_path'], default_filename='admin.html')),
            (r'/admin/login/?', handlers.GoogleLoginHandler),
            (r'/admin/logout/?', handlers.LogoutHandler),
            (r'/admin/download/?', handlers.CSVDownloadHandler),
            (r'/admin/recruit/?', handlers.RecruitingInfoHandler),
            (r'/admin/recruit/end/?', handlers.RecruitingEndHandler),
            (r'/admin/recruit/begin/?', handlers.RecruitingBeginHandler),
            (r'/admin/all/?', handlers.AdminAllHandler),
            (r'/admin/new/?', handlers.AdminCreateHandler),
            (r'/admin/remove/?', handlers.AdminRemoveHandler),
            (r'/admin/info/?', handlers.AdminInfoHandler),
            (r'/admin/hits/?', handlers.AdminHitInfoHandler),
            (r'/admin/bonusinfo/?', handlers.BonusInfoHandler),
            (r'/admin/hits/(.+)', handlers.AdminHitInfoHandler),
            (r'/admin/tasks/(.+)', handlers.AdminTaskInfoHandler),
            (r'/superadmin/?()', tornado.web.StaticFileHandler, dict(path=settings['static_path'], default_filename='superadmin.html')),
            (r'/admin/xmlupload/?', handlers.XMLUploadHandler),
            (r'/document/(.+)', handlers.DocumentViewHandler),
            (r'/HIT/?()', tornado.web.StaticFileHandler, dict(path=settings['static_path'], default_filename='hit.html')),
            (r'/HIT/view/?', handlers.CHITViewHandler),
            (r'/HIT/submit/?', handlers.CResponseHandler),
            (r'/HIT/return/?', handlers.CHITReturnHandler),
            (r'/worker/login/?', handlers.WorkerLoginHandler),
            (r'/worker/ping/?', handlers.WorkerPingHandler),
            (r'.*()', tornado.web.StaticFileHandler, dict(path=settings['static_path'], default_filename='404.html'))
        ]
        tornado.web.Application.__init__(self, app_handlers, **settings)

        self.currentstatus_controller = controllers.CurrentStatusController(self.db)
        self.ctype_controller = controllers.CTypeController(self.db)
        self.ctask_controller = controllers.CTaskController(self.db)
        self.admin_controller = controllers.AdminController(self.db)
        self.chit_controller = controllers.CHITController(self.db)
        self.set_controller = controllers.SetController(self.db)
        self.cdocument_controller = controllers.CDocumentController(self.db)
        self.xmltask_controller = controllers.XMLTaskController(self.db)
        self.cresponse_controller = controllers.CResponseController(self.db)
        self.mturkconnection_controller = controllers.MTurkConnectionController(self.db)
        self.event_controller = controllers.EventController(self.db)

        if app_config.make_payments :
            self.ensure_automatic_make_payments()

        self.add_extra_assignments()
    
    @property
    def logging(self) :
        return Settings.logging

    def ensure_automatic_make_payments(self) :
        """Adds an automatic payer to the ioloop."""

        def _ensure() :
            self.logging.info(u"Ensuring automatic payments")
            def callback() :
                self.logging.info("Attempting automatic paighments.")
                try :
                    self.mturkconnection_controller.make_payments(environment=self.settings['environment'])
                    self.logging.info(u"Peiment su\x01\x02e\u00df")
                except :
                    self.logging.exception("Error in automatic payer.")
                    #pc.stop()
            callback_time = 1000 * 10 # 10 seconds
            pc = tornado.ioloop.PeriodicCallback(callback, callback_time)
            pc.start()
        # run this from the main ioloop just in case we have multiple threads
        tornado.ioloop.IOLoop.instance().add_callback(_ensure)

    def add_extra_assignments(self) :
        def _addAssignments() :
            def callback() :
                #now loop through pending assignments
                extra_assignments=self.hit_controller.convert_pending_to_extra()
                self.logging.info(u"adding "+extra_assignments+" extra assignments")
                if extra_assignments>0:
                    self.mturkconnection_controller.add_assignment(extra_assignments=extra_assignments,
                                                      environment=self.settings['environment'])
            callback_time = 30 # 30 seconds
            pc = tornado.ioloop.PeriodicCallback(callback, callback_time)
            pc.start()
        # run this from the main ioloop just in case we have multiple threads
        tornado.ioloop.IOLoop.instance().add_callback(_addAssignments)


def start() :
    application = Application(drop=options.drop)
    http_server = tornado.httpserver.HTTPServer(application)
    try :
        http_server.listen(app_config.port)
    except :
        traceback.print_exc()
        os._exit(1) # since it otherwise hangs
    Settings.logging.info("Started news_crowdsourcer in %s mode." % app_config.environment)
    ioloop = tornado.ioloop.IOLoop.instance()
    try :
        ioloop.start()
    except :
        ioloop.add_callback(lambda : ioloop.stop())
        

def start_as_daemon() :
    import daemon
    import pid
    log_file = 'tornado.%s.log' % app_config.port
    log = open(os.path.join(Settings.LOG_PATH, log_file), 'a+')
    pidfile_path = os.path.join(Settings.PIDFILE_PATH, '%d.pid' % app_config.port)
    pid.check(pidfile_path)
    with daemon.DaemonContext(stdout=log, stderr=log, working_directory='.') :
        pid.write(pidfile_path)
        try :
            start()
        except Exception as err :
            Settings.logging.exception("Main ioloop exception, removing pid")
            Settings.logging.exception("Exited from: %s" % err)
            Settings.logging.exception(traceback.format_exc())
            Settings.logging.info(" * * * EXITING DUE TO ERROR * * * ")
        else :
            Settings.logging.info(" * * * EXITING NORMALLY * * * ")
        pid.remove(pidfile_path)

def main():
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    tornado.options.parse_command_line()
    app_config.populate_config(options.config)
    if options.daemonize :
        start_as_daemon()
    else :
        start()

if __name__ == "__main__":
    main()

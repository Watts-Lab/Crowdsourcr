import os
import errno

DEBUG = False # sets tornado debug mode. don't use when using command line arguments
DIRNAME = os.path.dirname(__file__)
ROOT_PATH = os.path.join(DIRNAME, '..')
STATIC_PATH = os.path.join(DIRNAME, '..', 'static')
DOC_PATH = os.path.join(DIRNAME, '..', 'doc')
TEMPLATE_PATH = os.path.join(DIRNAME, '..', 'template')
TMP_PATH = os.path.join(DIRNAME, '..', 'tmp')
LOG_PATH = os.path.join(DIRNAME, '..', 'log')
PIDFILE_PATH = os.path.join(DIRNAME, '..', 'pid')
CONFIG_PATH = os.path.join(DIRNAME, '..', 'config')
DOC_PATH = os.path.join(DIRNAME, '..', 'doc')

try :
    os.makedirs(TMP_PATH)
except OSError as x :
    if x.errno != errno.EEXIST :
        raise

import logging
import sys
#log linked to the standard error stream
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)-8s - %(message)s',
                    datefmt='%d/%m/%Y %Hh%Mm%Ss')
console = logging.StreamHandler(sys.stderr)
 
#import base64
#import uuid
#base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
COOKIE_SECRET = 'L8LwECiNRxq2N0N2eGxx9MZlrpmuMEimlydNX/vt1LM='

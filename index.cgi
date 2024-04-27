#!/home/rasheen88/anaconda3/bin/python
import sys, os

sys.path.insert(0, "/home/rasheen88/anaconda3/bin/python")

os.environ['DJANGO_SETTINGS_MODULE'] = "xserver.settings"

from wsgiref.handlers import CGIHandler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
CGIHandler().run(application)
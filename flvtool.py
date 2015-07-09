#!/usr/bin/python

from pprint import pprint as pp
import sys
import os
from snlib.flv import inspect_flv

#if (len(sys.argv) < 2) or not os.path.exists(sys.argv[1]):
#	print("need a file"); sys.exit();

#(4.0, 640.0, 480.0, 111.878, 29.969985961914062)
for filename in sys.argv[1:]:
    t, w, h, dur, rate = inspect_flv( filename )
    types = { 2:'Flash7', 4:'Flash8' }
    exts  = { 2:'flv7', 4:'flv' }
    type  = types[ int(t) ]
    ext   = exts[ int(t) ]
    
    print '%s %3dx%3d %4.1f secs %0.2f fps %4s -- mv "%s" %dx%d.%s' % ( type, w, h, dur, rate, ext, filename, w, h, ext )
    #print 'mv "%s" "%s.%s"' % ( filename, os.path.basename(filename), ext )
    

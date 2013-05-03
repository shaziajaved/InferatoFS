#Common utilities for FS

import inferatoFS, os, shutil, sys

def clean(arg, dir, files):
    for x in files:
        if str(x).endswith(inferatoFS.FSTemplates._suffix):
            os.remove(os.path.join(dir, x))

if len(sys.argv) < 2:
    print "Please, specify a path to clean"
    
else:
    if os.path.exists(sys.argv[1]):
        m = sys.argv[1] + os.sep + inferatoFS.FSTemplates._meta_storage
        if os.path.exists(m):
            shutil.rmtree(m)
        os.path.walk(sys.argv[1], clean, "")
        print "Cleaning is done"
    else:
        print "no such directory '" + sys.argv[1] + "'"

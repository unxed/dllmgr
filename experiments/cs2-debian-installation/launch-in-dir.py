import os,sys
os.chdir(sys.argv[1])
os.execvpe('wine',['wine',sys.argv[2],*sys.argv[3:]],os.environ)

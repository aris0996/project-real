     import sys
     import logging
     logging.basicConfig(stream=sys.stderr)
     sys.path.insert(0, "/home/arisdev/public_html/w-management")

     from main import app as application
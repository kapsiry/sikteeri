import logging 
import sys 

logger = logging.getLogger('') 
logger.setLevel(logging.DEBUG) 

handler = logging.StreamHandler(sys.stderr) 
handler.setLevel(logging.DEBUG) 

formatter = logging.Formatter('%(levelname)-8s: %(message)s') 

handler.setFormatter(formatter) 
logger.addHandler(handler)

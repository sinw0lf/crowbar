
try:
	import logging
	import os.path
except ImportError,e:
	import sys
	sys.stdout.write("%s\n" %e)
	sys.exit(1)

	
class Logger:

	def __init__(self, log_file, output_file):
	  
	  
		self.logger_log = logging.getLogger('log_file')
		self.logger_log.setLevel(logging.INFO)
     
		handler_log = logging.FileHandler(os.path.join(".", log_file),"a", encoding = None, delay = "true")
		handler_log.setLevel(logging.INFO)
		formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
		handler_log.setFormatter(formatter)
		self.logger_log.addHandler(handler_log)

		
		self.logger_output = logging.getLogger('output_file')
		self.logger_output.setLevel(logging.INFO)
     
		handler_out = logging.FileHandler(os.path.join(".", output_file),"a", encoding = None, delay = "true")
		handler_out.setLevel(logging.INFO)
		formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
		handler_out.setFormatter(formatter)
		self.logger_output.addHandler(handler_out)

		consoleHandler = logging.StreamHandler()
		consoleHandler.setFormatter(formatter)
		self.logger_output.addHandler(consoleHandler)
		
		
		
	def log_file(self , message):
		
		self.logger_log.critical(message)

    
	def output_file(self, message):
		
		self.logger_output.critical(message)

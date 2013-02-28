#!/usr/bin/python
##############################################################################
#
# NAME:        ph4CmdRunner.py
#
# COPYRIGHT:
#         Copyright (c) 2012, Dusan (ph4r05) Klinec
#         Licensed under the GPL 3.0
#         http://www.gnu.org/copyleft/gpl.html
#         This software is provided "as is", without warranties
#         or conditions of any kind, either express or implied.
#
# DESCRIPTION:
#
#         Backup script
#
# AUTHORS:     Dusan (ph4r05) Klinec
#
# CREATED:     23-Sep-2012
#
# NOTES:
#
# MODIFIED:

##############################################################################
import time
import shlex
import subprocess
import sys
import os
from threading import Thread
#from subprocess import Popen, PIPE
#import sys
#import os
#import socket
#import re
#from itertools import chain
#from random import random

class ph4CmdRunner(Thread):
    """Thread class helping to dump all traffic from/to specified client on
    specified ports. One tcpDumper should be created for one daemon"""
    
    running = True
    
    cmd = None
    pid = -1
    retcode = None
    stdout = None
    stderr = None
    haveFileNames = False
    fstdout = None
    fstderr = None
    stderr2stdout=False
    finishCallback = None
    startCallback = None
    callbackKey = None
    blocking=False
    ended=False
    
    datDir = None
    datFile= None
    
    pythonVersion = None
    
    # process
    p = None
    
    PROCESS_ENDED=0
    PROCESS_KILLED=1
    PROCESS_STARTED=2
    
    def __init__(self, cmd, stdout=None, stderr=None, finishCallback=None, startCallback=None, callbackKey=None, stdsAreFileNames=False, blocking=False):
        """Initialize one CmdRunner"""
        Thread.__init__(self)
        
        self.cmd = shlex.split(cmd)
        self.fstdout = stdout
        self.fstderr = stderr
        self.finishCallback = finishCallback
        self.startCallback = startCallback
        self.callbackKey = callbackKey
        self.haveFileNames = stdsAreFileNames
        self.blocking = blocking
        self.pythonVersion = sys.version_info
        
        if self.haveFileNames: 
            self.stderr=None
            self.stdout=None
            if self.fstdout == self.fstderr:
                self.stderr2stdout=True
        else: 
            self.stdout = stdout
            self.stderr = stderr
            if self.stdout == self.stderr:
                self.stderr2stdout=True
        
    def stoprun(self):
        """Just stops waiting for proccess to end and finish process"""
        # stop this thread, flush
        self.running=False
    
    def _openIfNeeded(self):
        """Opens stdout and stderr files if passed filenames"""
        if self.haveFileNames:
            if self.fstdout:
                try:
                    self.stdout = open(self.fstdout, 'w')
                except Exception, exc:
                    print "##\tCannot open stdout file: ", exc
                    self.stdout = None
                            
            if self.fstderr and self.fstdout != self.fstderr:
                try:
                    self.stderr = open(self.fstderr, 'w')
                except Exception, exc:
                    print "##\tCannot open stderr file: ", exc
                    self.stderr = None
        pass
    
    def _closeIfNeeded(self):
        """Closes stdout and stderr if passed as filenames"""
        if self.haveFileNames:
            if self.stdout:
                try:
                    self.stdout.close()
                except Exception, inst:
                    print "##\tCannot properly close file; ", inst
                    
            if self.stderr:
                try:
                    self.stderr.close()
                except Exception, inst:
                    print "##\tCannot properly close file; ", inst
        pass
    
    def run(self):
        """Thread class entry point - code here starts in different thread"""
        return self._work()
    
    def work(self):
        """Entry point for starting running, if blocking was chosen, thread is not started."""
        if self.blocking:
            #print "##\tStarting blocking operation: %s" % self.cmd
            self._work()
        else:
            #print "##\tStarting non-blocking operation: %s " % self.cmd
            self.start()
        return 0
    
    def _work(self):   
        """Main worker method that starts process and watches for its ending""" 
        # open files if needed
        self._openIfNeeded()
        
        # start new process
        if self.stderr2stdout:
            self.p = subprocess.Popen(self.cmd, stderr=subprocess.STDOUT, stdout=self.stdout) # Success!
        else:
            self.p = subprocess.Popen(self.cmd, stderr=self.stderr, stdout=self.stdout) # Success!
        self.pid = self.p.pid
        if self.startCallback:
            self.startCallback(self.callbackKey, self.pid, self.retcode, self.PROCESS_STARTED)
        
        if self.blocking:
            try:
                self.p.communicate(None)
                self.retcode = self.p.returncode
            except Exception, inst:
                print "##\tCmd probably stopped already; ", inst
            self.ended=True
            self.running=False
            if self.finishCallback:
                self.finishCallback(self.callbackKey, self.pid, self.retcode, self.PROCESS_ENDED)
        else:
            while self.running==True:
                self.retcode = self.p.poll()
                if self.retcode!=None:
                    # process finished
                    self.ended=True
                    self.running=False
                    if self.finishCallback:
                        self.finishCallback(self.callbackKey, self.pid, self.retcode, self.PROCESS_ENDED)
                    pass
                    break
                pass
                time.sleep(1)
                
            # after end of running - stop tcpdump process
            try:
                if self.pythonVersion[0]==2 and self.pythonVersion[1]>=6:
                    # first terminate - use provided API
                    self.p.terminate()
                else:
                    # API not provided - needed to send KILL signal manually
                    os.system('/bin/kill -SIGTERM %d' % int(self.pid))
                    
                # wait for command result - not to have ZOMBIE processes
                self.p.wait()
                self.retcode = self.p.returncode
                #self.p.kill()
            except Exception, inst:
                print "\tCmd probably stopped already; ", inst
            self.ended=True
            
            if self.finishCallback:
                self.finishCallback(self.callbackKey, self.pid, self.retcode, self.PROCESS_KILLED)      
        
        # if we have filenames, we need to take care about closing streams
        self._closeIfNeeded()
        #print "##\tThread should be stopped now: %s" % self.cmd

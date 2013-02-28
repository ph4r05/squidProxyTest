#!/usr/bin/python
##############################################################################
#
# NAME:        ph4Utils.py
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
#         Misc utils/helpers
#
# AUTHORS:     Dusan (ph4r05) Klinec
#
# CREATED:     23-Sep-2012
#
# NOTES:
#
# MODIFIED:

##############################################################################

import os
import re
#import shlex
import time
from threading import Thread
from ph4backuplib.ph4CmdRunner import ph4CmdRunner

STRACEPATH='/usr/bin/strace'
class stracer:
    running = True
    
    datfile = None
    args = None
    runner = None
    blocking=False
    
    def __init__(self, pid, datfile, pidIsCmd=False, blocking=False):
        """Initialize one tailer now"""
        print "##\tInitialized stracer thread %s" % pid
        
        # build data dir
        self.datfile = datfile
        self.blocking = blocking
        
        # echo built arguments
        if pidIsCmd:
            self.args = STRACEPATH + ' -q -s 512 -v -o "%s" -- %s' % (self.datfile, pid)
        else:
            self.args = STRACEPATH + ' -q -s 512 -v -o "%s" -p %d' % (self.datfile, int(pid))
        #self.args = shlex.split(self.args)
        
    def stoprun(self):
        """Just stops waiting for tcpdump and finish process"""
        # stop this thread, flush
        self.running=False
        if self.runner:
            self.runner.stoprun()
        pass
    
    def run(self):        
        # start new strace process        
        self.runner = ph4CmdRunner(self.args, blocking=self.blocking)
        self.runner.work()

class rdiffStracer(Thread):
    """Class made to strace rdiff-backup processes and analyze its output"""
    stracers = {}
    finished = False
    running = False
    
    openRegex = r'open\("([^"]+)".*'
    statRegex = r'lstat\("([^"]+)".*'
    
    def __init__ (self):
        Thread.__init__(self)
        pass
    
    def attachRdiffAll(self, timex=300):
        """Attaches all running rdiffs, follows <time> seconds, then are detached"""
        # get all running processes
        proclist = procListHelper.getProcList()
        rdiffs = procListHelper.getProcMatchingRegex(proclist, r'.*rdiff-backup.*')
        for pidList in rdiffs:
            self.attachRdiffPid(pidList[0], pidList[1], timex)
        pass
    
    def attachRdiffPid(self, pid, procName='', timex=300):
        """Attaches strace to particular PID for <time> seconds."""
        datfile='/tmp/ph4backup-strace-%d-%d.log' % (time.time(), int(pid))
        cStracer = stracer(pid, datfile, pidIsCmd=False, blocking=False)
        self.stracers[pid] = {'datfile':datfile, 'stracer':cStracer, 'started': 0, 'stopped': 0, 
                              'state': 2, 'procName':procName, 'followTime':timex,
                              'pwdx': procListHelper.getPwdx(pid),
                              'output': (0, [], []) }
        pass
    
    def run(self):
        """Starts tracing of defined processes"""
        self.running = True
        
        # phase 1: attach
        for pid in self.stracers:
            if self.stracers[pid]['state']==2:
                # waiting for start -> launch it here
                self.stracers[pid]['started']=time.time()
                self.stracers[pid]['state']=1
                self.stracers[pid]['stracer'].run()
            pass
        pass
    
        # phase 2: follow
        endPhase2=True
        while True:
            timeNow = time.time()
            endPhase2=True
            
            # iterate over straces list - are there any straces still running?
            for pid in self.stracers:
                if self.stracers[pid]['state']==1:
                    runTime = timeNow - self.stracers[pid]['started']
                    if runTime >= self.stracers[pid]['followTime']:
                        # stop this tracer now
                        self.detachStrace(pid)
                    else:
                        # still need to be done
                        endPhase2=False
                    pass    
                pass
            pass
            
            # nothing to do now
            if endPhase2:
                break
            
            time.sleep(1)
        pass
        
        # phase 3: process outputs
        for pid in self.stracers:
            if self.stracers[pid]['state']!=0:
                continue
            self.stracers[pid]['output'] = self.processFile(self.stracers[pid]['datfile'])
        pass
        
        # phase 4: delete output files
        for pid in self.stracers:
            if self.stracers[pid]['state']!=0:
                continue
            try:
                os.unlink(self.stracers[pid]['datfile'])
            except Exception, exc:
                continue
        pass
        self.running = False
        self.finished = True
    
    def processFile(self, fname):
        """Processes strace output. Returns (numberOfLines, openList file names, lstat file names)"""
        try:
            lines = [line.strip() for line in open(fname)]
            
            openList = []
            statList = []
            for line in lines:
                # find interesting lines
                matchObj1 = re.match(self.openRegex, line, re.M|re.I)
                matchObj2 = re.match(self.statRegex, line, re.M|re.I)
            
                if matchObj1:
                    openList.append(matchObj1.group(1))
                if matchObj2:
                    statList.append(matchObj2.group(1))    
            
            # make set from list
            return(len(lines), list(set(openList)), list(set(statList)))
        except Exception:
            return (0, [], [])
    
    def detachAllStraces(self):
        """Detaches all straces commands"""
        for pid in self.stracers:
            self.detachStrace(pid)
        pass
    
    def detachStrace(self, pid):
        """Detaches particular strace for PID"""
        if not (pid in self.stracers):
            return
        
        # already detached?
        if self.stracers[pid]['state']!=1:
            return
        
        self.stracers[pid]['stracer'].stoprun()
        self.stracers[pid]['stopped'] = time.time()
        self.stracers[pid]['state'] = 0
        pass
    
    pass

class procListHelper:
    def __init__(self):
        pass
    
    @staticmethod
    def getProcList():
        data = [(int(p), c.strip()) for p, c in [x.rstrip('\n').split(' ', 1) for x in os.popen('ps h -eo pid:1,command')]]
        return data
    
    @staticmethod
    def getPwdx(pid):
        try:
            data = [(int(p.rstrip(':')), c.strip()) for p, c in [x.rstrip('\n').split(' ', 1) for x in os.popen('pwdx %d' % int(pid))]]
            return data[0][1]
        except Exception, exc:
            return ""
    
    @staticmethod
    def getProcMatchingRegex(proclist, pattern):
        retlist = []
        for rec in proclist:
            matchObj = re.match(pattern, rec[1], re.M|re.I)
            if matchObj:
                retlist.append(rec)
        return retlist
    
    @staticmethod
    def getProcMatching(proclist, string):
        string2 = string.stip().lower()
        retlist = []
        for rec in proclist:
            proc = rec[1].strip().lower()
            if proc == string2:
                retlist.append(rec)
        return retlist
    
    @staticmethod
    def proclist2pidlist(proclist):
        return [p for p,c in proclist]
    
    @staticmethod
    def getproclistDict(proclist):
        cdict={}
        for rec in proclist:
            cdict[rec[0]] = rec[1]
        return cdict
    
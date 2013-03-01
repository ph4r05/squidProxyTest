#!/usr/bin/python
##############################################################################
#
# NAME:        ph4BackupRunner.py
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
import sys
import time
import os.path
import os
import re
import copy
from threading import Thread
from optparse import OptionParser
import datetime
import smtplib
import traceback
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import formatdate
from squid_proxy_check.ph4CmdRunner import ph4CmdRunner
from squid_proxy_check.ph4Utils import rdiffStracer
from proxycheck import proxyhunter
import hashlib

__author__   = "Dusan Klinec (ph4r05)"
__date__    = "01/03/2013"
__version__    = "01"

class ph4SimpleProxyTesterRunner(Thread):
    """Main Worker thread - executes main logic in separate thread 
    from server listening socket thread"""
    
    running=True
    options = None
    args = None
    checker=None
    
    def __init__ (self):
        Thread.__init__(self)
        
        # options parser
        parser = OptionParser()
        parser.add_option('--proxy-source', dest='proxysrc', default=None, help="Source of proxy list to check")
        parser.add_option('--proxy-retry', dest='proxyretry', default=3, help="Retry count for proxy to consider fail [default : %default]")
        parser.add_option('--proxy-timeout', dest='proxytimeout', default=30, help="Number of seconds to wait for reply [default : %default]")
        parser.add_option('--proxy-refresh', dest='proxyrefresh', default=60*5, help="Refresh proxy list interval in seconds [default : %default]")
        parser.add_option('--proxy-testurl', dest='proxyurl', default='http://www.google.com', help="URL to test proxies [default : %default]")
        parser.add_option('--outputfile', dest='output', default='/tmp/proxytester-output', help="Output of proxy test [default : %default]")
        
        # parse args now
        self.options, self.args = parser.parse_args()
        self.checker = ph4SimpleProxyTester()
        self.checker.proxysrc = self.options.proxysrc
        self.checker.proxyretry = self.options.proxyretry
        self.checker.proxytimeout = self.options.proxytimeout
        self.checker.proxyrefresh = self.options.proxyrefresh
        self.checker.proxyurl = self.options.proxyurl
        self.checker.output = self.options.output
    pass

    def run(self):
        self.checker.run()

class ph4SimpleProxyTester(Thread):
    """Main Worker thread - executes main logic in separate thread 
    from server listening socket thread"""
    
    running=True
    args = None
    
    proxysrc = None
    proxyretry=3
    proxytimeout=30
    proxyrefresh=60*5
    output='/tmp/proxytester-output'
    proxyurl='http://www.google.com'
    
    def __init__ (self):
        Thread.__init__(self)
        
    def getUniqFileName(self):
        """Returns unique (should be) file name for rdiff-backup stdout"""
        return '/tmp/proxysquidtester-%d.log' % (int(time.time()))
    
    def configCheck(self):
        """Checks configuration validity"""
        if self.proxysrc == None or os.path.exists(self.proxysrc)==False:
            print "Error: something is wrong with proxy source"
            return 1
        return 0          
        
    def readProxyList(self):
        """
        Reads proxy list from proxy file
        """
        proxylist = []   
        try:
            preventstrokes = open(self.proxysrc, "r")
            proxylist      = preventstrokes.readlines()
            count          = 0 
            while count < len(proxylist): 
                proxylist[count] = proxylist[count].strip() 
                count += 1
            # remove commented entries
            for i,p in enumerate(copy.deepcopy(proxylist)):
                if re.match('^\s*#',p)!=None: proxylist.remove(p)
            # parse on elements
            newProxyList = []
            for p in proxylist:
                newProxyList.append([c.strip() for c in str(p).split(':', 4)])
            return newProxyList
        except(IOError): 
            print "\n[-] Error: Check your proxylist path\n"
            return -1
    
    def work(self):
        """
        Main working routine
        Here is the protocol:
        
        Repeat every <refresh> seconds:
        1. load new proxy configuration file
        2. test each proxy, filter out the good ones
        3. generate report
        """
        phaseStartTime = time.time()
        phaseStartDatetime = datetime.datetime.now()
        desc = ''
        
        problem2send= ''
        timeReported=False
        phaseCurTime = time.time()
        phaseCurDatetime = datetime.datetime.now()
        
        desc += "* Starting daemon on %s (sec: %s)\n" % (phaseStartDatetime.strftime("%Y-%m-%d %H:%M"), phaseStartTime)
        print desc
        
        prevHash = None
        while True:
            time.sleep(10)
            phunt = proxyhunter(OutputProxy='proxylist.txt', GoodProxy='goodproxylist.txt', 
                                Verbose=False, TimeOut=int(self.proxytimeout), 
                                Sitelist=[], RetryCount=int(self.proxyretry), 
                                TestUrl=self.proxyurl)
            curProxyList = self.readProxyList()
            
            md5 = hashlib.md5()
            md5.update(str(curProxyList))
            newHash = md5.hexdigest()
            if (newHash==prevHash):
                continue
            
            phaseStartDatetime = datetime.datetime.now()
            outDat = "* Starting check on %s (sec: %s)\n" % (phaseStartDatetime.strftime("%Y-%m-%d %H:%M"), phaseStartTime)
            prevHash=newHash
            for i,p in enumerate(copy.deepcopy(curProxyList)):
                tmpProxyName=''
                if len(p)==2:
                    tmpProxyName=str(p[0]) + ":" + str(p[1])
                elif len(p)==4:
                    tmpProxyName=str(p[2]) + ":" + str(p[3]) + "@" + str(p[0]) + ":" + str(p[1])
                else:
                    curProxyList.remove(p)
                    
                '''Proxy test and remove failures'''
                cProxyStart = time.time()
                cProxyRes = phunt.CoreFreshTester(tmpProxyName)
                cProxyTime = time.time()-cProxyStart 
                if cProxyRes:
                    outDat += "[*] %s \n \'--------------> Piece of Shit [%05.2f s]\n" % (tmpProxyName, cProxyTime)
                else:
                    outDat += "[*] %s \n \'--------------> We have a Good One [%05.2f s]\n" % (tmpProxyName, cProxyTime)
            pass
            print outDat
            
            '''Generate report'''
            try:
                tmpOutFileH = open(self.output, 'w')
                tmpOutFileH.write(outDat)
                tmpOutFileH.close()
            except Exception, e:
                print "Error during saving new configuration file: ", e
                continue
       
    def run(self):
        """Main runner method"""
        startTime = time.time()
        startDatetime = datetime.datetime.now()
        
        desc = "Starting proxy tester: %s (sec:%s)" % (startDatetime.strftime("%Y-%m-%d %H:%M"), startTime) 
        print desc
        if self.configCheck() > 0:
            print "Cannot continue, configuration error"
            sys.exit(1)
        
        try:
            # iterate over sources
            self.work()
            #print "Everything finished at %s !\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            #print "="*80
        except Exception, exc:
            print "Something very weird happened, exception in main body!"
            traceback.print_exc()
        pass



def main():
    print "\nSquid proxy testerv.%s by %s - Proxy Hunter and Tester Opensource engine\nA high-level cross-protocol proxy-hunter\n" % (__version__, __author__)
    engine = ph4SimpleProxyTesterRunner()
    engine.run()
                     
if __name__ == '__main__':
    main()

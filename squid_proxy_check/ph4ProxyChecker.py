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

__author__   = "Dusan Klinec (ph4r05)"
__date__    = "01/03/2013"
__version__    = "01"

class ph4ProxyCheckerRunner(Thread):
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
        parser.add_option('--squid-proxy-template', dest='squid_proxy_template', default=None, help="Template proxy configuration file for squid")
        parser.add_option('--squid-config-file', dest='squid_config_file', default=None, help="Where to place resulting squid configuration file")
        parser.add_option('--squid-reload-command', dest='squid_reload_command', default=None, help="Command to force Squid to refresh configuration")
        parser.add_option('--squid-path', dest='squid_path', default='/usr/sbin/squid', help="Path to squid binary [default : %default]")
        parser.add_option('--mail-test', dest='mailtest', default=None, help="Sends error mail to defined address")
        parser.add_option('--mail-dest', dest='maildest', default=None, help="Destionation of mail warnings")
        
        # parse args now
        self.options, self.args = parser.parse_args()
        self.checker = ph4ProxyChecker()
        self.checker.proxysrc = self.options.proxysrc
        self.checker.proxyretry = self.options.proxyretry
        self.checker.proxytimeout = self.options.proxytimeout
        self.checker.proxyrefresh = self.options.proxyrefresh
        self.checker.proxyurl = self.options.proxyurl
        self.checker.squid_proxy_template = self.options.squid_proxy_template
        self.checker.squid_config_file = self.options.squid_config_file
        self.checker.squid_reload_command = self.options.squid_reload_command
        self.checker.squid_path = self.options.squid_path
        self.checker.mailtest = self.options.mailtest
        self.checker.maildest = self.options.maildest
    pass

    def run(self):
        self.checker.run()

class ph4ProxyChecker(Thread):
    """Main Worker thread - executes main logic in separate thread 
    from server listening socket thread"""
    
    running=True
    args = None
    
    proxysrc = None
    proxyretry=3
    proxytimeout=30
    proxyrefresh=60*5
    proxyurl='http://www.google.com'
    squid_proxy_template=None
    squid_config_file=None
    squid_reload_command=None
    squid_path='/usr/sbin/squid'
    mailtest=None
    maildest=None
    
    def __init__ (self):
        Thread.__init__(self)
        
    def getUniqFileName(self):
        """Returns unique (should be) file name for rdiff-backup stdout"""
        return '/tmp/proxysquidchecker-%d.log' % (int(time.time()))
    
    def configCheck(self):
        """Checks configuration validity"""
        if self.proxysrc == None or os.path.exists(self.proxysrc)==False:
            print "Error: something is wrong with proxy source"
            return 1
        if self.squid_proxy_template == None or \
                os.path.exists(self.squid_proxy_template)==False or \
                ';' in self.squid_proxy_template or \
                ' ' in self.squid_proxy_template:
            print "Error: proxy squid template is missing"
            return 1
        if self.squid_config_file == None or \
                ';' in self.squid_config_file or \
                ' ' in self.squid_config_file:
            print "Error: squid config file parameter is missing"
            return 1
        if self.squid_reload_command == None:
            print "Error: squid reload command parameter is missing"
            return 1
        if self.squid_path == None or os.path.exists(self.squid_path)==False:
            print "Error: path to squid binary is invalid"
            return 1
        return 0
    
    def sendMail(self, to, subject, body):
        if to==None:
            return
        toText = to
        toEffective = [to]
        if type(to) == type([]):
            toText = ','.join(to)
            toEffective = to
        
        for to in toEffective:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = '%s@net-wings.eu' % "proxycheck"
            msg['To'] = toText
            msg['Date'] = formatdate(localtime=True)
            
            part1 = MIMEText(body, 'plain')
            #part2 = MIMEText(body, 'html') 
            msg.attach(part1)
            #msg.attach(part2)
            
            # Send the message via our own SMTP server, but don't include the
            # envelope header.
            s = smtplib.SMTP('89.29.122.41', '25')
            try:
                s.sendmail(msg['From'], to, msg.as_string())
                s.quit()
            except Exception, e:
                print "Unable to send email. Error: %s" % str(e)
            pass
        pass
    
    def mailTest(self, to):
        self.sendMail(to, "Ph4BackupLib mail test", "Message body here")
   
    def straceAll(self, timex):
        """Strace all running rdiff processes"""
        print "Starting stracers for: %s secs" % timex
        self.stracer = rdiffStracer()
        self.stracer.attachRdiffAll(timex)
        self.stracer.start()
        
        while True:
            time.sleep(1)
            
            try:
                if self.stracer != None and self.stracer.running==False and self.stracer.finished==True:
                    print "Finished!"
                    self.printRdiffStracerDump(self.stracer.stracers)
                    self.stracer=None
                    break
            except Exception, exc:
                print "Exception in straceAll: ", exc
                break 
    
    def proxyConfigTest(self, path2test):
        """
        Checks proxy configuration
        """
        tmpOutFile = self.getUniqFileName()
        cmd2run = self.squid_path + " -k parse -f " + path2test
        
        runner = ph4CmdRunner(cmd2run, tmpOutFile, tmpOutFile, stdsAreFileNames=True, blocking=True)
        runner.work()
        
        # check stdoutput
        tmpOutFileH = None
        stdout = None
        try:
            tmpOutFileH = open(tmpOutFile, 'r')
            stdout = tmpOutFileH.read()
            stdout = stdout.strip()
            tmpOutFileH.close()
            try:
                if (os.path.exists(tmpOutFile)):
                    os.remove(tmpOutFile)
            except Exception, e:
                print ("Error: cannot delete tmpOutFile[%s]: " %(tmpOutFile)), e                
            if 'FATAL:' in stdout:
                print "!Error! \"FATAL:\" keyword appeared after squid configuration test!"
                return 1
        except Exception, exc:
            print "Error: cannot open stdout file: %s ; " % (tmpOutFile), exc
            return 2
        pass
        return 0
    
    def generateSquidConfigFromTemplate(self, proxylist):
        """
        Generates SQUID configuration file from template configuration file.
        Place where new proxies should be put should be marked with {{{PROXIES}}}
        
        Proxy list is iterable structure, element of structure is simple list with meaning
        0 -> IP
        1 -> port
        2 -> login
        3 -> password
        """
        
        '''At first we generate proxy file'''
        nn = datetime.datetime.now()
        proxyString = "# Generated: [%s]\n" % (nn.strftime("%Y-%m-%d %H:%M")) 
        for i,p in enumerate(proxylist):
            if len(p)==2:
                proxyString += "cache_peer %s parent %s 0 round-robin no-query\n" % (p[0], p[1])
            else:
                proxyString += "cache_peer %s parent %s 0 round-robin no-query login=%s:%s\n" % (p[0], p[1], p[2], p[3])
        
        '''Substitute proxies to configuration file'''
        try:
            tmpOutFileH = open(self.squid_proxy_template, 'r')
            tpl = str(tmpOutFileH.read())
            tmpOutFileH.close()
            
            return tpl.replace('{{{PROXIES}}}', proxyString, 1)
        except Exception, e:
            print "Error during generating new configuration file"
            return None            
        
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
            print "[*] File successfully loaded..."
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
        3. generate new config file from template file
        4. test new config file with squid parse, if is OK, reload squid
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
        while True:
            time.sleep(float(self.proxyrefresh))
            phaseCurTime = time.time()
            phaseCurDatetime = datetime.datetime.now()
            phunt = proxyhunter(OutputProxy='proxylist.txt', GoodProxy='goodproxylist.txt', 
                                Verbose=False, TimeOut=int(self.proxytimeout), 
                                Sitelist=[], RetryCount=int(self.proxyretry), 
                                TestUrl=self.proxyurl)
            
            curProxyList = self.readProxyList()
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
                    print "[*] %s%s%s \n \'--------------> Piece of Shit [%05.2f s]" % (phunt._red, tmpProxyName, phunt._reset, cProxyTime)
                    curProxyList.remove(p)
                else:
                    print "[*] %s%s%s \n \'--------------> We have a Good One [%05.2f s]" % (phunt._red, tmpProxyName, phunt._reset, cProxyTime)
            pass
            
            '''Generate new squid file with new proxies'''
            cfgTxt = self.generateSquidConfigFromTemplate(curProxyList)
            tmpSquidConfigFile=self.squid_config_file + "__tmp__"
            if cfgTxt == None:
                print "Error: generated proxy configuration file is empty, cannot continue"
                continue
            
            '''Substitute proxies to configuration file'''
            try:
                tmpOutFileH = open(tmpSquidConfigFile, 'w')
                tmpOutFileH.write(cfgTxt)
                tmpOutFileH.close()
            except Exception, e:
                print "Error during saving new configuration file: ", e
                continue
            
            '''Test that damn proxies configuration'''
            cfgTestRes = self.proxyConfigTest(tmpSquidConfigFile)
            if cfgTestRes > 0:
                print "Error during generated config file testing"
                continue
            
            '''Owerwrite old config file with new config file'''
            try:
                os.rename(tmpSquidConfigFile, self.squid_config_file)
            except Exception,e:
                print "Error during moving [%s] -> [%s]; " % (tmpSquidConfigFile, self.squid_config_file), e
                continue
            
            '''Reload new changes'''
            runner = ph4CmdRunner(self.squid_reload_command, blocking=True)
            runner.work()
            print "DONE", "="*80, "\n"
            
        #if not problem2send == '':
        #    body = 'Problem with rdiff-backup! Problems: \n%s\n Desc:\n%s Stoud: %s\n' % (problem2send, desc, stdout)
        #    self.sendMail(self.backupDesc['erroremail'], "Problem with backup [%s - %s]" % (self.backupDesc['user'], rec['src']), body)
        #else:
        #    print "Process ended successfully!"
        #print ""
        
       
    def run(self):
        """Main runner method"""
        startTime = time.time()
        startDatetime = datetime.datetime.now()
        
        # mailtest?
        if self.mailtest != None:
            self.mailTest(self.mailtest)
            sys.exit(0)
        
        desc = "Starting squid proxy check: %s (sec:%s)" % (startDatetime.strftime("%Y-%m-%d %H:%M"), startTime) 
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
            body = 'Main backup failed, exception thrown\nDesc: %s\nExc: %s\n' % (desc, exc)
            self.sendMail(self.maildest, "Problem with proxycheck", body)
        pass

def main():
    print "\nSquid proxy checker v.%s by %s - Proxy Hunter and Tester Opensource engine\nA high-level cross-protocol proxy-hunter\n" % (__version__, __author__)
    engine = ph4ProxyCheckerRunner()
    engine.run()
                     
if __name__ == '__main__':
    main()

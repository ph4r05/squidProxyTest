#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the 
#      Free Software Foundation, Inc., 
#      59 Temple Place, Suite 330, 
#      Boston, MA  02111-1307  USA
#
#   http://www.securityoverride.com

import sys
import warnings
import urllib2
import re
import socket
import random
import optparse
import os
import copy
warnings.filterwarnings(action="ignore", message=".*(sets) module is deprecated", category=DeprecationWarning)
import sets

__author__   = "dr8breed"
__date__    = "Thu May  16 00:00:41 2011"
__version__    = "09"
__copyright__    = "burp and farts"

class proxyhunter(object):
   """ 
   Instance variables:
    
   Outputproxy
      Output file every proxy will be printed in
      Default : proxylist.txt
   
   Goodproxy
      Output file all good proxy will be print
      Default : goodproxylist.txt
   
   Verbose
      More noise, every proxy will be print into screen
      Default : True
   Timeout
      Timeout every test proxy connections in socket
      Default : 30
   
   Sitelist
      Proxy site for parsing proxy
      Default : []
      
   """
   def __init__(self, OutputProxy='proxylist.txt', GoodProxy='goodproxylist.txt', Verbose=True, TimeOut=30, Sitelist=[], RetryCount=3, TestUrl='http://www.google.com'):
      self._red       = '\033[31m'
      self._reset       = '\033[0;0m'
      self._wide      = " "*50
      self._timeout      = TimeOut
      self._retrycount   = RetryCount
      self._verbose      = Verbose
      self._testurl      = TestUrl
      self._ouruseragent    = ['Mozilla/4.0 (compatible; MSIE 5.0; SunOS 5.10 sun4u; X11)',
               'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.2pre) Gecko/20100207 Ubuntu/9.04 (jaunty) Namoroka/3.6.2pre',
               'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Avant Browser;',
               'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 5.0)',
                    'Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.1)',
                    'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.0.6)',
                    'Microsoft Internet Explorer/4.0b1 (Windows 95)',
                    'Opera/8.00 (Windows NT 5.1; U; en)',
               'amaya/9.51 libwww/5.4.0',
               'Mozilla/4.0 (compatible; MSIE 5.0; AOL 4.0; Windows 95; c_athome)',
               'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)',
               'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
               'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; ZoomSpider.net bot; .NET CLR 1.1.4322)',
               'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; QihooBot 1.0 qihoobot@qihoo.net)',
               'Mozilla/4.0 (compatible; MSIE 5.0; Windows ME) Opera 5.11 [en]']
      self._referer      = ['http://google.com','http://bing.com']
      # You can add yours...       
      self._sitelist       = Sitelist   
      self._output      = OutputProxy
      self._goodproxy      = GoodProxy           
          
   def Samairdotru(self): 
      counter    = 1 
      proxycounter   = 0 
      maxpages    = 60 
      urls       = [] 
      cntlen      = 0
      proxyfile   = file(self._output, 'a') 
      print "[*] Hunting proxy from samair.ru please wait..." 
      while counter <= maxpages: 
         if counter <= 9: 
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            opener.addheaders = [('User-agent', random.choice(self._ouruseragent)),
                     ('Referer', random.choice(self._referer))]      
            urllib2.install_opener(opener)
            url = urllib2.urlopen('http://www.samair.ru/proxy/proxy-0'+repr(counter)+'.htm').read() 
         else: 
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            opener.addheaders = [('User-agent', random.choice(self._ouruseragent)),
                     ('Referer', random.choice(self._referer))]      
            urllib2.install_opener(opener)
            url = urllib2.urlopen('http://www.samair.ru/proxy/proxy-'+repr(counter)+'.htm').read() 
         proxies = re.findall(('\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:\d{1,5}'), url) 
         lenstr   = len(proxies)
         proxycounter = int(proxycounter) + int(len(proxies))
         sys.stdout.write("\r[*] %s%d%s Proxies received from : http://www.samair.ru/proxy/ %s" % (self._red, int(proxycounter), self._reset, self._wide))
         sys.stdout.flush()
         for singleproxy in proxies:
            if self._verbose:
               print singleproxy
            proxyfile.write(singleproxy+"\n")   
         counter = counter+1 
         opener.close()
      print "\n" 
      proxyfile.close()          
         
   def ParseProxy(self, site): 
      print "[*] Parse proxy from %s" % (site.split("//",3)[1])
      proxycounter    = 0 
      urls       = [] 
      proxyfile    = file(self._output, 'a') 
      opener       = urllib2.build_opener(urllib2.HTTPHandler)
      opener.addheaders = [('User-agent', random.choice(self._ouruseragent)), ('Referer', random.choice(self._referer))]      
      urllib2.install_opener(opener)
      url       = urllib2.urlopen(site).read() 
      proxies    = re.findall(('\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}[:]\d{1,5}'), url) 
      for singleproxy in proxies: 
          if self._verbose:
            print singleproxy
            proxyfile.write(singleproxy+"\n") 
            proxycounter = proxycounter+1 
      sys.stdout.write("[*] %s%d%s Proxies receieved from : %s %s\n" % (self._red, int(proxycounter), self._reset, site.split("//",3)[1], self._wide))
      sys.stdout.flush()      
      opener.close() 
      proxyfile.close() 
         
   def Single(self):
      for site in self._sitelist:
         self.ParseProxy(site)
               
   def Cleanitup(self, sorted_output="uniqueproxylist.txt"): 
      """ proxy will be printed in uniqueproxylist.txt by default """
      proxyfile    = open(self._output, 'r').readlines() 
      outfile    = file(sorted_output, 'a') 
      sortproxy    = [] 
      finalcount   = 0 
      for proxy in proxyfile: 
         if proxy not in sortproxy: 
            sortproxy.append(proxy) 
            outfile.write(proxy) 
            finalcount += 1 
      if self._verbose:
         for proxy in sortproxy:
            print proxy,
      print "\n[*] %s%d%s Unique proxy list has been sorted ." % (self._red, int(finalcount), self._reset),
      if sorted_output == "":
         print ""
      else:
         print "saved in %s" % (sorted_output)
         
      outfile.close() 

   def LoadProxy(self):
      global proxylist   
      try:
         #preventstrokes = open(self._output, "r")
         preventstrokes = open(self._output, "r")
         proxylist      = preventstrokes.readlines()
         count          = 0 
         while count < len(proxylist): 
            proxylist[count] = proxylist[count].strip() 
            count += 1
         # remove commented entries
         for i,p in enumerate(copy.deepcopy(proxylist)):
             if re.match('^\s*#',p)!=None: proxylist.remove(p)
         print "[*] File successfully loaded..."
      except(IOError): 
           print "\n[-] Error: Check your proxylist path\n"
           sys.exit(1)
      
   def CoreFreshTester(self, proxy):
      curRetry = self._retrycount
      try:
          if proxy==None or proxy=="": return 1
          socket.setdefaulttimeout(self._timeout)   
      except Exception, detail:
          if self._verbose: print "Error init: %s" % (detail)
          return 1
      while curRetry > 0:
          if self._verbose: print "Retries left: %d" % curRetry 
          try:   
             #proxy_support = urllib2.ProxyHandler({"http" : "http://%s:%d" % (proxy[0], int(proxy[1]))})
             proxy_support = urllib2.ProxyHandler({"http" : "http://%s" % (proxy)})
             opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
             opener.addheaders = [('User-agent', random.choice(self._ouruseragent)), ('Referer', random.choice(self._referer))]      
             urllib2.install_opener(opener)
             f = urllib2.urlopen(self._testurl)
             if self._verbose:
                print "HEADERS: ", f.headers
                print "BODY: ", f.read()
             return 0
          except urllib2.HTTPError, e:     
              if self._verbose:   
                  print 'Error y: %s code : %s' % (e, e.code)
              curRetry-=1     
          except Exception, detail:
             if self._verbose:
                 print "Error x: %s" % (detail)
             curRetry-=1
      # retrycount failed now
      return 1   

   def MainFreshTester(self, proxy):
      if self.CoreFreshTester(proxy):
         print "[*] %s%s%s \n \'--------------> Piece of Shit" % (self._red, proxy, self._reset)
      else:
         print "[*] %s%s%s \n \'--------------> We have a Good One" % (self._red, proxy, self._reset)
         writegoodpxy.write(proxy)   
         writegoodpxy.write("\n")   
            
   def TestProxy(self):
      global writegoodpxy
      writegoodpxy    = file(self._goodproxy, 'w')   
      for proxy in proxylist:
         self.MainFreshTester(proxy)
      print "[*] All Fresh proxy has been saved in %s" % (self._goodproxy)   
      writegoodpxy.close()   

''' Direct use class of this library '''
class runengine(object):
   def __init__(self):
      self._sitelist    = ['http://www.proxy-list.net/anonymous-proxy-lists.shtml', 
             'http://www.digitalcybersoft.com/ProxyList/fresh-proxy-list.shtml', 
             'http://www.1proxyfree.com/', 
             'http://www.proxylists.net/http_highanon.txt', 
             'http://www.atomintersoft.com/products/alive-proxy/socks5-list/',
             'http://www.proxylist.net/',
             'http://aliveproxy.com/high-anonymity-proxy-list/',
             'http://spys.ru/en/',
             'http://spys.ru/en/http-proxy-list/',
             'http://atomintersoft.com/free_proxy_list',
             'http://aliveproxy.com/proxy-list/proxies.aspx/Indonesia-id',
            'http://tinnhanh.ipvnn.com/free-proxy/Indonesia_Proxy_List.ipvnn'] 
   def parseoption(self):
      global jSamairdotru, jSingle, jTestproxy, doall, version, output, proxytest, verbose, goodproxy, timeout, retrycount 
      baseprog   = os.path.basename(sys.argv[0])
      parser       = optparse.OptionParser()
      if len(sys.argv) <= 1:
         parser.exit(msg="""Usage : %s [option]
   -h or --help for get help \n\n""" % (sys.argv[0]))
      ''' parse for option '''      
      parser.add_option("-s", "--samair", 
              dest="jSamairdotru", 
              action="store_true",
                          help="just use samair.ru to hunt proxies")
      parser.add_option("-l", "--sitelist", dest="jSingle", action="store_true",
                        help="use all site in the list")   
      parser.add_option("-t", "--test", 
              dest="jTestproxy", 
              action="store_true",
                        help="test all proxy !") 
      parser.add_option("-a", "--all", 
              dest="doall", 
              action="store_true",
                        help="do all !")
      parser.add_option("-v", "--version", 
              dest="version", 
              action="store_true", 
                        help="print current proxy hunter version")
      parser.add_option("-d", "--debug", 
              dest="verbose", 
              action="store_true",
                        help="debug program for more talkable &amp; every proxy will be print to screen")                        
      parser.add_option("-o", "--outputfile", 
              dest="outputfile", 
              default="proxylist.txt", 
              type="string", 
              action="store", 
              metavar="FILE",
                        help="output proxy will be print               [default : %default]" )                        
      parser.add_option("-i", "--inputfile", 
              dest="inputfile", 
              default="proxylist.txt", 
              type="string", 
              action="store", 
              metavar="FILE",
                        help="input proxy will be checked               [default : %default]")
      parser.add_option("-g", "--outputgood", 
              dest="outputgoodproxy", 
              default="goodproxy.txt", 
              type="string", 
              action="store", 
              metavar="FILE",
                        help="output all good proxy will be saved             [default : %default]")                        
      parser.add_option("-c", "--timeout", 
              dest="timeout", 
              default=30, 
              type="int", 
              action="store", 
              metavar="NUMBER",
                        help="timeout connections being program run            [default : %default]")  
      parser.add_option("-r", "--retry-count", 
              dest="retrycount", 
              default=3, 
              type="int", 
              action="store", 
              metavar="NUMBER",
                        help="retry count to consider proxy failing            [default : %default]")   

 
      group = optparse.OptionGroup(parser, "Example ",
                          """%s -s         | Gather proxy with samair.ru
                          
                          %s -l         | Gather proxy in the url list 
                          
                          %s -t proxylist.txt   | Test proxy inside proxylist.txt   
                          
                          %s -a         | Do all                            
                          
                          %s -v          | Print current version
                          """ % (baseprog, baseprog, baseprog, baseprog, baseprog))
      parser.add_option_group(group)                                                              
      (options, args) = parser.parse_args()
      jSamairdotru    = options.jSamairdotru
      jSingle      = options.jSingle
      jTestproxy   = options.jTestproxy
      doall      = options.doall
      version      = options.version
      output      = options.outputfile
      proxytest   = options.inputfile
      verbose      = options.verbose
      goodproxy   = options.outputgoodproxy
      timeout      = options.timeout
      retrycount  = options.retrycount
      
   def printversion(self):
      print "Version : %s \n" % (__version__)   
                      
   def run(self):
      proxyengine   = proxyhunter(OutputProxy=output, GoodProxy=goodproxy, Verbose=verbose, TimeOut=timeout, Sitelist=self._sitelist, RetryCount=retrycount)   
      if version:
         self.printversion()
      if jSamairdotru:
         proxyengine.Samairdotru()
         proxyengine.Cleanitup()
      if jSingle:
         proxyengine.Single()
         proxyengine.Cleanitup()
      if jTestproxy:
         proxyengine.LoadProxy()
         proxyengine.TestProxy()
      if doall:
         proxyengine.Samairdotru()
         proxyengine.Single()   
         proxyengine.LoadProxy()
         proxyengine.TestProxy()         
      
def main():
   print "\nPyProxy v.%s by %s - Proxy Hunter and Tester Opensource engine\nA high-level cross-protocol proxy-hunter\n" % (__version__, __author__)
   proxyengine   = runengine()
   proxyengine.parseoption()
   proxyengine.run()
                     
if __name__ == '__main__':
   main()

#!/usr/bin/env python
#
# Proprietary and Confidential
#
# (c) 2008, the grugq <the.grugq@gmail.com>

from mechanize import LinkNotFoundError
import mechanize
import urllib2

def monkeypatch_thai():
    from encodings import aliases
    aliases.aliases['windows-874'] = 'tis_620'
monkeypatch_thai()


class Browser(mechanize.Browser):
    def __init__(self, ua, factory=mechanize.RobustFactory()):
        mechanize.Browser.__init__(self, factory)
        self.set_handle_robots(False)
        try:
            self.set_handle_gzip(True)
        except Warning:
            pass # fuck it, this works for me
        self.addheaders = [
            ('User-Agent', ua),
            ('Accept-Encoding', 'gzip,deflate')
        ]

    def open(self, url, data=None, proxy=None):
        try:
            url.get_full_url
        except AttributeError:
            scheme, authority = mechanize._rfc3986.urlsplit(url)[:2]
            if scheme is None:
                if self._response is None:
                    raise mechanize.BrowserStateError("Can't fetch relative reference:"
                                                        "not viewing any document")
                url = mechanize._rfc3986.urljoin(self._response.geturl(), url)
        req = self._request(url, data, None)
        if proxy is not None:
            req.set_proxy(proxy, 'http')
        rp = mechanize.Browser.open(self, req, data)
        self.clear_history()
        return rp


class FireFox2(Browser):
    def __init__(self):
        Browser.__init__(self,
        'Mozilla/5.0 (Macintosh; U; PPC Mac OS X Mach-O; en-US; rv:1.8.1) Gecko/20061010 Firefox/2.0'
        )
FireFox = FireFox2

class FireFox3(Browser):
    def __init__(self):
        Browser.__init__(self, '')

class Safari(Browser):
    def __init__(self):
        Browser.__init__(self,
        'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en-us) AppleWebKit/523.10.5 (KHTML, like Gecko) Version/3.0.4 Safari/523.10.6'
        )

class InternetExplorer6(Browser):
    def __init__(self):
        Browser.__init__(self, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)')
IE6 = InternetExplorer6

class InternetExplorer7(Browser):
    def __init__(self):
        Browser.__init__(self, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)')
IE7 = InternetExplorer7

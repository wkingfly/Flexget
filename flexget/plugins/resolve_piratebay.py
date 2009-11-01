import urllib2
import logging
from module_resolver import ResolverException
from flexget.plugin import *
from flexget.utils.soup import get_soup

log = logging.getLogger('piratebay')

class ResolvePirateBay:
    """PirateBay resolver."""

    # resolver API
    def resolvable(self, feed, entry):
        url = entry['url']
        if url.endswith('.torrent'): return False
        if url.startswith('http://thepiratebay.org/'): return True
        if url.startswith('http://torrents.thepiratebay.org/'): return True
        return False
        
    # resolver API
    def resolve(self, feed, entry):
        if entry['url'].startswith('http://thepiratebay.org/search/'):
            # use search
            try:
                entry['url'] = self.search_title(entry['title'])
                log.debug('search returned %s' % entry['url'])
            except PluginWarning, e:
                raise ResolverException(e)
        else:
            # parse download page
            entry['url'] = self.parse_download_page(entry['url'])

    @internet(log)
    def parse_download_page(self, url):
        page = urllib2.urlopen(url)
        try:
            soup = get_soup(page)
            tag_div = soup.find('div', attrs={'class':'download'})
            if not tag_div:
                raise ResolverException('Unable to locate download link from url %s' % url)
            tag_a = tag_div.find('a')
            torrent_url = tag_a.get('href')
            return torrent_url
        except Exception, e:
            raise ResolverException(e)    
            
    # search API
    def search(self, feed, entry):
        return self.search_title(entry['title'])

    @internet(log)
    def search_title(self, name, url=None):
        """Search for name from piratebay, if a search url is passed it will be 
        used instead of internal search."""
        
        import urllib
        name = name.replace('.',' ').lower()
        if not url:
            url = 'http://thepiratebay.org/search/'+urllib.quote(name)
        page = urllib2.urlopen(url)
        
        soup = get_soup(page)
        torrents = []
        for link in soup.findAll('a', attrs={'class': 'detLink'}):
            if not link.contents[0].replace('.', ' ').lower() == name:
                continue
            torrent = {}
            torrent['name'] = link.contents[0]
            torrent['link'] = 'http://thepiratebay.org'+link.get('href')
            tds = link.parent.parent.findAll('td')
            torrent['seed'] = int(tds[-2].contents[0])
            torrent['leech'] = int(tds[-1].contents[0])
            torrents.append(torrent)
            
        if not torrents:
            raise PluginWarning('No matches for %s' % name, log, log_once=True)
            
        def best(a, b):
            score_a = a['seed']*2 + a['leech']
            score_b = b['seed']*2 + b['leech']
            return cmp(score_a, score_b)

        torrents.sort(best)
        torrents.reverse()
        return torrents[0]['link']

register_plugin(ResolvePirateBay, 'piratebay', groups=['resolver', 'search'])

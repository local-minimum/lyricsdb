"""Functionality for crawling a site...

Note: This module is meant as an illustration of how
 scraping a site could be done. It might not be compatible
 with the policies of said site. And such policies may matter
 or not, depending on where in the world you live. So use
 with care...
"""
import requests
from itertools import product
import re
from bs4 import BeautifulSoup
from threading import BoundedSemaphore, Thread, Lock, RLock
from string import uppercase
from time import sleep


def get_session():
    s = requests.session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    return s


def crawl_for_content(s, uri, pattern, visited):

    if uri in visited:
        return tuple()

    response = s.get(uri)
    if response and response.ok:
        return pattern.finditer(response.text)
    else:
        return tuple()


def parse_lyrics_to_com_song(session, uri, visited):

    if uri in visited:
        return None

    response = session.get(uri)

    if response and response.ok:

        soup = BeautifulSoup(response.text, "lxml")
        song = soup.find(id="lyric-body-text")
        if song:
            return tuple(l.strip() for l in song.get_text().split("\n") if l.strip())

    return None


class Collector(object):

    def __init__(self, obj=None):

        if obj is None:
            obj = []

        self._obj = obj
        self._lock = Lock()

    def __call__(self, song):

        self._lock.acquire()
        try:
            self._obj.append(song)
        except AttributeError:
            self._obj.add(song)
        self._lock.release()

    @property
    def data(self):

        return self._obj


class Visited(object):

    def __init__(self):

        self._set = set()
        self._lock = Lock()

    def __contains__(self, item):

        self._lock.acquire()

        if item not in self._set:

            self._set.add(item)
            self._lock.release()
            return False

        self._lock.release()
        return True

    def __len__(self):

        self._lock.acquire()
        l = len(self._set)
        self._lock.release()
        return l

    @property
    def data(self):

        return self._set


class Counter(object):

    def __init__(self, max_count, report_frequency):

        self._report_freq = report_frequency
        self._next_report = report_frequency
        self._max_count = max_count
        self._count = 0
        self._lock = RLock()

    def increase(self):

        self._lock.acquire()
        self._count += 1

        if self.should_report:
            print("{0} Lyrics parsed".format(str(self._count).zfill(8)))
        self._lock.release()

    @property
    def value(self):

        return self._count

    @property
    def overflow(self):

        self._lock.acquire()
        ret = self._max_count is not None and self._count > self._max_count
        self._lock.release()
        return ret

    @property
    def should_report(self):

        self._lock.acquire()
        if self._count > self._next_report:

            self._next_report += self._report_freq
            self._lock.release()
            return True

        self._lock.release()
        return False


def crawl(callback, depth=100, **kwargs):

    pattern_fillers = product(tuple("/" + l for l in uppercase),
                              ["/{0}".format(v + 1) if v else "" for v in range(depth)])

    return crawl_site(callback, pattern_fillers=pattern_fillers, **kwargs)


def crawl_site(callback,
               pattern="http://www.lyrics.com{0}{1}",
               pattern_fillers=tuple(),
               page_parser=parse_lyrics_to_com_song,
               max_lyrics=None,
               print_frequency=100,
               max_workers=1000,
               visited=None):

    def worker(album, counter, semaphor_pool, visited):

        worker_session = get_session()
        for lyric in crawl_for_content(
                worker_session,
                "http://www.lyrics.com{0}".format(album.group()[6:]),
                lyric_reg,
                visited):

            if counter.overflow:
                semaphor_pool.release()
                return

            elif lyric:

                callback(
                    page_parser(
                        worker_session,
                        "http://www.lyrics.com{0}".format(lyric.group()[6:]),
                        visited))

                counter.increase()

        semaphor_pool.release()

    session = get_session()

    threads = set()

    artist_reg = re.compile(r'href="artist/[^"]+')
    album_reg = re.compile(r'href="/album/[^"]+')
    lyric_reg = re.compile(r'href="/lyric/[^"]+')

    lyric_counter = Counter(max_lyrics, print_frequency)

    if visited is None:
        visited = Visited()

    semaphor_pool = BoundedSemaphore(value=max_workers)
    break_out = False

    try:

        for fillers in pattern_fillers:

            for artist in crawl_for_content(session, pattern.format(*fillers), artist_reg, visited):

                if artist:

                    for album in crawl_for_content(session,
                                                   "http://www.lyrics.com/{0}".format(artist.group()[6:]),
                                                   album_reg,
                                                   visited):

                        if album:
                            semaphor_pool.acquire()
                            t = Thread(target=worker, args=(album, lyric_counter, semaphor_pool, visited))
                            t.start()
                            threads.add(t)

                        if lyric_counter.overflow:
                            break_out = True
                            break
                        else:
                            print("** Album thread started")
                            sleep(0.5)

                if break_out:
                    break

            if break_out:
                break

    except KeyboardInterrupt:

        print("** Waiting for threads, CTRL+C to not do that")

        try:

            for t in threads:
                t.join()

        except KeyboardInterrupt:

            pass

    return visited
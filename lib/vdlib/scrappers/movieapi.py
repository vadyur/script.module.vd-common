# -*- coding: utf-8 -*-

from typing import Iterator, List, Optional, TypedDict, Dict, Union

from vdlib.kodi.video_info import Art
from ..util import log
from ..util.log import debug

from ..util import urlopen

import json, re

import requests
from bs4 import BeautifulSoup, Tag
from ..util.base import clean_html

user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100"


def get_tmdb_api_key():
    key = "f090bb54758cabf231fb605d3e3e0468"
    host = "api.themoviedb.org"

    from ..util import filesystem

    try:
        from ..kodi.compat import translatePath
        from ..util.string import decode_string
        import xbmc

        home_path = decode_string(translatePath("special://home"))
        major = xbmc.getInfoLabel("System.BuildVersion").split(".")[0]

        if int(major) > 17:
            return {"host": host, "key": key}

    except ImportError:
        # cur = filesystem.dirname(__file__)
        # home_path = filesystem.join(cur, '../..')

        return {"host": host, "key": key}

    try:
        xml_path = filesystem.join(
            home_path, "addons", "metadata.common.themoviedb.org", "tmdb.xml"
        )
        with filesystem.fopen(xml_path, "r") as xml:
            content = xml.read()
            match = re.search(r"api_key=(\w+)", content)
            if match:
                key: str = match.group(1)
                debug("get_tmdb_api_key: ok")

            m = re.search(r"://(.+)/3/", content)
            if m:
                host = m.group(1)

    except BaseException as e:
        debug("get_tmdb_api_key: " + str(e))

    return {"host": host, "key": key}


def attr_text(s):
    return s.get_text()


def attr_split_slash(s):
    itms = s.get_text().split("/")
    return [i.strip() for i in itms]


def attr_year(s):
    import re

    m = re.search(r"(\d\d\d\d)", s.get_text())
    if m:
        return m.group(1)


def attr_genre(s):
    return [a.get_text() for a in s.find_all("a")]


class IDs(object):
    kp_by_imdb = {}
    imdb_by_kp = {}

    @staticmethod
    def id_by_kp_url(url):
        import re

        m = re.search(r"(\d\d+)", url)
        if m:
            return m.group(1)

        return None

    @staticmethod
    def get_by_kp(kp_url):
        return IDs.imdb_by_kp.get(IDs.id_by_kp_url(kp_url))

    @staticmethod
    def get_by_imdb(imdb_id):
        return IDs.kp_by_imdb.get(imdb_id)

    @staticmethod
    def set(imdb_id, kp_url):
        if imdb_id and kp_url:
            kp_id = IDs.id_by_kp_url(kp_url)
            IDs.imdb_by_kp[kp_id] = imdb_id
            IDs.kp_by_imdb[imdb_id] = kp_id

    @staticmethod
    def has_imdb(imdb_id):
        return imdb_id in IDs.kp_by_imdb

    @staticmethod
    def has_kp(kp_url):
        kp_id = IDs.id_by_kp_url(kp_url)
        return kp_id in IDs.imdb_by_kp


from ..base.soup_base import soup_base

class tmdb_movie_item_base(object):
    def __init__(self, json_data: Dict):
        self._json_data: Dict = json_data

    def tmdb_id(self) -> Optional[str]:
        return self._json_data.get("id")

    def poster(self) -> str:
        try:
            return "http://image.tmdb.org/t/p/w500" + self._json_data["poster_path"]
        except BaseException:
            return ""

    def fanart(self) -> str:
        try:
            return "http://image.tmdb.org/t/p/original" + self._json_data["backdrop_path"]
        except BaseException:
            return ""

    def get_art(self) -> Art:
        art: Art = {}

        path = self.poster()

        art["thumb"] = path
        art["poster"] = path
        art["fanart"] = self.fanart()

        return art

    def title(self) -> str:
        try:
            return self._json_data["title"]
        except KeyError:
            return self._json_data.get('name', '')

    def original_title(self) -> str:
        try:
            return self._json_data["original_title"]
        except KeyError:
            return self._json_data.get('original_name', '')

    def overview(self) -> str:
        return self._json_data["overview"]

    def release_date(self) -> str:
        try:
            return self._json_data["release_date"]
        except KeyError:
            return ''

    def year(self) -> Optional[int]:
        date = self.release_date()
        if date:
            return int(date[:4])

    def get(self, key: str):
        if key == 'title':
            return self.title()
        elif key == 'originaltitle':
            return self.original_title()
        elif key == 'plot':
            return self.overview()
        elif key == 'year':
            return self.year()
        else:
            raise KeyError(key)


class tmdb_movie_item(tmdb_movie_item_base):
    def __init__(self, json_data: Dict, type="movie", url: Optional[str]=None):
        super(tmdb_movie_item, self).__init__(json_data)

        self._url = url
        self.type = type

    def _get_json_data(self) -> Dict:
        from ..util import HTTPError, URLError
        if self._url is None:
            return self._json_data
        else:
            try:
                self._json_data = json.load(urlopen(self._url))
                self._url = None
            except (HTTPError, URLError) as e:
                debug("Error TMDB request for {}".format(self._url))
        return self._json_data


    def get_info(self):
        info = {}

        if "genres" in self._get_json_data():
            info["genre"] = ", ".join([i["name"] for i in self._get_json_data()["genres"]])

        analogy = [
            ("aired", "release_date"),
            ("plot", "overview"),
            ("title", "name"),
            ("originaltitle", "original_title"),
            ("originaltitle", "original_name"),
        ]

        for xbmc_tag, tmdb_tag in analogy:
            if tmdb_tag in self._get_json_data():
                info[xbmc_tag] = self._get_json_data()[tmdb_tag]

        for tag in ["first_air_date", "aired", "release_date"]:
            if tag in self._get_json_data():
                aired = self._get_json_data()[tag]
                if aired:
                    m = re.search(r"(\d{4})", aired)
                    if m:
                        info["year"] = int(m.group(1))
                        break

        try:
            vid_item = self._get_json_data()["videos"]["results"][0]
            if vid_item["site"] == "YouTube":
                info["trailer"] = (
                    "plugin://plugin.video.youtube/?action=play_video&videoid="
                    + vid_item["key"]
                )
        except BaseException:
            pass

        string_items = [
            "mpaa",
            "title",
            "originaltitle",
            "duration",
            "code",
            "album",
        ]
        for item in string_items:
            if item in self._get_json_data():
                info[item] = self._get_json_data()[item]

        #  'credits',

        created_by = self._get_json_data().get("created_by")
        if created_by:
            info["director"] = [person["name"] for person in created_by]
        else:
            crew = self._get_json_data().get("credits", {}).get("crew")
            if crew:
                info["director"] = [person["name"] for person in crew if person["job"] == "Director"]

        production_companies = self._get_json_data().get("production_companies")
        if production_companies:
            companies = []
            for company in production_companies:
                companies.append(company["name"])
            info["studio"] = companies

        vote_average = self._get_json_data().get("vote_average")
        if vote_average:
            info["rating"] = vote_average

        if "uniqueid" not in info:
            info["uniqueid"] = {}
        info["uniqueid"].update({
            "imdb": self.imdb(),
            "tmdb": str(self.tmdb_id()),
            "tvdb": str(self.tvdb_id()),
        })

        return info

    def imdb(self) -> Optional[str]:
        try:
            if "imdb_id" in self._get_json_data():
                return self._get_json_data()["imdb_id"]
            else:
                return self._get_json_data().get("external_ids", {}).get("imdb_id")

        except BaseException:
            return None

    def tvdb_id(self):
        return self._get_json_data().get("external_ids", {}).get("tvdb_id")

    def posters(self) -> List[str]:
        try:
            _posters = self._get_json_data().get('images', {}).get('posters', [])
            return [ "http://image.tmdb.org/t/p/w500" + img['file_path'] for img in _posters ]
        except BaseException:
            return []

    def release_date(self) -> str:
        res = tmdb_movie_item_base.release_date(self)
        if res:
            return res
        return self._get_json_data().get('first_air_date', '')


class Object(object):
    pass


class imdb_cast(soup_base):
    def __init__(self, url):
        soup_base(self, url + "/fullcredits")
        self._actors = []

    @property
    def actors(self):
        #if not self._actors:
        #    tbl = self.soup.find("table", class_="cast_list")
        #    if tbl and isinstance(tbl, Tag):
        #        for tr in tbl.find("tr"):
        #            if "class" in tr:
        #                act = {}
        #                # https://images-na.ssl-images-amazon.com/images/M/MV5BMTkxMzk2MDkwOV5BMl5BanBnXkFtZTcwMDAxODQwMg@@._V1_UX32_CR0,0,32,44_AL_.jpg
        #                # https://images-na.ssl-images-amazon.com/images/M/MV5BMjExNzA4MDYxN15BMl5BanBnXkFtZTcwOTI1MDAxOQ@@._V1_SY1000_CR0,0,721,1000_AL_.jpg
        #                # https://images-na.ssl-images-amazon.com/images/M/MV5BMjExNzA4MDYxN15BMl5BanBnXkFtZTcwOTI1MDAxOQ@@._V1_UY317_CR7,0,214,317_AL_.jpg
        #                # img = tr.find('img')
        return self._actors


class ImdbAPI(object):
    headers = {"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "referer": 'https://www.google.com/',
                "sec-ch-ua": '"Not?A_Brand";v="99", "Opera";v="97", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "Windows",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.5563.147 Safari/537.36"
               }

    script_begin = '<script type="application/ld+json">'
    script_end='</script>'

    def __init__(self, imdb_id):

        self.resp = requests.get(
            "https://www.imdb.com/title/" + imdb_id + "/", headers=self.headers
        )

        self._json = None
        self._page = None

    @property
    def page(self):
        if self._page:
            return self._page

        if self.resp.status_code == requests.codes.ok:
            text = clean_html(self.resp.text)
            self._page = BeautifulSoup(text, "html.parser") # type: ignore
            return self._page

    @property
    def content(self):
        if self.resp.status_code == requests.codes.ok:
            return self.resp.content
        return b''

    @property
    def json(self):
        if self._json:
            return self._json

        lines = self.content.splitlines()
        for line in lines:
            string = line.decode('utf-8')
            if self.script_begin in string and '"@context"' in string:
                string = string.split(self.script_begin)[-1]
                string = string.split(self.script_end)[0]
                self._json = json.loads(string)
                return self._json

        return {}

    def year(self):
        jsn = self.json
        return jsn.get('datePublished', '')[:4] if jsn else ''

    def rating(self):
        jsn = self.json
        return str(jsn['aggregateRating']['ratingValue']) if jsn else 0

    def runtime(self):
        duration = self.json['duration']
        duration = duration.replace('PT', '').replace('H', 'h ').replace('M', 'm')
        return duration

    def mpaa(self):
        result = self.json.get('contentRating', '')
        return result

    def title(self):
        result = self.json['alternateName']
        return result

    def originaltitle(self):
        result = self.json['name']
        return result

    def type(self):
        a = self.page.find("a", href=re.compile(r"/title/tt\d+/episodes")) if self.page else None
        return "tvshow" if a else "movie"


class TMDB_Episode(TypedDict):
    air_date: str
    episode_number: int
    episode_type: str
    id: int
    name: str
    overview: str
    production_code: str
    runtime: int
    season_number: int
    show_id: int
    still_path: str
    vote_average: float
    vote_count: int

class TMDB_Season(TypedDict):
    air_date: str
    name: str
    overview: str
    poster_path: str
    season_number: int
    vote_average: float

def get_tmdb_lang():
    # 1. settings override
    try:
        import xbmcaddon

        addon = xbmcaddon.Addon("script.service.torrspy")
        lang = addon.getSetting("tmdb_language")
        if lang and lang != "auto":
            return lang

    except Exception:
        pass

    from vdlib.util.lang import get_language
    return get_language()

class tmdb_query_result(object):
    def __init__(self) -> None:
        self.result: List[tmdb_movie_item] = []

    def append(self, item: tmdb_movie_item) -> None:
        self.result.append(item)

    def __iter__(self) -> Iterator[tmdb_movie_item]:
        for x in self.result:
            yield x

    def __add__(self, other: 'tmdb_query_result') -> 'tmdb_query_result':
        r = tmdb_query_result()
        r.result = self.result + other.result
        return r

    def __len__(self) -> int:
        return len(self.result)

    def __getitem__(self, index: int) -> tmdb_movie_item:
        return self.result[index]

    def __bool__(self) -> bool:
        return len(self.result) != 0

    __nonzero__ = __bool__


class TMDB_API(object):
    api_url = "https://api.themoviedb.org/3"
    tmdb_api_key = get_tmdb_api_key()

    @staticmethod
    def get_lang():
        return get_tmdb_lang()

    @staticmethod
    def url_imdb_id(idmb_id):

        url = "http://%s/3/find/%s?api_key=%s&language=%s&external_source=imdb_id" % (
            TMDB_API.tmdb_api_key["host"],
            idmb_id,
            TMDB_API.tmdb_api_key["key"],
            TMDB_API.get_lang()
        )
        tmdb_data = json.load(urlopen(url))

        for type in ["movie", "tv"]:
            try:
                id = tmdb_data["%s_results" % type][0]["id"]
                return (
                    "http://%s/3/" % TMDB_API.tmdb_api_key["host"]
                    + type
                    + "/"
                    + str(id)
                    + "?api_key="
                    + TMDB_API.tmdb_api_key["key"]
                    + "&language=" + TMDB_API.get_lang()
                    + "&append_to_response=credits"
                )
            except:
                pass

        return None

    @staticmethod
    def search(title:str, append_to_response:Optional[str]=None, type:Optional[str]=None,  **kwargs) -> tmdb_query_result:
        from ..util import quote

        def make_url(media_type):
            host = TMDB_API.tmdb_api_key["host"]
            query = quote(title.encode("utf-8"))
            api_key=TMDB_API.tmdb_api_key["key"]
            lang = TMDB_API.get_lang()
            url = f"http://{host}/3/search/{media_type}?query={query}&api_key={api_key}&language={lang}"
            for k, v in kwargs.items():
                if k == 'include_image_language':
                    continue
                url += f"&{k}={v}"
            return url

        def get_movies():
            url = make_url("movie")
            return TMDB_API.tmdb_query(url, "movie", append_to_response, **kwargs)

        def get_tvs():
            url = make_url("tv")
            return TMDB_API.tmdb_query(url, "tv", append_to_response, **kwargs)

        if type is None:
            return get_movies() + get_tvs()
        elif type=='movie':
            return get_movies()
        elif type == 'tv':
            return get_tvs()
        else:
            raise ValueError(f"Unknown type {type}")

    @staticmethod
    def tmdb_query(url, type="movie", append_to_response=None, **kwargs) -> tmdb_query_result:
        if append_to_response is None:
            append_to_response = 'credits,videos,external_ids'

        result = tmdb_query_result()
        from ..util import HTTPError, URLError

        all_data = []
        pages_count = 1
        page = 1

        while page <= pages_count:
            page_url = url
            if page > 1:
                page_url += f"&page={page}"

            try:
                debug("Request is: " + page_url)
                data = json.load(urlopen(page_url))
                debug("data is: {}".format(data))
                all_data.append(data)
                pages_count = data.get("total_pages", 1)

            except (HTTPError, URLError) as e:
                debug("Error TMDB request")
                debug(e)
                continue

            finally:
                page += 1

        def make_url(type, id):
            api_key = TMDB_API.tmdb_api_key["key"]
            lang = TMDB_API.get_lang()
            host = TMDB_API.tmdb_api_key["host"]
            return f"http://{host}/3/{type}/{id}?api_key={api_key}&language={lang}&append_to_response={append_to_response}"

        for data in all_data:
            for tag in ["results", "movie_results", "tv_results"]:
                if tag not in data:
                    continue
                for r in data[tag]:

                    if "_results" in tag:
                        type = tag.replace("_results", "")

                    pending_url = make_url(type, r["id"])
                    for k, v in kwargs.items():
                        pending_url += f"&{k}={v}"

                    result.append(tmdb_movie_item(json_data=r, url=pending_url, type=type))

        return result

    @staticmethod
    def tmdb_by_imdb(imdb, type):
        url = (
            "http://%s/3/find/" % TMDB_API.tmdb_api_key["host"]
            + imdb
            + "?external_source=imdb_id&api_key="
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        url += "&append_to_response=credits,videos,external_ids"
        debug(url)
        return TMDB_API.tmdb_query(url, type)

    @staticmethod
    def popular(page=1):
        url = (
            "http://%s/3/movie/popular?api_key=" % TMDB_API.tmdb_api_key["host"]
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        url += "&page={}".format(page)
        return TMDB_API.tmdb_query(url)

    @staticmethod
    def popular_by_genre(genre, page=1):
        url = (
            "http://%s/3/discover/movie?api_key=" % TMDB_API.tmdb_api_key["host"]
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        # url += '&sort_by=popularity.desc'
        # url += '&sort_by=vote_average.desc&vote_count.gte=50'
        url += "&with_release_type=4|5|6"
        url += "&with_genres={}".format(genre)
        url += "&page={}".format(page)
        return TMDB_API.tmdb_query(url)

    @staticmethod
    def popular_tv(page=1):
        url = (
            "http://%s/3/tv/popular?api_key=" % TMDB_API.tmdb_api_key["host"]
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        url += "&page={}".format(page)
        return TMDB_API.tmdb_query(url, "tv")

    @staticmethod
    def top_rated(page=1):
        url = (
            "http://%s/3/movie/top_rated?api_key=" % TMDB_API.tmdb_api_key["host"]
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        url += "&page={}".format(page)
        return TMDB_API.tmdb_query(url)

    @staticmethod
    def top_rated_tv(page=1):
        url = (
            "http://%s/3/tv/top_rated?api_key=" % TMDB_API.tmdb_api_key["host"]
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        url += "&page={}".format(page)
        return TMDB_API.tmdb_query(url, "tv")

    @staticmethod
    def show_similar_t(page, tmdb_id, type):
        url = (
            "http://%s/3/" % TMDB_API.tmdb_api_key["host"]
            + type
            + "/"
            + str(tmdb_id)
            + "/similar?api_key="
            + TMDB_API.tmdb_api_key["key"]
            + "&language=" + TMDB_API.get_lang()
        )
        url += "&page={}".format(page)
        log.debug(url)
        return TMDB_API.tmdb_query(url, type)

    @staticmethod
    def show_similar(tmdb_id):
        return TMDB_API.show_similar_t(1, tmdb_id, "movie") + TMDB_API.show_similar_t(
            1, tmdb_id, "tv"
        )

    @staticmethod
    def imdb_by_tmdb_search(orig, year):
        try:
            for res in TMDB_API.search(orig):
                if year and res.year() and year != res.year():
                    continue

                r_title = res.title()
                r_original_title = res.original_title()

                if orig and (orig == r_title or orig == r_original_title):
                    return res.imdb()

        except BaseException as e:
            from log import print_tb

            print_tb(e)

        return None

    @staticmethod
    def genres_list():
        # &language=ru
        _ = TMDB_API.tmdb_api_key
        url = "http://{}/3/genre/movie/list?api_key={}".format(_["host"], _["key"])

        en = requests.get(url + "&language=en").json()["genres"]
        ru = requests.get(url + "&language=ru").json()["genres"]

        return [
            {
                "id": item[0]["id"],
                "en_name": item[0]["name"],
                "ru_name": item[1]["name"],
            }
            for item in zip(en, ru)
        ]

    def __init__(self, imdb_id=None, tmdb_id=None, type=None, append_to_response='credits'):
        url_ = None
        if imdb_id:
            url_ = TMDB_API.url_imdb_id(imdb_id)
        elif tmdb_id and type:
            url_ = "http://%s/3/" % TMDB_API.tmdb_api_key["host"] \
                    + type  \
                    + "/" \
                    + str(tmdb_id) \
                    + "?api_key=" \
                    + TMDB_API.tmdb_api_key["key"] \
                    + "&language=" + TMDB_API.get_lang() \
                    + "&append_to_response=" + append_to_response
        try:
            if url_:
                self.tmdb_data = json.load(urlopen(url_))
                debug("tmdb_data (" + url_ + ") \t\t\t[Ok]")
            else:
                self.tmdb_data = {}
        except Exception as e:
            debug("tmdb_data (" + str(url_) + ") \t\t\t[Error] " + str(e))
            self.tmdb_data = {}

    def title(self):
        try:
            if "title" in self.tmdb_data:
                return self.tmdb_data["title"]
            if "name" in self.tmdb_data:
                return self.tmdb_data["name"]
        except:
            pass
        raise AttributeError

    def originaltitle(self):
        try:
            if "original_title" in self.tmdb_data:
                return self.tmdb_data["original_title"]
            if "original_name" in self.tmdb_data:
                return self.tmdb_data["original_name"]
        except:
            pass
        raise AttributeError

    def year(self):
        try:
            return self.tmdb_data["release_date"].split("-")[0]
        except:
            raise AttributeError

    def poster(self):
        return "http://image.tmdb.org/t/p/original" + self.tmdb_data["poster_path"]

    def fanart(self):
        return "http://image.tmdb.org/t/p/original" + self.tmdb_data["backdrop_path"]

    def set(self):
        try:
            if "belongs_to_collection" in self.tmdb_data:
                belongs_to_collection = self.tmdb_data["belongs_to_collection"]
                if belongs_to_collection and "name" in belongs_to_collection:
                    return belongs_to_collection["name"]
        except:
            pass

        raise AttributeError

    def runtime(self):
        return self.tmdb_data["runtime"]

    def tag(self):
        return self.tmdb_data["tagline"]

    def plot(self):
        return self.tmdb_data["overview"]

    def actors(self):
        try:
            cast = self.tmdb_data["credits"]["cast"]
        except AttributeError:
            return []

        result = []
        for actor in cast:
            res = {}
            res["en_name"] = actor["name"]
            if actor.get("profile_path"):
                res["photo"] = (
                    "http://image.tmdb.org/t/p/original" + actor["profile_path"]
                )
            if actor.get("character"):
                res["role"] = actor["character"]
            if actor.get("order"):
                res["order"] = actor["order"]

            result.append(res)
        return result

    def genres(self):
        ll = [g["name"] for g in self.tmdb_data["genres"]]
        return ll

    def countries(self):
        from .countries import ru

        cc = [c["iso_3166_1"] for c in self.tmdb_data["production_countries"]]
        return [ru(c) for c in cc]

    def studios(self):
        ss = [s["name"] for s in self.tmdb_data["production_companies"]]
        return ss

    def season(self, season_number: int) -> Optional[TMDB_Season]:
        key = f"season/{season_number}"
        try:
            result = self.tmdb_data[key]
        except KeyError:
            for season in self.tmdb_data.get('seasons', []):
                if season['season_number'] == season_number:
                    return season
            return None
        return result

    def episodes(self, season_number: int) -> List[TMDB_Episode]:
        key = f"season/{season_number}"
        try:
            result = self.tmdb_data[key]['episodes']
        except KeyError:
            return []
        return result

class MovieAPI(object):

    APIs = {}

    @staticmethod
    def get_by(
        imdb_id=None,
        orig=None,
        year=None,
        imdbRaiting=None,
        settings=None,
    ):

        if not imdb_id:
            try:
                _orig = orig
                _year = year

            except BaseException as e:
                from log import print_tb

                print_tb(e)

        if imdb_id and imdb_id in MovieAPI.APIs:
            return MovieAPI.APIs[imdb_id], imdb_id

        api = MovieAPI(imdb_id, settings, orig, year)
        if imdb_id:
            MovieAPI.APIs[imdb_id] = api

        return api, imdb_id

    def __init__(
        self, imdb_id=None, settings=None, orig=None, year=None
    ):

        self.providers = []

        self.tmdbapi = None
        self.imdbapi = None

        self._actors = None

        if imdb_id:
            self.tmdbapi = TMDB_API(imdb_id)
            self.imdbapi = ImdbAPI(imdb_id)

            self.providers = [self.tmdbapi, self.imdbapi]
            if not self.tmdbapi.tmdb_data:
                self.providers.remove(self.tmdbapi)

        if imdb_id:
            if not settings:
                if not orig:
                    for api in self.providers:
                        try:
                            orig = api.originaltitle()
                            break
                        except:
                            pass

    def actors(self):
        if self._actors is not None:
            return self._actors

        actors = []
        for api in [self.tmdbapi]:
            if api:
                a = api.actors()
                if a:
                    actors.append(a)

        if len(actors) > 0:
            self._actors = [actor.copy() for actor in actors[0]]
        else:
            self._actors = []

        for act in self._actors:
            for variant in actors[1:]:
                for add in variant:
                    try:
                        if act["en_name"] == add["en_name"]:
                            act.update(add)
                    except KeyError:
                        pass

        return self._actors

    def __getitem__(self, key):
        for api in self.providers:
            try:
                res = api.__getattribute__(key)
                if res:
                    return res()
            except BaseException as e:
                continue

        raise AttributeError

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except AttributeError:
            return default

    def __getattr__(self, name):

        if name.startswith("_") or name in self.__dict__:
            return object.__getattribute__(self, name)

        for api in self.providers:
            try:
                res = api.__getattribute__(name)
                if res:
                    return res
            except AttributeError:
                continue

        raise AttributeError

    def ru(self, name):
        def ru_text(text):
            if not text:
                return False

            r = 0
            nr = 0
            for ch in text:
                if ch >= "А" and ch <= "Я":
                    r += 1
                elif ch >= "а" and ch <= "я":
                    r += 1
                else:
                    nr += 1
            return r > nr

        def ru_list(ll):
            for l in ll:
                if ru_text(l):
                    return True
            return False

        for api in self.providers:
            try:
                res = api.__getattribute__(name)
                if res and callable(res):
                    value = res()
                    if isinstance(value, list):
                        if ru_list(value):
                            return value
                    else:
                        if ru_text(value):
                            return value

            except AttributeError:
                continue

        raise AttributeError

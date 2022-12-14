from ..DI import DI

from ..plugin import Plugin
import json, xbmcgui, xbmc
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

class TMDB(Plugin):
    name = "tmdb"
    def get_list(self, url):
        if url.startswith("tmdb"):
            api = TMDB_API()
            if "tmdb_tv_show" in url:
                show_id, _, _ = url.replace("tmdb_tv_show(", "")[:-1].split(",")
                return api.handle_show(show_id)
            elif "tmdb_tv_season" in url:
                show_id, season = url.replace("tmdb_tv_season(", "")[:-1].split(",")
                return api.handle_season(show_id, season)
            else:
                _, kind, list_id = url.split("/")
                if kind == "list":
                    return api.handle_list(list_id)
                elif kind == "movie":
                    return api.handle_movies(list_id)
                elif kind == "keyword":
                    return api.handle_keyword(list_id)
                elif kind == "collection":
                    return api.handle_collection(list_id)

    def process_item(self, item):
        try:
            if "imdb_id" in item and "tmdb_id" not in item:
                api = TMDB_API()
                item["tmdb_id"] = api.get_tmdb_id(item["imdb_id"])
            if "tmdb_id" in item:
                api = TMDB_API()
                movie = api.get_movie(item["tmdb_id"])
                thumbnail = api.image_url + movie.get("poster_path", "")
                fanart = api.image_url + movie.get("backdrop_path", "")
                summary = movie.get("overview", "<empty summary>")
                list_item = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                list_item.setArt({"thumb": thumbnail, "fanart": fanart})
                list_item.setInfo("video", {"plot": summary, "plotoutline": summary})
                item["thumbnail"] = thumbnail
                item["fanart"] = fanart
                item["summary"] = summary
                item["imdb_id"] = movie["imdb_id"]
                item["year"] = movie["release_date"].split("-")[0]
                item["list_item"] = list_item
                item["link"] = f'microjenscrapers/play/{item["content"]}|{movie["title"]}|{movie["imdb_id"]}|{item["year"]}'
                item["is_dir"] = False
                return item
        except:
            pass

class TMDB_API:
    @property
    def headers(self):
        return {
            'content-type': "application/json;charset=utf-8",
            'authorization': f"Bearer {self.access_token}"
        }
    base_url = "https://api.themoviedb.org"
    image_url = "https://image.tmdb.org/t/p/w500"
    api_key = ownAddon.getSetting('tmdb.api_key') or ''
    access_token = ownAddon.getSetting('tmdb.access_token') or ''
    session = DI.session

    def get_list(self, list_id: int, page:int = 1):
        response = self.session.get(f"{self.base_url}/4/list/{list_id}?api_key={self.api_key}&page={page}", headers = self.headers)
        tmdb_list = response.json()
        results = tmdb_list["results"]
        if tmdb_list["total_pages"] > page:
            results.extend(self.get_list(list_id, page+1))
        return results

    def get_collection(self, list_id: int):
        response = self.session.get(f"{self.base_url}/3/collection/{list_id}?api_key={self.api_key}", headers = self.headers)
        tmdb_list = response.json()
        results = tmdb_list["parts"]            
        return results

    def get_keyword(self, list_id: int):
        response = self.session.get(f"{self.base_url}/3/keyword/{list_id}/movies?api_key={self.api_key}", headers = self.headers)
        tmdb_list = response.json()
        results = tmdb_list["results"]
        return results

    def get_show(self, show_id:int):
        response = self.session.get(f"{self.base_url}/3/tv/{show_id}?api_key={self.api_key}", headers = self.headers)
        tmdb_show = response.json()     
        return tmdb_show   

    def get_season(self, show_id:int, season:int):
        response = self.session.get(f"{self.base_url}/3/tv/{show_id}/season/{season}?api_key={self.api_key}", headers = self.headers)
        tmdb_season = response.json()     
        return tmdb_season   
    
    def get_movie(self, movie_id: int):
        response = self.session.get(f"{self.base_url}/3/movie/{movie_id}?api_key={self.api_key}", headers = self.headers)
        tmdb_movie = response.json()     
        return tmdb_movie    
    
    def get_movies(self, endpoint: str):
        response = self.session.get(f"{self.base_url}/3/movie/{endpoint}?api_key={self.api_key}", headers = self.headers)
        tmdb_movie = response.json()     
        return tmdb_movie["results"]   

    def process_items(self, items):
        items = [self.handle_item(item) for item in items]
        return items

    def handle_item(self, item):
        media_type = item["media_type"]
        if media_type == "movie":
            return self.handle_movie_xml(item)
        elif media_type == "tv":
            return self.handle_show_xml(item)

    def handle_movie_xml(self, movie):
        return {
            "type": "item",
            "title": movie["title"],
            "content": "movie",
            "summary": movie["overview"],
            "tmdb_id": movie["id"],
            "thumbnail": self.image_url + movie["poster_path"],
            "fanart": self.image_url + movie["backdrop_path"],
        }        
    
    def handle_movies_xml(self, movies):
        return [self.handle_movie_xml(movie) for movie in movies]  

    def handle_show_xml(self, show):
        try:
            year = show["first_air_date"].split("-")[0]
        except KeyError:
            year = 0
        item = {
            "type": "dir",
            "title": show["name"],
            "link": f'tmdb_tv_show({show["id"]}, {year}, {show["name"]})',
            "summary": show["overview"],
            "thumbnail": self.image_url + show.get("poster_path", ""),
            "fanart": self.image_url + show.get("backdrop_path", "")
        }
    
    def handle_season_xml(self, show):
        return [{
            "type": "dir",
            "title": season["name"],
            "link": f'tmdb_tv_season({show["id"]}, {season["season_number"]})',
            "summary": season["overview"],
            "thumbnail": self.image_url + season.get("poster_path", ""),
            "fanart": self.image_url + show.get("backdrop_path", "")
        } for season in show["seasons"]]        

    def handle_episodes_xml(self, season):
        return [{
            "type": "item",
            "title": episode["name"],
            "summary": episode['overview'],
            "content": "episode",
            "tmdb_id": episode["id"],
            "thumbnail": self.image_url + episode.get("still_path", ""),
            "fanart": self.image_url + season.get("poster_path", ""),
            "season": season['season_number'],
            "episode": episode['episode_number']
        } for episode in season["episodes"]]

    def handle_list(self, list_id: int):
        return json.dumps({"items": self.process_items(self.get_list(list_id))})

    def handle_collection(self, list_id: int):
        return json.dumps({"items": [self.handle_movie_xml(item) for item in self.get_collection(list_id)]})
        

    def handle_keyword(self, list_id: int):
        return json.dumps({"items": [self.handle_movie_xml(item) for item in self.get_keyword(list_id)]})
        
    
    def handle_show(self, show_id:int):
        return json.dumps({"items": self.handle_season_xml(self.get_show(show_id.strip()))})
        

    def handle_season(self, show_id:int, season:int):
        return json.dumps({"items": self.handle_episodes_xml(self.get_season(show_id.strip(), season.strip()))})

    def handle_movies(self, list_id: str):
        j = json.dumps({"items": self.handle_movies_xml(self.get_movies(list_id))})
        return j
    
    def get_tmdb_id(self, imdb_id: str):
        response = self.session.get(f"{self.base_url}/3/movie/{imdb_id}/external_ids?api_key={self.api_key}", headers = self.headers)
        r = response.json()       
        return r["id"]
        

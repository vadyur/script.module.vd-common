from typing import Optional, TypedDict, List, Union

class VideoInfo(TypedDict, total=False):
    title: str
    plot: str
    year: int
    genre: Union[str, List[str]]
    originaltitle: str
    rating: float
    country: Union[str, List[str]]
    episode: int
    season: int
    sortepisode: int
    sortseason: int
    episodeguide: str
    showlink: Union[str, List[str]]
    top250: int
    setid: int
    tracknumber: int
    userrating: int
    playcount: int
    overlay: int
    cast: List[str]
    castandrole: List[tuple]
    director: Union[str, List[str]]
    mpaa: str
    plotoutline: str
    sorttitle: str
    duration: int
    studio: Union[str, List[str]]
    tagline: str
    writer: Union[str, List[str]]
    tvshowtitle: str
    premiered: str
    status: str
    set: str
    setoverview: str
    tag: Union[str, List[str]]
    imdbnumber: str
    code: str
    aired: str
    credits: Union[str, List[str]]
    lastplayed: str
    album: str
    artist: List[str]
    votes: str
    path: str
    trailer: str
    dateadded: str
    mediatype: str
    dbid: int


class Art(TypedDict, total=False):
    thumb    : str # string - image filename
    poster   : str # string - image filename
    banner   : str # string - image filename
    fanart   : str # string - image filename
    clearart : str # string - image filename
    clearlogo: str # string - image filename
    landscape: str # string - image filename
    icon     : str # string - image filename

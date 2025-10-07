from urllib.parse import urlparse, urlunparse

def normalise_url(url) -> str:

    parsed_url = urlparse(url.strip())

    path = parsed_url.path or "/" # "http://example.onion" → path = "/"

    if path.endswith(("index.html", "index.htm", "index.php")): # http://example.onion/index.html → http://example.onion/
        path = path[: path.rfind("/") + 1]

    
    if path != "/" and path.endswith("/"): # http://example.onion/about/  →  http://example.onion/about
        path = path.rstrip("/")


    normalized = parsed_url._replace(
    scheme=parsed_url.scheme.lower(),
    netloc=parsed_url.netloc.lower(),
    path=path,
    params="",
    query="",
    fragment="",
    )   


    return urlunparse(normalized)
    

normalise_url("http://example.onion/about")
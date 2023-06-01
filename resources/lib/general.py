import requests

reqs = requests.session()

def request_get( url, data=None, extraHeaders=None ):

    """ makes a request """

    try:

        # headers
        my_headers = {
            'Accept-Language': 'en-gb,en;q=0.5',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Accept': 'a*/*',
            'content-type': 'application/x-www-form-urlencoded',
            'Referer': url,
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }

        # add extra headers
        if extraHeaders:
            my_headers.update(extraHeaders)

        # make request
        if data:
            response = reqs.post(url, data=data, headers=my_headers, verify=False, timeout=10)
        else:
            response = reqs.get(url, headers=my_headers, verify=False, timeout=10)

        return response.text

    except Exception:
        return ''

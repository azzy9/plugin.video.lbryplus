import xbmc
import xbmcaddon
import requests

from urllib.parse import quote,unquote,quote_plus,unquote_plus

from resources.lib.exception import *

ADDON = xbmcaddon.Addon()

lbry_api_url = unquote(ADDON.getSetting('lbry_api_url'))
if lbry_api_url == '':
    raise Exception('Lbry API URL is undefined.')
using_lbry_proxy = lbry_api_url.find('api.lbry.tv') != -1

reqs = requests.session()

def call_rpc(method, params={}, errdialog=True, additional_headers = None):
    try:
        xbmc.log('call_rpc: url=' + lbry_api_url + ', method=' + method + ', params=' + str(params))
        headers = {'content-type' : 'application/json'}
        if additional_headers:
            headers.update( additional_headers )
        json = { 'jsonrpc' : '2.0', 'id' : 1, 'method': method, 'params': params }
        result = requests.post(lbry_api_url, headers=headers, json=json)
        result.raise_for_status()
        rjson = result.json()
        if 'error' in rjson:
            raise PluginException(rjson['error']['message'])
        return result.json()['result']
    except requests.exceptions.ConnectionError as e:
        if errdialog:
            dialog.notification(tr(30105), tr(30106), NOTIFICATION_ERROR)
        raise PluginException(e)
    except requests.exceptions.HTTPError as e:
        if errdialog:
            dialog.notification(tr(30101), str(e), NOTIFICATION_ERROR)
        raise PluginException(e)
    except PluginException as e:
        if errdialog:
            dialog.notification(tr(30102), str(e), NOTIFICATION_ERROR)
        raise e
    except Exception as e:
        xbmc.log('call_rpc exception:' + str(e))
        raise e

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

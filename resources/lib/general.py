# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import time

import requests

import six

from six.moves.urllib.parse import quote, unquote, quote_plus, unquote_plus

from resources.lib.exception import *

ADDON = xbmcaddon.Addon()
KODI_VERSION = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4])

#language
__language__ = ADDON.getLocalizedString

dialog = xbmcgui.Dialog()
reqs = requests.session()

def get_string( string_id ):

    """ gets language string based upon id """

    if string_id >= 30000:
        return __language__( string_id )
    return xbmc.getLocalizedString( string_id )

def get_api_url():

    """ gets api URL - enforces Odysee url if using Odysee functionality """

    if ADDON.getSetting( 'odysee_enable' ) == 'true':
        return 'https://api.na-backend.odysee.com/api/v1/proxy'

    return unquote(ADDON.getSetting('lbry_api_url'))

def translate_path(path):

    """ method to translate path for both PY2 & PY3 """

    if six.PY2:
        return xbmc.translatePath( path )
    return xbmcvfs.translatePath( path )

def call_rpc(method, params={}, errdialog=True, additional_headers = None):

    """ Makes a RPC Call """

    try:
        xbmc.log('call_rpc: url=' + get_api_url() + ', method=' + method + ', params=' + str(params))
        headers = {'content-type' : 'application/json'}
        if additional_headers:
            headers.update( additional_headers )
        json_data = { 'jsonrpc' : '2.0', 'id' : 1, 'method': method, 'params': params }
        result = requests.post(get_api_url(), headers=headers, json=json_data)
        result.raise_for_status()
        rjson = result.json()
        if 'error' in rjson:
            raise PluginException(rjson['error']['message'])
        return result.json()['result']
    except requests.exceptions.ConnectionError as err:
        if errdialog:
            dialog.notification(get_string(30105), get_string(30106), xbmcgui.NOTIFICATION_ERROR)
        raise PluginException(err)
    except requests.exceptions.HTTPError as err:
        if errdialog:
            dialog.notification(get_string(30101), str(err), xbmcgui.NOTIFICATION_ERROR)
        raise PluginException(err)
    except PluginException as err:
        if errdialog:
            dialog.notification(get_string(30102), str(err), xbmcgui.NOTIFICATION_ERROR)
        raise err
    except Exception as err:
        xbmc.log('call_rpc exception:' + str(err))
        raise err

def request_get( url, data=None, extra_headers=None, return_json=True ):

    """ makes a request """

    try:

        # headers
        my_headers = {
            'Accept-Language': 'en-gb,en;q=0.5',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'a*/*',
            'Content-type': 'application/x-www-form-urlencoded',
            'Referer': url,
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }

        # add extra headers
        if extra_headers:
            my_headers.update(extra_headers)

        # make request
        if data:
            response = reqs.post(url, data=data, headers=my_headers, verify=False, timeout=10)
        else:
            response = reqs.get(url, headers=my_headers, verify=False, timeout=10)

        if return_json:
            return response.json()
        return response.text

    except Exception:
        return ''

def serialize_uri(item):

    """ all uris passed via kodi's routing system must be urlquoted """

    if type(item) is dict:
        item = item['name'] + '#' + item['claim_id']
    return quote(six.ensure_str(item))

def deserialize_uri(item):

    """ all uris passed via kodi's routing system must be urlquoted """

    return unquote(item)

def item_set_info( line_item, properties ):

    """ line item set info """

    if KODI_VERSION > 19.8:
        vidtag = line_item.getVideoInfoTag()
        if properties.get( 'year' ):
            vidtag.setYear( properties.get( 'year' ) )
        if properties.get( 'episode' ):
            vidtag.setEpisode( properties.get( 'episode' ) )
        if properties.get( 'season' ):
            vidtag.setSeason( properties.get( 'season' ) )
        if properties.get( 'plot' ):
            vidtag.setPlot( properties.get( 'plot' ) )
        if properties.get( 'title' ):
            vidtag.setTitle( properties.get( 'title' ) )
        if properties.get( 'studio' ):
            vidtag.setStudios([ properties.get( 'studio' ) ])
        if properties.get( 'writer' ):
            vidtag.setWriters([ properties.get( 'writer' ) ])
        if properties.get( 'duration' ):
            vidtag.setDuration( int( properties.get( 'duration' ) ) )
        if properties.get( 'tvshowtitle' ):
            vidtag.setTvShowTitle( properties.get( 'tvshowtitle' ) )
        if properties.get( 'mediatype' ):
            vidtag.setMediaType( properties.get( 'mediatype' ) )
        if properties.get('premiered'):
            vidtag.setPremiered( properties.get( 'premiered' ) )

    else:
        line_item.setInfo('video', properties)

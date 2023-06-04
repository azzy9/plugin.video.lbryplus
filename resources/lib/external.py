# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

from resources.lib.odysee import *
from resources.lib.general import *

ADDON = xbmcaddon.Addon()

odysee = odysee()

def get_profile_path(rpath):

    """ Gets Profile Path """

    return translate_path(ADDON.getAddonInfo('profile') + rpath)

def get_additional_header():

    """ Gets header with token if user is signed in """

    if odysee.has_login_details() and odysee.signed_in:
        return {'x-lbry-auth-token': odysee.auth_token}
    return {}

def get_stream_headers():

    """ Gets stream headers - required for some videos otherwise will return a 401 error """

    return '|Referer=https://odysee.com/'

def load_channel_subs():

    """ Gets Followed channels from Odysee """

    channels = []
    if odysee.has_login_details() and odysee.signed_in:

        subscriptions = call_rpc(
            'preference_get', {}, additional_headers=get_additional_header()
        )[ 'shared' ][ 'value' ][ 'subscriptions' ]

        for uri in subscriptions:
            uri = uri.replace('lbry://', '')
            items = uri.split('#')
            if len(items) < 2:
                continue
            channels.append((items[0],items[1]))
    return channels

def save_channel_subs(channels):

    """ TODO: Move to Odysee """

    try:
        with xbmcvfs.File(get_profile_path('channel_subs'), 'w') as f:
            for (name, claim_id) in channels:
                f.write(bytearray(name.encode('utf-8')))
                f.write('#')
                f.write(bytearray(claim_id.encode('utf-8')))
                f.write('\n')
    except Exception as err:
        xbmcgui.Dialog().notification(get_string(30104), str(err), xbmcgui.NOTIFICATION_ERROR)

def load_playlist(name):
    items = []
    try:
        with xbmcvfs.File(get_profile_path(name + '.list'), 'r') as f:
            lines = f.readBytes()
    except Exception:
        pass
    lines = lines.decode('utf-8')
    for line in lines.split('\n'):
        if line != '':
            items.append(line)
    return items

def save_playlist(name, items):
    try:
        with xbmcvfs.File(get_profile_path(name + '.list'), 'w') as f:
            for item in items:
                f.write(bytearray(item.encode('utf-8')))
                f.write('\n')
    except Exception as err:
        xbmcgui.Dialog().notification(get_string(30104), str(err), xbmcgui.NOTIFICATION_ERROR)

def odysee_init():

    """ Initiate Odysee Login """

    if odysee.has_login_details() and not odysee.auth_token:
        odysee.user_new()

    if odysee.has_login_details() and odysee.auth_token and not odysee.signed_in:
        if odysee.user_signin():
            odysee.signed_in = 'True'
            ADDON.setSetting( 'signed_in', odysee.signed_in )

odysee_init()

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

def add_channel_sub(uri):

    """ adds an Odysee subscription """

    uri = deserialize_uri(uri)
    channel_name = uri.split('#')[0]
    claim_id = uri.split('#')[1]

    odysee.subscription_new(channel_name, claim_id)

def remove_channel_sub(uri):

    """ removes an Odysee subscription """

    uri = deserialize_uri(uri)
    claim_id = uri.split('#')[1]

    odysee.subscription_delete(claim_id)

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

    # check if we have a new login
    if odysee.has_login_details() and not odysee.auth_token:
        odysee.user_new()

    # checks if the odysee user is still logged in
    if odysee.has_login_details() and odysee.auth_token and odysee.signed_in:
        if not odysee.user_me():
            odysee.signed_in = 'False'
            ADDON.setSetting( 'signed_in', odysee.signed_in )

    # Try to login
    if odysee.has_login_details() and odysee.auth_token and not odysee.signed_in:
        if odysee.user_signin():
            odysee.signed_in = 'True'
            ADDON.setSetting( 'signed_in', odysee.signed_in )
        else:
            raise Exception('Unable to Login')

odysee_init()

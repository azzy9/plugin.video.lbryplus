# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

from resources.lib.odysee import *
from resources.lib.general import *

ADDON = xbmcaddon.Addon()

ODYSEE = Odysee()

def get_profile_path(rpath):

    """ Gets Profile Path """

    return translate_path(ADDON.getAddonInfo('profile') + rpath)

def get_additional_header():

    """ Gets header with token if user is signed in """

    if ODYSEE.has_login_details() and ODYSEE.signed_in:
        return {'x-lbry-auth-token': ODYSEE.auth_token}
    return {}

def get_stream_headers():

    """ Gets stream headers - required for some videos otherwise will return a 401 error """

    return '|Referer=https://odysee.com/'

def load_channel_subs():

    """ Gets Followed channels from Odysee """

    channels = []
    if ODYSEE.has_login_details() and ODYSEE.signed_in:

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

    ODYSEE.subscription_new(channel_name, claim_id)

def remove_channel_sub(uri):

    """ removes an Odysee subscription """

    uri = deserialize_uri(uri)
    claim_id = uri.split('#')[1]

    ODYSEE.subscription_delete(claim_id)

def load_playlist(name):

    """ Loads playlist """

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

    """ Saves playlist """

    try:
        with xbmcvfs.File(get_profile_path(name + '.list'), 'w') as f:
            for item in items:
                f.write(bytearray(item.encode('utf-8')))
                f.write('\n')
    except Exception as err:
        xbmcgui.Dialog().notification(get_string(30104), str(err), xbmcgui.NOTIFICATION_ERROR)

def get_wallet_address():

    """ gets wallet address for Odysee """

    wallet_address = False

    if ODYSEE.has_login_details() and ODYSEE.signed_in:

        wallet_address = call_rpc(
            'address_unused',
            {},
            additional_headers=get_additional_header()
        )[ 'result' ]

    return wallet_address

def get_wallet_balance():

    """ gets wallet balance for Odysee """

    wallet_balance = False

    if ODYSEE.has_login_details() and ODYSEE.signed_in:

        wallet_balance = call_rpc(
            'wallet_balance',
            {},
            additional_headers=get_additional_header()
        )[ 'available' ]

    return wallet_balance

def odysee_init():

    """ Initiate Odysee Login """

    # check if we have a new login
    if ODYSEE.has_login_details() and not ODYSEE.auth_token:
        ODYSEE.user_new()

    # checks if the odysee user is still logged in
    if ODYSEE.has_login_details() and ODYSEE.auth_token and ODYSEE.signed_in:
        if not ODYSEE.user_me():
            ODYSEE.signed_in = 'False'
            ADDON.setSetting( 'signed_in', ODYSEE.signed_in )

    # Try to login
    if ODYSEE.has_login_details() and ODYSEE.auth_token and not ODYSEE.signed_in:
        if ODYSEE.user_signin():
            ODYSEE.signed_in = 'True'
            ADDON.setSetting( 'signed_in', ODYSEE.signed_in )
        else:
            raise Exception('Unable to Login')

odysee_init()

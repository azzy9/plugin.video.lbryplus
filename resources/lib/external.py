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

def get_preferences():

    """ method to get preferences from Odysee """

    preferences = {}

    if ODYSEE.has_login_details() and ODYSEE.signed_in:

        preferences = call_rpc(
            'preference_get', {}, additional_headers=get_additional_header()
        )

    return preferences

def load_channel_subs():

    """ Gets Followed channels from Odysee """

    channels = []

    subscriptions = get_preferences().get( 'shared', {} ).get( 'value', {} )\
        .get( 'subscriptions', False )

    if subscriptions:
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

def load_playlist( name ):

    """ Gets from playlist """

    #TODO: ability to get from other Odysee playlists

    items = []

    playlist = get_preferences().get( 'shared', {} ).get( 'value', {} )\
        .get( 'builtinCollections', {} ).get( 'watchlater', False )

    if playlist and playlist.get( 'itemCount', 0 ) > 0:
        for uri in playlist['items']:
            items.append(uri)

    return items

def save_playlist( name, items ):

    """ Saves playlist """

    #TODO: ability to save to other Odysee playlists

    preferences = get_preferences()

    playlist = get_preferences().get( 'shared', {} ).get( 'value', {} )\
        .get( 'builtinCollections', {} ).get( 'watchlater', False )

    # make sure playlist exists first
    if playlist:

        preferences[ 'shared' ][ 'value' ][ 'builtinCollections' ][ 'watchlater' ][ 'itemCount' ] = len( items )
        preferences[ 'shared' ][ 'value' ][ 'builtinCollections' ][ 'watchlater' ][ 'items' ] = items

        if ODYSEE.has_login_details() and ODYSEE.signed_in:

            preference_set = call_rpc(
                'preference_set',
                {'key':'shared', 'value': preferences[ 'shared' ] },
                additional_headers=get_additional_header()
            )


def get_wallet_address():

    """ gets wallet address for Odysee """

    wallet_address = False

    if ODYSEE.has_login_details() and ODYSEE.signed_in:

        wallet_address = call_rpc(
            'address_unused',
            {},
            additional_headers=get_additional_header()
        )

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

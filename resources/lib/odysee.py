"""
Main Odysee integration class
Created by Azzy9
"""

import email
import xbmc, xbmcaddon
from resources.lib.general import *

ADDON = xbmcaddon.Addon()

import json

class odysee:

    API_URL = 'https://api.odysee.com'

    signed_in = ''
    email = ''
    password = ''
    auth_token = ''
    device_id = ''

    # Construct to get the saved details
    def __init__( self ):
        self.details_load()

    # get the saved login details
    def details_load( self ):

        self.signed_in = ADDON.getSetting( 'signed_in' )
        self.email = ADDON.getSetting( 'email' )
        self.password = ADDON.getSetting( 'password' )
        self.auth_token = ADDON.getSetting( 'auth_token' )
        self.device_id = ADDON.getSetting( 'device_id' )

        # a device id is required
        if not self.device_id:
            self.device_id = self.generate_id().decode("utf-8")
            ADDON.setSetting( 'device_id', self.device_id )

    # if there is login details
    def has_login_details( self ):
        return ( self.email and self.password )

    # new user login to get auth token which can then be used to login
    def user_new( self ):
        data = {
            'auth_token': '',
            'language': 'en',
            'app_id': self.device_id,
        }
        result = request_get( self.API_URL + '/user/new', data=data )
        if result:
            result = json.loads(result)
            if result and result[ 'success' ]:
                self.auth_token = result[ 'data' ][ 'auth_token' ]
                ADDON.setSetting( 'auth_token', self.auth_token )
                return self.auth_token

    def user_exists( self, email ):
        data = {
            'auth_token': self.auth_token,
            'email': email,
        }
        result = request_get( self.API_URL + '/user/exists', data=data )
        if result:
            result = json.loads(result)
            return result and result[ 'success' ]
        return False

    def user_signin( self ):

        if self.user_exists( self.email ):
            data = {
                'auth_token': self.auth_token,
                'email': self.email,
                'password': self.password,
            }
            result = request_get( self.API_URL + '/user/signin', data=data )
            if result:
                result = json.loads(result)
                return result and result[ 'success' ]
        return False

    def user_me( self ):
        result = request_get( self.API_URL + '/user/me', data=data )

    def locale_get( self ):
        result = request_get( self.API_URL + '/locale/get', data=data )

    def notification_list( self ):
        result = request_get( self.API_URL + '/notification/list', data=data )

    def generate_id( self, num_bytes = 64 ):

        import secrets
        import hashlib
        from resources.lib.base58 import base58

        try:
            return base58.b58encode( hashlib.sha384(secrets.token_bytes( num_bytes )).hexdigest() )[:66]
        except Exception:
            return ''
       

# -*- coding: utf-8 -*-

import json

import xbmcaddon

ADDON = xbmcaddon.Addon()

def search_history_load():

    """ loads search history """

    search_history = ADDON.getSetting('search_history')

    if search_history:
        try:
            search_history = json.loads( search_history )
            if search_history:
                search_history.reverse()
                return search_history
        except Exception:
            return []

    return []

def search_history_add( search_string ):

    """ add to search history """

    if search_string:

        search_history = search_history_load()

        # if exists, remove to ensure it get put at the end
        if search_string in search_history:
            search_history.remove(search_string)

        search_history.append(search_string)
        ADDON.setSetting('search_history', json.dumps( search_history ))

        return True

    return False

def search_history_remove( search_string ):

    """ remove from search history """

    if search_string:

        removed = False
        search_history = search_history_load()

        # if exists, remove
        if search_string in search_history:
            search_history.remove(search_string)
            removed = True

        ADDON.setSetting('search_history', json.dumps( search_history ))

        return removed

    return False

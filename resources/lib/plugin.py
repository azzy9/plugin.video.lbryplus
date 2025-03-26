# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc
import xbmcaddon
import xbmcgui
from xbmcplugin import addDirectoryItem, addDirectoryItems, endOfDirectory, setContent, setResolvedUrl

import routing
import time

from six.moves.urllib.parse import quote, unquote, quote_plus, unquote_plus

from resources.lib.exception import PluginException
from resources.lib.comments import CommentWindow, IS_LBRY_PROXY

ADDON = xbmcaddon.Addon()

ODYSEE_ENABLED = ADDON.getSetting( 'odysee_enable' ) == 'true'
ODYSEE_UPCOMING_ENABLED = ADDON.getSetting( 'upcoming_enabled' ) == 'true'

if ODYSEE_ENABLED:
    from resources.lib.external import *
else:
    from resources.lib.local import *
from resources.lib.general import *

if get_api_url() == '':
    raise Exception('Lbry API URL is undefined.')

# assure profile directory exists
profile_path = ADDON.getAddonInfo('profile')
if not xbmcvfs.exists(profile_path):
    xbmcvfs.mkdir(profile_path)

items_per_page = ADDON.getSettingInt('items_per_page')
nsfw = ADDON.getSettingBool('nsfw')

plugin = routing.Plugin()
ph = plugin.handle
setContent(ph, 'videos')
dialog = xbmcgui.Dialog()

def thumbnails_get( item, fallback = '' ):

    """ gets and sanitises thumbnails """

    thumbnail_url = item.get('value', {}).get('thumbnail',{}).get('url', fallback)
    cover_url = item.get('value', {}).get('cover',{}).get('url', thumbnail_url)

    IMAGE_OPTIMISE_SERVICE = ADDON.getSetting( 'image_optimise' )
    if IMAGE_OPTIMISE_SERVICE:

        IMAGE_OPTIMISE_SERVICE = unquote_plus( IMAGE_OPTIMISE_SERVICE )

        if thumbnail_url:
            thumbnail_url = IMAGE_OPTIMISE_SERVICE + quote_plus( thumbnail_url )

        if cover_url:
            cover_url = IMAGE_OPTIMISE_SERVICE + quote_plus( cover_url )

    #thumbnail_url = 'https://' + thumbnail_url.rsplit('https://', 1)[-1] or thumbnail_url
    #cover_url = 'https://' + cover_url.rsplit('https://', 1)[-1] or cover_url

    return { 'thumbnail': thumbnail_url, 'cover': cover_url }

def to_video_listitem(item, playlist='', channel='', repost=None):

    line_item_title = item['value']['title'] if 'title' in item['value'] else item['file_name'] if 'file_name' in item else ''

    # inform user of members only video
    if 'c:members-only' in item.get('value',{}).get('tags', {}):
        line_item_title += ' (Members Only)'

    line_item = xbmcgui.ListItem(line_item_title)
    line_item.setProperty('IsPlayable', 'true')

    thumbnails = thumbnails_get(item)

    line_item.setArt({
        'thumb': thumbnails[ 'thumbnail' ],
        'poster': thumbnails[ 'thumbnail' ],
        'fanart': thumbnails[ 'cover' ],
    })

    info_labels = {}
    menu = []
    plot = ''

    # adds information context menu
    info_labels['mediatype'] = 'tvshow'

    if 'description' in item['value']:
        plot = item['value']['description']
    if 'author' in item['value']:
        info_labels['writer'] = item['value']['author']
    elif 'channel_name' in item:
        info_labels['writer'] = item['channel_name']
    if 'timestamp' in item:
        timestamp = time.localtime(item['timestamp'])
        info_labels['year'] = timestamp.tm_year
        info_labels['premiered'] = time.strftime('%Y-%m-%d',timestamp)
    if 'video' in item['value'] and 'duration' in item['value']['video']:
        info_labels['duration'] = str(item['value']['video']['duration'])

    if playlist == '':
        if 'signing_channel' in item and 'name' in item['signing_channel']:
            comment_uri = item['signing_channel']['name'] + '#' + item['signing_channel']['claim_id'] + '#' + item['claim_id']
            menu.append((
                get_string(30238), 'RunPlugin(%s)' % plugin.url_for(plugin_comment_show, uri=serialize_uri(comment_uri))
            ))

        menu.append((
            get_string(30212) % get_string(30211), 'RunPlugin(%s)' % plugin.url_for(plugin_playlist_add, name=quote(get_string(30211)), uri=serialize_uri(item))
        ))
    else:
        menu.append((
            get_string(30213) % get_string(30211), 'RunPlugin(%s)' % plugin.url_for(plugin_playlist_del, name=quote(get_string(30211)), uri=serialize_uri(item))
        ))

    menu.append((
        get_string(30208), 'RunPlugin(%s)' % plugin.url_for(claim_download, uri=serialize_uri(item))
    ))

    if 'signing_channel' in item and 'name' in item['signing_channel']:
        ch_name = item['signing_channel']['name']
        #ch_claim = item['signing_channel']['claim_id']
        ch_title = ''
        if 'value' in item['signing_channel'] and 'title' in item['signing_channel']['value']:
            ch_title = item['signing_channel']['value']['title']

        plot = '[B]' + (ch_title if ch_title.strip() != '' else ch_name) + '[/B]\n' + plot

        info_labels['studio'] = ch_name

        if channel == '':
            menu.append((
                get_string(30207) % ch_name, 'Container.Update(%s)' % plugin.url_for(lbry_channel, uri=serialize_uri(item['signing_channel']),page=1)
            ))
        menu.append((
            get_string(30205) % ch_name, 'RunPlugin(%s)' % plugin.url_for(plugin_follow, uri=serialize_uri(item['signing_channel']))
        ))

    if repost is not None:
        if 'signing_channel' in repost and 'name' in repost['signing_channel']:
            plot = (('[COLOR yellow]%s[/COLOR]\n' % get_string(30217)) % repost['signing_channel']['name']) + plot
        else:
            plot = ('[COLOR yellow]%s[/COLOR]\n' % get_string(30216)) + plot

    info_labels['plot'] = plot
    item_set_info( line_item, info_labels )
    line_item.addContextMenuItems(menu)

    return line_item

def result_to_itemlist(result, playlist='', channel=''):

    items = []

    for item in result:
        if not 'value_type' in item:
            xbmc.log(str(item))
            continue
        if item['value_type'] == 'stream' and 'stream_type' in item['value'] and item['value']['stream_type'] == 'video':
            # nsfw?
            if 'tags' in item['value']:
                if 'mature' in item['value']['tags'] and not nsfw:
                    continue

            line_item = to_video_listitem(item, playlist, channel)
            url = plugin.url_for(claim_play, uri=serialize_uri(item))

            items.append((url, line_item))
        elif item['value_type'] == 'repost' and 'reposted_claim' in item and item['reposted_claim']['value_type'] == 'stream' and item['reposted_claim']['value']['stream_type'] == 'video':
            stream_item = item['reposted_claim']
            # nsfw?
            if 'tags' in stream_item['value']:
                if 'mature' in stream_item['value']['tags'] and not nsfw:
                    continue

            line_item = to_video_listitem(stream_item, playlist, channel, repost=item)
            url = plugin.url_for(claim_play, uri=serialize_uri(stream_item))

            items.append((url, line_item))
        elif item['value_type'] == 'channel':
            line_item = xbmcgui.ListItem('[B]%s[/B] [I]#%s[/I]' % (item['name'], item['claim_id'][0:4]))
            line_item.setProperty('IsFolder','true')

            thumbnails = thumbnails_get(item)

            line_item.setArt({
                'thumb': thumbnails[ 'thumbnail' ],
                'poster': thumbnails[ 'thumbnail' ],
                'fanart': thumbnails[ 'cover' ],
            })

            url = plugin.url_for(lbry_channel, uri=serialize_uri(item),page=1)

            menu = []
            ch_name = item['name']
            menu.append((
                get_string(30205) % ch_name, 'RunPlugin(%s)' % plugin.url_for(plugin_follow, uri=serialize_uri(item))
            ))
            line_item.addContextMenuItems(menu)

            items.append((url, line_item, True))
        else:
            xbmc.log('ignored item, value_type=' + item['value_type'])
            xbmc.log('item name=' + item['name'])

    return items

def set_user_channel(channel_name, channel_id):
    ADDON.setSettingString('user_channel', "%s#%s" % (channel_name, channel_id))
    ADDON.setSettingString('user_channel_vis', "%s#%s" % (channel_name, channel_id[:5]))

@plugin.route('/clear_user_channel')
def clear_user_channel():
    ADDON.setSettingString('user_channel', '')
    ADDON.setSettingString('user_channel_vis', '')

@plugin.route('/select_user_channel')
def select_user_channel():

    progress_dialog = xbmcgui.DialogProgress()
    progress_dialog.create(get_string(30231))

    page = 1
    total_pages = 1
    items = []
    while page <= total_pages:
        if progress_dialog.iscanceled():
            break

        try:
            params = {'page' : page}
            result = call_rpc(get_api_url(), 'channel_list', params, errdialog=not IS_LBRY_PROXY)
            total_pages = max(result['total_pages'], 1) # Total pages returns 0 if empty
            if 'items' in result:
                items += result['items']
            else:
                break
        except Exception:
            pass

        page = page + 1
        progress_dialog.update(
            int(100.0*page/total_pages), get_string(30220) + ' %s/%s' % (page, total_pages)
        )

    selected_item = None

    if len(items) == 0:
        progress_dialog.update(100, get_string(30232)) # No owned channels found
        xbmc.sleep(1000)
        progress_dialog.close()
        return

    if len(items) == 1:
        progress_dialog.update(100, get_string(30233)) # Found single user
        xbmc.sleep(1000)
        progress_dialog.close()

        selected_item = items[0]
    else:
        progress_dialog.update(100, get_string(30234)) # Multiple users found
        xbmc.sleep(1000)
        progress_dialog.close()

        names = []
        for item in items:
            names.append(item['name'])

        selected_name_index = dialog.select(get_string(30239), names) # Post As

        if selected_name_index >= 0: # If not cancelled
            selected_item = items[selected_name_index]

    if selected_item:
        set_user_channel(selected_item['name'], selected_item['claim_id'])

@plugin.route('/')
def lbry_root():

    addDirectoryItem(ph, plugin.url_for(plugin_recent, page=1), xbmcgui.ListItem(get_string(30218)), True)
    if ODYSEE_ENABLED and ODYSEE_UPCOMING_ENABLED:
        addDirectoryItem(ph, plugin.url_for(plugin_upcoming, page=1), xbmcgui.ListItem('Upcoming'), True)
    addDirectoryItem(ph, plugin.url_for(plugin_follows), xbmcgui.ListItem(get_string(30200)), True)
    if ODYSEE_ENABLED:
        addDirectoryItem(ph, plugin.url_for(plugin_livestreams), xbmcgui.ListItem(get_string(30247)), True)
    #addDirectoryItem(ph, plugin.url_for(plugin_playlists), xbmcgui.ListItem(get_string(30210)), True)
    addDirectoryItem(ph, plugin.url_for(plugin_playlist, name=quote_plus(get_string(30211))), xbmcgui.ListItem(get_string(30211)), True)
    #addDirectoryItem(ph, plugin.url_for(lbry_new, page=1), ListItem(get_string(30202)), True)
    addDirectoryItem(ph, plugin.url_for(lbry_search), xbmcgui.ListItem(get_string(137)), True)

    if ODYSEE_ENABLED:

        wallet_balance = get_wallet_balance()

        if wallet_balance is not False:
            addDirectoryItem(ph, plugin.url_for(lbry_root), xbmcgui.ListItem('Wallet: ' + wallet_balance), False)

        if ODYSEE.has_login_details() and ODYSEE.signed_in:
            addDirectoryItem(ph, plugin.url_for(show_rewards), xbmcgui.ListItem('Rewards'), True)

    addDirectoryItem(ph, plugin.url_for(settings), xbmcgui.ListItem(get_string(5)), True)
    endOfDirectory(ph)

#@plugin.route('/playlists')
#def plugin_playlists():
#    addDirectoryItem(ph, plugin.url_for(plugin_playlist, name=quote_plus(get_string(30211))), xbmcgui.ListItem(get_string(30211)), True)
#    endOfDirectory(ph)

@plugin.route('/playlist/list/<name>')
def plugin_playlist(name):
    name = unquote_plus(name)
    uris = load_playlist(name)
    claim_info = call_rpc(get_api_url(), 'resolve', {'urls': uris})
    items = []
    for uri in uris:
        items.append(claim_info[uri])
    items = result_to_itemlist(items, playlist=name)
    addDirectoryItems(ph, items, items_per_page)
    endOfDirectory(ph)

@plugin.route('/playlist/add/<name>/<uri>')
def plugin_playlist_add(name,uri):
    name = unquote_plus(name)
    uri = deserialize_uri(uri)
    items = load_playlist(name)
    if not uri in items:
        items.append(uri)
    save_playlist(name, items)

@plugin.route('/playlist/del/<name>/<uri>')
def plugin_playlist_del(name,uri):
    name = unquote_plus(name)
    uri = deserialize_uri(uri)
    items = load_playlist(name)

    if not uri in items:
        uri = 'lbry://' + uri

    items.remove(uri)
    save_playlist(name, items)
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/follows')
def plugin_follows():
    channels = load_channel_subs()
    resolve_uris = []
    for (name,claim_id) in channels:
        resolve_uris.append(name+'#'+claim_id)
    channel_infos = call_rpc(get_api_url(), 'resolve', {'urls': resolve_uris})

    for (name,claim_id) in channels:
        uri = name+'#'+claim_id
        channel_info = channel_infos[uri]
        list_item = xbmcgui.ListItem(name)
        if not 'error' in channel_info:
            plot = ''
            if 'title' in channel_info['value'] and channel_info['value']['title'].strip() != '':
                plot = '[B]%s[/B]\n' % channel_info['value']['title']
            else:
                plot = '[B]%s[/B]\n' % channel_info['name']
            if 'description' in channel_info['value']:
                plot = plot + channel_info['value']['description']
            info_labels = { 'plot': plot }
            item_set_info( list_item, info_labels )

            thumbnails = thumbnails_get(channel_info)

            list_item.setArt({
                'thumb': thumbnails[ 'thumbnail' ],
                'poster': thumbnails[ 'thumbnail' ],
                'fanart': thumbnails[ 'cover' ],
            })
        menu = []
        menu.append((
            get_string(30206) % name, 'RunPlugin(%s)' % plugin.url_for(plugin_unfollow, uri=serialize_uri(uri))
        ))
        list_item.addContextMenuItems(menu)
        addDirectoryItem(ph, plugin.url_for(lbry_channel, uri=serialize_uri(uri), page=1), list_item, True)
    endOfDirectory(ph)

@plugin.route('/recent/<page>')
def plugin_recent(page):

    page = int(page)
    channels = load_channel_subs()
    channel_ids = []

    for( name, claim_id ) in channels:
        channel_ids.append(claim_id)

    # first page we check and show current subscribed live streams
    if page == 1:
        if ODYSEE_ENABLED and \
            ODYSEE.has_login_details() and \
            ODYSEE.signed_in:

            livestreams = ODYSEE.livestream_subscribed( channel_ids )

            if livestreams:
                urls = []
                for stream in livestreams:
                    if stream['ActiveClaim']['CanonicalURL']:
                        urls.append(stream['ActiveClaim']['CanonicalURL'])
                claim_info = call_rpc(get_api_url(), 'resolve', {'urls': urls})

                for stream in livestreams:
                    if stream['Live']:
                        info = claim_info.get( stream['ActiveClaim']['CanonicalURL'], {} )
                        list_item = xbmcgui.ListItem( '[COLOR red](Live)[/COLOR] ' + info.get('value', {}).get('title', '') + ' (' + str( stream['ViewerCount'] ) + ')' )
                        thumbnails = thumbnails_get( info, stream[ 'ThumbnailURL' ] )
                        list_item.setArt({
                            'thumb': thumbnails[ 'thumbnail' ],
                            'poster': thumbnails[ 'thumbnail' ],
                            'fanart': thumbnails[ 'cover' ],
                        })
                        addDirectoryItem(ph, plugin.url_for(play_livestream, uri=quote(stream['ActiveClaim']['CanonicalURL'], safe='')), list_item)

    query = {
        'page': page,
        'page_size': items_per_page,
        'order_by': 'release_time',
        'channel_ids': channel_ids,
        'has_source': 'true',
        'claim_type': ['stream','repost','channel']
    }

    if not ADDON.getSettingBool('server_filter_disable'):
        query['stream_types'] = ['video']

    result = call_rpc(get_api_url(), 'claim_search', query)
    items = result_to_itemlist(result['items'])
    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(plugin_recent, page=page+1), xbmcgui.ListItem(get_string(30203)), True)
    endOfDirectory(ph)

@plugin.route('/upcoming/<page>')
def plugin_upcoming(page):

    page = int(page)
    channels = load_channel_subs()
    channel_ids = []

    for( name, claim_id ) in channels:
        channel_ids.append(claim_id)

    query = {
        'page': page,
        'page_size': items_per_page,
        'claim_type':['stream'],
        'any_tags': ['c:scheduled-livestream'],
        'order_by': ['^release_time'],
        'has_no_source': True,
        'channel_ids': channel_ids,
        'release_time': ['>' + str( int(time.time()) - 600 )],
        'remove_duplicates': True
    }

    # get upcoming livestream
    result = call_rpc(get_api_url(), 'claim_search', query)

    # sleep to stop getting errors
    xbmc.sleep(1000)
    query.pop('has_no_source')
    query[ 'any_tags' ] = ['c:scheduled:show']
    query[ 'has_source' ] = True

    # get scheduled videos
    result2 = call_rpc(get_api_url(), 'claim_search', query)

    if result2['items']:
        for item in result2['items']:
            result['items'].append(item)

    items = []
    if result['items']:
        for item in result['items']:
            
            item_details = item.get( 'value', False )
            if item_details:

                line_item_title = ''
                channel = item.get( 'signing_channel', {} ).get( 'value', {} ).get( 'title', False )
                if channel:
                    line_item_title += '[COLOR gold]' + channel + "[/COLOR]: "
                line_item_title += item_details.get('title', '')

                info_labels = {}
                # adds information context menu
                info_labels['mediatype'] = 'tvshow'

                if 'description' in item_details:
                    info_labels['plot'] = item_details['description']
                if 'release_time' in item_details:
                    timestamp = time.localtime(int(item_details['release_time']))
                    info_labels['year'] = timestamp.tm_year
                    info_labels['premiered'] = time.strftime('%Y-%m-%d',timestamp)

                    line_item_title += "\nLive at " + time.strftime('%Y-%m-%d %H:%M',timestamp)

                line_item = xbmcgui.ListItem( line_item_title )
                item_set_info( line_item, info_labels )
                thumbnails = thumbnails_get( item )

                line_item.setArt({
                    'thumb': thumbnails[ 'thumbnail' ],
                    'poster': thumbnails[ 'thumbnail' ],
                    'fanart': thumbnails[ 'cover' ],
                })
                items.append((plugin.url_for(plugin_upcoming, page=page), line_item, True))

    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(plugin_recent, page=page+1), xbmcgui.ListItem(get_string(30203)), True)
    endOfDirectory(ph)

    endOfDirectory(ph)

@plugin.route('/livestreams')
def plugin_livestreams():

    livestreams = ODYSEE.livestream_all()

    if livestreams:
        urls = []
        for stream in livestreams:
            if stream['ActiveClaim']['CanonicalURL']:
                urls.append(stream['ActiveClaim']['CanonicalURL'])
        claim_info = call_rpc(get_api_url(), 'resolve', {'urls': urls})

        for stream in livestreams:
            info = claim_info.get( stream['ActiveClaim']['CanonicalURL'], {} )
            list_item = xbmcgui.ListItem( info.get('value', {}).get('title', '') + ' (' + str( stream['ViewerCount'] ) + ')' )
            thumbnails = thumbnails_get( info, stream[ 'ThumbnailURL' ] )
            list_item.setArt({
                'thumb': thumbnails[ 'thumbnail' ],
                'poster': thumbnails[ 'thumbnail' ],
                'fanart': thumbnails[ 'cover' ],
            })
            addDirectoryItem(ph, plugin.url_for(play_livestream, uri=quote(stream['ActiveClaim']['CanonicalURL'], safe='')), list_item)
    endOfDirectory(ph)

@plugin.route('/comments/show/<uri>')
def plugin_comment_show(uri):
    params = deserialize_uri(uri).split('#')
    CommentWindow(
        channel_name=params[0],
        channel_id=params[1],
        claim_id=params[2]
    )

@plugin.route('/follows/add/<uri>')
def plugin_follow(uri):
    add_channel_sub(uri)

@plugin.route('/follows/del/<uri>')
def plugin_unfollow(uri):
    remove_channel_sub(uri)
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/new/<page>')
def lbry_new(page):
    page = int(page)
    query = {'page': page, 'page_size': items_per_page, 'order_by': 'release_time'}
    if not ADDON.getSettingBool('server_filter_disable'):
        query['stream_types'] = ['video']
    result = call_rpc(get_api_url(), 'claim_search', query)
    items = result_to_itemlist(result['items'])
    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(lbry_new, page=page+1), xbmcgui.ListItem(get_string(30203)), True)
    endOfDirectory(ph)

@plugin.route('/channel/<uri>')
def lbry_channel_landing(uri):
    lbry_channel(uri,1)

@plugin.route('/channel/<uri>/<page>')
def lbry_channel(uri,page):
    uri = deserialize_uri(uri)
    page = int(page)
    query = {
        'page': page,
        'page_size': items_per_page,
        'order_by': 'release_time',
        'channel': uri,
        'has_source': 'true',
        'claim_type': ['stream','repost','channel']
    }
    if not ADDON.getSettingBool('server_filter_disable'):
        query['stream_types'] = ['video']
    result = call_rpc(get_api_url(), 'claim_search', query)
    items = result_to_itemlist(result['items'], channel=uri)
    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(lbry_channel, uri=serialize_uri(uri), page=page+1), xbmcgui.ListItem(get_string(30203)), True)
    endOfDirectory(ph)

@plugin.route('/search')
def lbry_search():
    query = dialog.input(get_string(30209))
    lbry_search_pager(quote_plus(query), 1)

@plugin.route('/search/<query>/<page>')
def lbry_search_pager(query, page):
    query = unquote_plus(query)
    page = int(page)
    if query != '':
        params = {
            'text': query,
            'page': page,
            'page_size': items_per_page,
            'order_by': 'release_time'
        }
        #always times out on server :(
        #if not ADDON.getSettingBool('server_filter_disable'):
        #    params['stream_types'] = ['video']
        result = call_rpc(get_api_url(), 'claim_search', params)
        items = result_to_itemlist(result['items'])
        addDirectoryItems(ph, items, result['page_size'])
        total_pages = int(result['total_pages'])
        if total_pages > 1 and page < total_pages:
            addDirectoryItem(ph, plugin.url_for(lbry_search_pager, query=quote_plus(query), page=page+1), xbmcgui.ListItem(get_string(30203)), True)
        endOfDirectory(ph)
    else:
        endOfDirectory(ph, False)

@plugin.route('/rewards')
def show_rewards():

    """ Shows rewards """

    rewards = ODYSEE.reward_list()

    current_url = plugin.url_for(show_rewards)

    if rewards:
        for reward in reversed(rewards):

            reward_url = current_url
            if reward[ 'claim_code' ]:
                reward_url = plugin.url_for(claim_reward, reward_type=reward[ 'reward_type' ], claim_code=reward[ 'claim_code' ])

            reward_title = reward[ 'reward_title' ] + ': ' + str( reward[ 'reward_amount' ] )

            if reward[ 'id' ] > 0:
                reward_title += ' (Claimed ' + reward[ 'created_at' ].replace( 'T', ' ' ).replace( 'Z', '' ) + ')'

            addDirectoryItem(ph, reward_url, xbmcgui.ListItem( reward_title ), False)

    endOfDirectory(ph)

@plugin.route('/claim_reward/<reward_type>/<claim_code>')
def claim_reward(reward_type, claim_code):

    """ Try to claim reward """

    wallet_address = get_wallet_address()

    if wallet_address is not False:
        reward_claimed = ODYSEE.reward_claim( reward_type, wallet_address, claim_code )

        if reward_claimed is not False:
            if reward_claimed[ 'success' ] is False:
                dialog.notification('Claim Reward', reward_claimed[ 'error' ], xbmcgui.NOTIFICATION_ERROR)
            else:
                dialog.notification('Claim Reward', 'Reward Claimed', xbmcgui.NOTIFICATION_INFO)

def user_payment_confirmed(claim_info):
    # paid for claim already?
    purchase_info = call_rpc(get_api_url(), 'purchase_list', {'claim_id': claim_info['claim_id']})
    if len(purchase_info['items']) > 0:
        return True

    account_list = call_rpc(get_api_url(), 'account_list')
    for account in account_list['items']:
        if account['is_default']:
            balance = float(str(account['satoshis'])[:-6]) / float(100)
    dtext = get_string(30214) % (float(claim_info['value']['fee']['amount']), str(claim_info['value']['fee']['currency']))
    dtext = dtext + '\n\n' + get_string(30215) % (balance, str(claim_info['value']['fee']['currency']))
    return dialog.yesno(get_string(30204), dtext)

@plugin.route('/play/<uri>')
def claim_play(uri):

    """ Method to play video """

    uri = deserialize_uri(uri)

    claim_info = call_rpc(get_api_url(), 'resolve', {'urls': uri})[uri]
    if 'error' in claim_info:
        dialog.notification(get_string(30102), claim_info['error']['name'], xbmcgui.NOTIFICATION_ERROR)
        return

    if 'fee' in claim_info['value']:
        if claim_info['value']['fee']['currency'] != 'LBC':
            dialog.notification(get_string(30204), get_string(30103), xbmcgui.NOTIFICATION_ERROR)
            return

        if not user_payment_confirmed(claim_info):
            return

    if ODYSEE_ENABLED and ODYSEE.signed_in and ADDON.getSetting( 'file_view_inform' ) == 'true':
        # tell Odysee we are viewing the file, this is used for claiming the reward
        ODYSEE.file_view(
            uri,
            claim_info['txid'] + ':0',
            claim_info['claim_id']
        )

    result = call_rpc(get_api_url(), 'get', {'uri': uri, 'save_file': False})
    stream_url = result['streaming_url'].replace('0.0.0.0','127.0.0.1')

    # Use HTTP
    if ADDON.getSetting('useHTTP') == 'true':
        stream_url = stream_url.replace('https://', 'http://', 1) + get_stream_headers()

    (url, list_item) = result_to_itemlist([claim_info])[0]
    list_item.setPath(stream_url)
    setResolvedUrl(ph, True, list_item)

@plugin.route('/play/livestream/<uri>')
def play_livestream(uri):

    """ Method to play live livestream """

    canonical_url = unquote(uri)

    if canonical_url:

        claim_info = call_rpc(get_api_url(), 'resolve', {'urls': [canonical_url]})
        info = claim_info.get( canonical_url, {} )

        stream = ODYSEE.livestream_is_live( info[ 'signing_channel' ][ 'claim_id' ] )

        stream_url = stream['VideoURL'].replace('master.','live.')

        # Use HTTP
        if ADDON.getSetting('useHTTP') == 'true':
            stream_url = stream_url.replace('https://', 'http://', 1) + get_stream_headers()

        list_item = xbmcgui.ListItem( info.get('value', {}).get('title', '') )
        thumbnails = thumbnails_get( info, stream[ 'ThumbnailURL' ] )
        list_item.setArt({
            'thumb': thumbnails[ 'thumbnail' ],
            'poster': thumbnails[ 'thumbnail' ],
            'fanart': thumbnails[ 'cover' ],
        })

        if '.m3u8' in stream_url:
            xbmc.Player().play(stream_url, list_item)
        else:
            setResolvedUrl(ph, True, list_item)

@plugin.route('/download/<uri>')
def claim_download(uri):
    uri = deserialize_uri(uri)

    claim_info = call_rpc(get_api_url(), 'resolve', {'urls': uri})[uri]
    if 'error' in claim_info:
        dialog.notification(get_string(30102), claim_info['error']['name'], xbmcgui.NOTIFICATION_ERROR)
        return

    if 'fee' in claim_info['value']:
        if claim_info['value']['fee']['currency'] != 'LBC':
            dialog.notification(get_string(30204), get_string(30103), xbmcgui.NOTIFICATION_ERROR)
            return

        if not user_payment_confirmed(claim_info):
            return

    call_rpc(get_api_url(), 'get', {'uri': uri, 'save_file': True})

@plugin.route('/settings')
def settings():

    """ Method to open settings menu """

    ADDON.openSettings()

@plugin.route('/session/reset/<notify>')
def session_reset(notify):

    """ Resets the Odysee session """

    ADDON.setSetting( 'auth_token', '' )
    ADDON.setSetting( 'signed_in', '' )
    ADDON.setSetting( 'device_id', '' )

    if notify == 'notify':
        dialog.notification('Session', 'Session has been reset', xbmcgui.NOTIFICATION_INFO)

@plugin.route('/login/test')
def login_test():

    """ Method that resets session, then tests the login """

    response_str = ''

    session_reset(False)

    if not ODYSEE_ENABLED:

        response_str = 'Odysee not enabled - please save settings first before running'

    else:

        if ODYSEE.has_login_details():

            ODYSEE.ensure_device_id()

            # check and test current login
            if ODYSEE.auth_token and ODYSEE.signed_in and ODYSEE.user_me():
                response_str = 'Valid login already detected'
            else:

                xbmc.sleep( 1000 )

                if not ODYSEE.user_exists( ODYSEE.email ):
                    response_str = 'User does not exist?'
                else:
                    if ODYSEE.user_new() == '':
                        response_str = 'Unable to get auth token from Odysee'
                    else:
                        if not ODYSEE.user_signin():
                            response_str = 'Login Failed - Incorrect details?'
                        else:
                            response_str = 'Login Successful - Session has been set'
                            ODYSEE.signed_in = 'True'
                            ADDON.setSetting( 'signed_in', ODYSEE.signed_in )

        else:
            response_str = 'No details detected - please save login details first before running'

    dialog.notification(
        'Login Test',
        response_str,
        xbmcgui.NOTIFICATION_INFO
    )

def run():

    """ Run the plugin """

    try:
        plugin.run()
    except PluginException as err:
        xbmc.log("PluginException: " + str( err ))

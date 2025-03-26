import xbmcgui

from resources.lib.general import *
from resources.lib.exception import *

IS_LBRY_PROXY = ( 'api.na-backend.odysee.com' in get_api_url() )

class CommentWindowXML(xbmcgui.WindowXML):

    COMMENT_API_URL = 'https://comments.odysee.com/api/v2'

    def __init__(self, *args, **kwargs):
        self.channel_name = kwargs['channel_name']
        self.channel_id = kwargs['channel_id']
        self.claim_id = kwargs['claim_id']
        self.last_selected_position = -1
        xbmcgui.WindowXML.__init__(self, args, kwargs)

    def onInit(self):
        self.refresh()

    def get_user_channel(self):
        user_channel_str = ADDON.getSettingString('user_channel')
        if user_channel_str:
            toks = user_channel_str.split('#')
            if len(toks) == 2:
                return (toks[0], toks[1])
        return None

    def onAction(self, action):

        if action == xbmcgui.ACTION_CONTEXT_MENU:
            # Commenting is not supported
            if IS_LBRY_PROXY:
                ret = dialog.contextmenu([get_string(30240)]) # Only allow refreshing
                if ret == 0:
                    self.refresh()
                return

            user_channel = self.get_user_channel()

            # No user channel. Allow user to select an account or refresh.
            if not user_channel:
                ret = dialog.contextmenu([get_string(30240)])
                if ret == 0:
                    self.refresh()
                return

            # User channel selected. Allow comment manipulation.
            if user_channel:
                ccl = self.get_comment_control_list()
                selected_pos = ccl.getSelectedPosition()
                item = ccl.getSelectedItem()

                menu = []
                offsets = []
                offset = 0
                invalid_offset = 10000
                if item:
                    comment_id = item.getProperty('id')

                    menu.append(get_string(30226)) # Like
                    offsets.append(0)

                    menu.append(get_string(30227)) # Dislike
                    offsets.append(1)

                    menu.append(get_string(30228)) # Clear Vote
                    offsets.append(2)

                    offset = 3
                else:
                    offsets.append(invalid_offset)
                    offsets.append(invalid_offset)
                    offsets.append(invalid_offset)
                    offset = 0

                menu.append(get_string(30221)) # New comment
                offsets.append(offset)
                offset = offset + 1

                if item:
                    menu.append(get_string(30222)) # Reply
                    offsets.append(offset)
                    offset = offset + 1

                    if item.getProperty('channel_id') == self.get_user_channel()[1]:

                        menu.append(get_string(30223)) # Edit
                        offsets.append(offset)
                        offset = offset + 1

                        menu.append(get_string(30224)) # Remove
                        offsets.append(offset)
                        offset = offset + 1
                    else:
                        offsets.append(invalid_offset)
                        offsets.append(invalid_offset)
                else:
                    offsets.append(invalid_offset)
                    offsets.append(invalid_offset)
                    offsets.append(invalid_offset)

                menu.append(get_string(30240)) # Refresh
                offsets.append(offset)

                ret = dialog.contextmenu(menu)

                if ret == offsets[0]: # Like
                    self.like(comment_id)
                    item.setProperty('my_vote', str(1))
                    self.refresh_label(item)

                elif ret == offsets[1]: # Dislike
                    self.dislike(comment_id)
                    item.setProperty('my_vote', str(-1))
                    self.refresh_label(item)

                elif ret == offsets[2]: # Clear Vote
                    self.neutral(comment_id, item.getProperty('my_vote'))
                    item.setProperty('my_vote', str(0))
                    self.refresh_label(item)

                elif ret == offsets[3]: # New Comment
                    comment = dialog.input(get_string(30221), type=xbmcgui.INPUT_ALPHANUM)
                    if comment:
                        comment_id = self.create_comment(comment)

                        # Remove 'No Comments' item
                        if ccl.size() == 1 and ccl.getListItem(0).getLabel() == get_string(30230):
                            ccl.reset()

                        # Add new comment item
                        ccl.addItem(self.create_list_item(comment_id, user_channel[0], user_channel[1], 0, 0, comment, 0, 1))
                        ccl.selectItem(ccl.size()-1)

                elif ret == offsets[4]: # Reply
                    comment = dialog.input(get_string(30222), type=xbmcgui.INPUT_ALPHANUM)
                    if comment:
                        comment_id = self.create_comment(comment, comment_id)

                        # Insert new item by copying the list (no XMBC method to allow a fast insertion).
                        newItems = []
                        for i in range(selected_pos+1):
                            newItems.append(self.copy_list_item(ccl.getListItem(i)))
                        newItems.append(self.create_list_item(comment_id, user_channel[0], user_channel[1], 0, 0, comment, int(item.getProperty('indent'))+1, 1))
                        for i in range(selected_pos+1, ccl.size()):
                            newItems.append(self.copy_list_item(ccl.getListItem(i)))

                        ccl.reset()
                        ccl.addItems(newItems)
                        ccl.selectItem(selected_pos+1)

                elif ret == offsets[5]: # Edit
                    id = item.getProperty('id')
                    comment = item.getProperty('comment')
                    comment = dialog.input(get_string(30223), type=xbmcgui.INPUT_ALPHANUM, defaultt=comment)
                    if comment:
                        self.edit_comment(id, comment)
                        item.setProperty('comment', comment)
                        self.refresh_label(item)

                elif ret == offsets[6]: # Change User
                    indentRemoved = item.getProperty('indent')
                    self.remove_comment(comment_id)
                    ccl.removeItem(selected_pos)

                    while True:
                        if selected_pos == ccl.size():
                            break
                        indent = ccl.getListItem(selected_pos).getProperty('indent')
                        if indent <= indentRemoved:
                            break
                        ccl.removeItem(selected_pos)

                    if selected_pos > 0:
                        ccl.selectItem(selected_pos-1)

                    if ccl.size() == 0:
                        ccl.addItem(xbmcgui.ListItem(label=get_string(30230)))

                elif ret == offsets[7]: # Refresh
                    self.refresh()

        else:
            xbmcgui.WindowXML.onAction(self, action)

        # If an action changes the selected item position refresh the label
        ccl = self.get_comment_control_list()
        if self.last_selected_position != ccl.getSelectedPosition():
            if self.last_selected_position >= 0 and self.last_selected_position < ccl.size():
                oldItem = ccl.getListItem(self.last_selected_position)
                if oldItem:
                    self.refresh_label(oldItem, False)
            newItem = ccl.getSelectedItem()
            if newItem:
                self.refresh_label(newItem, True)
            self.last_selected_position = ccl.getSelectedPosition()

    def fetch_comment_list(self, page):
        return call_rpc(
            self.COMMENT_API_URL,
            'comment.List',
            params={
                'page': page,
                'page_size': 50,
                'include_replies': True,
                'visible': False,
                'hidden': False,
                'top_level': False,
                'channel_name': self.channel_name,
                'channel_id': self.channel_id,
                'claim_id': self.claim_id,
                'sort_by': 0
            }
        )

    def fetch_react_list(self, comment_ids):
        user_channel = self.get_user_channel()
        params = {'comment_ids' : comment_ids }
        if user_channel:
            params['channel_name'] = user_channel[0]
            params['channel_id'] = user_channel[1]
            self.sign(user_channel[0], params)
        return call_rpc(self.COMMENT_API_URL, 'reaction.List', params=params)

    def refresh(self):
        self.last_selected_position = -1
        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(get_string(30219), get_string(30220) + ' 1')

        ccl = self.get_comment_control_list()

        page = 1
        result = self.fetch_comment_list(page)
        total_pages = result['total_pages']

        while page < total_pages:
            if progress_dialog.iscanceled():
                break
            progress_dialog.update(
                int(100.0*page/total_pages), get_string(30220) + " %s/%s" % (page + 1, total_pages)
            )
            page = page+1
            result['items'] += self.fetch_comment_list(page)['items']

        if 'items' in result:
            ccl.reset()
            items = result['items']

            # Grab the likes and dislikes.
            comment_ids = ''
            for item in items:
                comment_ids += item['comment_id'] + ','
            result = self.fetch_react_list(comment_ids)
            others_reactions = result['others_reactions']

            # Items are returned newest to oldest which implies that child comments are always before their parents.
            # Iterate from oldest to newest comments building up a pre-order traversal ordering of the comment tree.
            # Order the tree roots by decreasing score (likes-dislikes).

            sort_indices = []
            i = len(items)-1
            while i >= 0:
                item = items[i]
                comment_id = item['comment_id']
                if 'parent_id' in item and item['parent_id'] != 0:
                    # search for the parent in the sorted index list
                    for j in range(len(sort_indices)):
                        sorted_item = items[sort_indices[j][0]]
                        indent = sort_indices[j][1]
                        if sorted_item['comment_id'] == item['parent_id']: # found the parent
                            # Insert at the end of the subtree of the parent. Use the indentation to figure
                            # out where the end is.
                            while j+1 < len(sort_indices):
                                if sort_indices[j+1][1] > indent: # Item with index j+1 is in the child subtree
                                    j = j+1
                                else: # Item with index j+1 is not in the child subtree. Break and insert before this item.
                                    break
                            sort_indices.insert(j+1, (i, indent+1, 0))
                            break
                else:
                    reaction = others_reactions[comment_id]
                    likes = reaction['like']
                    dislikes = reaction['dislike']
                    score = likes-dislikes

                    j = 0
                    insert_index = len(sort_indices)
                    while j < len(sort_indices):
                        if sort_indices[j][1] == 0 and score > sort_indices[j][2]:
                            insert_index = j
                            break
                        j = j+1

                    sort_indices.insert(insert_index, (i, 0, score))

                i -= 1

            for (index,indent,score) in sort_indices:
                item = items[index]
                channel_name = item['channel_name']
                channel_id = item['channel_id']
                comment = item['comment']
                comment_id = item['comment_id']
                reaction = result['others_reactions'][comment_id]
                likes = reaction['like']
                dislikes = reaction['dislike']

                if 'my_reactions' in result:
                    my_reaction = result['my_reactions'][comment_id]
                    my_vote = my_reaction['like'] - my_reaction['dislike']
                else:
                    my_vote = 0

                ccl.addItem(
                    self.create_list_item(
                        comment_id, channel_name, channel_id, likes, dislikes, comment, indent, my_vote
                    )
                )
        else:
            if ccl.size() == 0:
                ccl.addItem(xbmcgui.ListItem(label=get_string(30230))) # No Comments

        progress_dialog.update(100)
        progress_dialog.close()

    def get_comment_control_list(self):
        return self.getControl(1)

    def create_list_item(self, comment_id, channel_name, channel_id, likes, dislikes, comment, indent, my_vote):
        li = xbmcgui.ListItem(label=self.create_label(channel_name, channel_id, likes, dislikes, comment, indent, my_vote))
        li.setProperty('id', comment_id)
        li.setProperty('channel_name', channel_name)
        li.setProperty('channel_id', channel_id)
        li.setProperty('likes', str(likes))
        li.setProperty('dislikes', str(dislikes))
        li.setProperty('comment', comment)
        li.setProperty('indent', str(indent))
        li.setProperty('my_vote', str(my_vote))
        return li

    def copy_list_item(self, li):

        """ Creates a copy of the line item """

        li_copy = xbmcgui.ListItem(label=li.getLabel())
        li_copy.setProperty('id', li.getProperty('id'))
        li_copy.setProperty('channel_name', li.getProperty('channel_name'))
        li_copy.setProperty('channel_id', li.getProperty('channel_id'))
        li_copy.setProperty('likes', li.getProperty('likes'))
        li_copy.setProperty('dislikes', li.getProperty('dislikes'))
        li_copy.setProperty('comment', li.getProperty('comment'))
        li_copy.setProperty('indent', li.getProperty('indent'))
        li_copy.setProperty('my_vote', li.getProperty('my_vote'))
        return li_copy

    def refresh_label(self, li, selected=True):
        li.getProperty('id')
        channel_name = li.getProperty('channel_name')
        channel_id = li.getProperty('channel_id')
        likes = int(li.getProperty('likes'))
        dislikes = int(li.getProperty('dislikes'))
        comment = li.getProperty('comment')
        indent = int(li.getProperty('indent'))
        my_vote = int(li.getProperty('my_vote'))
        li.setLabel(
            self.create_label(
                channel_name, channel_id, likes, dislikes, comment, indent, my_vote, selected
            )
        )

    def create_label(self, channel_name, channel_id, likes, dislikes, comment, indent, my_vote, selected=False):
        user_channel = self.get_user_channel()
        if user_channel and user_channel[1] == channel_id:
            color = 'red' if selected else 'green'
            channel_name = '[COLOR ' + color + ']' + channel_name + '[/COLOR]'

        if my_vote == 1:
            likes = '[COLOR green]' + str(likes+1) + '[/COLOR]'
            dislikes = str(dislikes)
        elif my_vote == -1:
            likes = str(likes)
            dislikes = '[COLOR green]' + str(dislikes+1) + '[/COLOR]'
        else:
            likes = str(likes)
            dislikes = str(dislikes)

        lilabel = channel_name + ' [COLOR orange]' + likes + '/' + dislikes \
            + '[/COLOR] [COLOR white]' + comment + '[/COLOR]'

        padding = ''
        for i in range(indent):
            padding += '   '
        lilabel = padding + lilabel

        return lilabel

    def sign(self, data, params):

        """ Sign data if a user channel is selected """

        user_channel = self.get_user_channel()
        if not user_channel:
            return None

        # assume data type is str
        if type(data) is not str:
            raise Exception('attempt to sign non-str type')

        bdata = bytes(data, 'utf-8')

        toHex = lambda x : "".join([format(c,'02x') for c in x])

        res =  call_rpc(
            get_api_url(),
            'channel_sign',
            params={'channel_id': user_channel[1], 'hexdata': toHex(bdata)}
        )
        params['signature'] = res['signature']
        params['signing_ts'] = res['signing_ts']

    def create_comment(self, comment, parent_id=None):
        user_channel = self.get_user_channel()
        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(get_string(30241), get_string(30242))
        params = { 'claim_id' : self.claim_id, 'comment' : comment, 'channel_id' : user_channel[1] }
        if parent_id:
            params['parent_id'] = parent_id
        self.sign(comment, params)
        res = call_rpc(self.COMMENT_API_URL, 'comment.Create', params)
        self.like(res['comment_id'])
        progress_dialog.close()
        return res['comment_id']

    def edit_comment(self, comment_id, comment):
        params = { 'comment_id' : comment_id, 'comment' : comment }
        self.sign(comment, params)
        return call_rpc(self.COMMENT_API_URL, 'comment.Edit', params)

    def remove_comment(self, comment_id):
        params = { 'comment_id' : comment_id }
        self.sign(comment_id, params)
        call_rpc(self.COMMENT_API_URL, 'comment.Abandon', params)

    def react(self, comment_id, current_vote=0, react_type=None):
        # No vote to clear
        if current_vote == '0' and react_type is None:
            return

        user_channel = self.get_user_channel()
        params = { 'comment_ids' : comment_id,
                'channel_name' : user_channel[0],
                'channel_id' : user_channel[1]
                }
        if type == 'like':
            params['clear_types'] = 'dislike'
            params['type'] = 'like'
        elif type == 'dislike':
            params['clear_types'] = 'like'
            params['type'] = 'dislike'
        else:
            params['remove'] = True
            params['type'] = 'dislike' if current_vote == '-1' else 'like'

        self.sign(user_channel[0], params)
        call_rpc(self.COMMENT_API_URL, 'reaction.React', params)

    def like(self, comment_id):
        self.react(comment_id, react_type='like')

    def dislike(self, comment_id):
        self.react(comment_id, react_type='dislike')

    def neutral(self, comment_id, current_vote):
        self.react(comment_id, current_vote=current_vote)

class CommentWindow:

    def __init__(self, channel_name, channel_id, claim_id):
        window = CommentWindowXML(
            'addon-lbry-comments.xml',
            xbmcaddon.Addon().getAddonInfo('path'),
            'Default',
            channel_name=channel_name,
            channel_id=channel_id,
            claim_id=claim_id
        )
        window.doModal()
        del window

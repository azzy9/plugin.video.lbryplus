# Kodi/XBMC plugin for LBRY and Odysee

This plugin is a fork from https://github.com/accumulator/plugin.video.lbry by accumulator.

This is a basic plugin for accessing [LBRY](https://lbry.com) content (video's only, for now).

This plugin can also get your followed channels and recent videos from Odysee by signing into your Odysee account.
This can be done in the Odysee section within the options of the plugin.

By default you don't need to install any extra software to start using this LBRY plugin, the plugin uses the API server provided by lbry.tv (https://api.lbry.tv/api/v1/proxy).

Alternatively, you can run your own API server and contribute to the LBRY network by hosting content data of videos you watched. This enables the 'Download' feature in the plugin, so you can watch videos uninterrupted or save the video to a local file. Also this enables wallet features like watching paid videos or tipping authors.

You will need to run `lbrynet` client (installation described here: https://github.com/lbryio/lbry-sdk) and have a bit of storage space available.

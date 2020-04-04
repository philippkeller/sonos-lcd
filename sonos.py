#!/usr/bin/env python

import soco
from timeit import default_timer as timer

TUNEIN_TEMPLATE = """
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
    xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
    xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="R:0/0/0" parentID="R:0/0" restricted="true">
        <dc:title>{title}</dc:title>
        <upnp:class>object.item.audioItem.audioBroadcast</upnp:class>
        <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
            {service}
        </desc>
    </item>
</DIDL-Lite>' """
TUNEIN_SERVICE = "SA_RINCON65031_"

class Sonos():
  def __init__(self, speakers=None):
    """
    in some setups (e.g. over VPN) then socos.discover()
    does not work, in this case do smth like:

    >>> import soco
    >>> s1 = soco.Soco("192.168.188.24")
    >>> s2 = soco.Soco("192.168.188.26")
    >>> sonos.Sonos([s1, s2])
    """
    self._speakers = []
    if speakers is None:
      speakers = soco.discover()
    for speaker in speakers:
      self._speakers.append((speaker.player_name, speaker))
    self._speakers = sorted(self._speakers)
    self._library = self._speakers[0][1].music_library

  def speakers(self):
    return [s[0] for s in self._speakers]

  def search(self, context, term, offset=0, max_items=7, debug=False):
    """
    context: albums, artists, titles, sonos_playlists
    """
    if debug:
      start = timer()

    if context == 'radio_stations':
      # search does not work for radio stations
      soco_res = self._library.get_favorite_radio_stations()
      res = []
      for i in soco_res:
        title, uri = i.title, i.get_uri()
        uri = uri.replace('&', '&amp;')
        metadata = TUNEIN_TEMPLATE.format(title=title, service=TUNEIN_SERVICE)
        res.append((title, (uri, metadata)))
    else:
      soco_res = self._library.get_music_library_information(context, search_term=term, 
          start=offset, max_items=7)
      res = [(i.title, i.get_uri()) for i in soco_res]

    if debug:
      print(f'search {context}: {timer() - start:.2f}')

    return res

  def play(self, speaker_number, uri):
    """
    speaker_number: index of `speakers()`
    uri: second item of `search_albums()`
    """
    _, s = self._speakers[speaker_number]
    if type(uri) == tuple:
      # tunein
      _uri, _meta = uri
      s.play_uri(_uri, _meta)
    else:
      s.play_uri(uri)

  def add_to_queue(self, speaker_number, uri):
    _, s = self._speakers[speaker_number]
    s.add_uri_to_queue(uri)

  def volume_play_as_string(self, speaker_number, debug=False):
    """
    return string representing play/pause and volume
    """
    _, s = self._speakers[speaker_number]
    if debug:
      start = timer()
    t = s.get_current_transport_info()

    play_pause = ''
    if t['current_transport_state'] == 'PAUSED_PLAYBACK':
      play_pause = "| | "
    elif t['current_transport_state'] == 'PLAYING':
      play_pause = u"\u25B6"
    elif t['current_transport_state'] == 'STOPPED':
      play_pause = "\u25A0"
    res = f'{play_pause} {s.volume}%'
    if debug:
      print(f'fetch status: {timer() - start}')
    return res

  def next(self, speaker_number):
    self._speakers[speaker_number][1].next()
  def previous(self, speaker_number):
    self._speakers[speaker_number][1].previous()

  def change_volume(self, speaker_number, diff):
    _, s = self._speakers[speaker_number]
    s.volume += diff

  def play_pause(self, speaker_number):
    """
    pause if playing, play if pausing
    """
    _, s = self._speakers[speaker_number]
    t = s.get_current_transport_info()
    if t['current_transport_state'] == 'PAUSED_PLAYBACK':
      s.play()
    elif t['current_transport_state'] == 'PLAYING':
      s.pause()

if __name__ == '__main__':
  s = Sonos()
  albums = s.search_albums('leonie')
  speakers = s.speakers()
  index = speakers.index('Weiss')
  s.play(index, albums[0][1])


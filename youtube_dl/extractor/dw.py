# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    merge_dicts,
    unified_strdate,
    url_or_none,
)
from ..compat import compat_urlparse


class DWIE(InfoExtractor):
    IE_NAME = 'dw'
    _VALID_URL = r'https?://(?:www\.)?dw\.com/(?:[^/]+/)+(?:av|e)-(?P<id>\d+)'
    _TESTS = [{
        # video
        'url': 'http://www.dw.com/en/intelligent-light/av-19112290',
        'md5': '7fbf91ee1d8fe842b55eabf3c4ba9387',
        'info_dict': {
            'id': '19112290',
            'ext': 'mp4',
            'title': 'Intelligent light',
            'description': 'md5:90e00d5881719f2a6a5827cb74985af1',
            'upload_date': '20160605',
            'uploader': 'DW.COM',
        }
    }, {
        # audio
        'url': 'http://www.dw.com/en/worldlink-my-business/av-19111941',
        'md5': '2814c9a1321c3a51f8a7aeb067a360dd',
        'info_dict': {
            'id': '19111941',
            'ext': 'mp3',
            'title': 'WorldLink: My business',
            'description': 'md5:bc9ca6e4e063361e21c920c53af12405',
            'upload_date': '20160311',
            'uploader': 'DW.COM',
        }
    }, {
        # DW documentaries, only last for one or two weeks
        'url': 'http://www.dw.com/en/documentaries-welcome-to-the-90s-2016-05-21/e-19220158-9798',
        'md5': '56b6214ef463bfb9a3b71aeb886f3cf1',
        'info_dict': {
            'id': '19274438',
            'ext': 'mp4',
            'title': 'Welcome to the 90s – Hip Hop',
            'description': 'Welcome to the 90s - The Golden Decade of Hip Hop',
            'upload_date': '20160521',
        },
        'skip': 'Video removed',
    }, {
        # video podcast
        'url': 'https://www.dw.com/en/under-construction-indonesias-new-capital-nusantara/av-63121733',
        'md5': '259a9318230c02ef5b38bb5e2a067109',
        'info_dict': {
            'id': '63121733',
            'ext': 'mp4',
            'title': 'Under construction: Indonesia\'s new capital Nusantara',
            'description': 'Indonesia\'s government wants to move the capital from Jakarta on the island of Java to the island of Borneo. Nearly $33 billion (€33 billion) will be spent building the new metropolis Nusantara. The relocation is expected to take decades.',
            'upload_date': '20220914',
            'uploader': 'DW.COM',
        }
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)
        hidden_inputs = self._hidden_inputs(webpage)
        upload_date = None
        if 'media_title' not in hidden_inputs:
            title = self._og_search_title(webpage)
            entries = self._parse_html5_media_entries(url, webpage, media_id, m3u8_entry_protocol='m3u8_native')
            for i, entry in enumerate(entries):
                entry['id'] = '%s_%d' % (media_id, i) if i > 0 else media_id
        else:
            title = hidden_inputs['media_title']
            media_id = hidden_inputs.get('media_id') or media_id

            direct_url = url_or_none(hidden_inputs.get('file_name'))
            if direct_url:
                formats = [{'url': hidden_inputs['file_name']}]
            else:
                formats = self._extract_smil_formats(
                    'http://www.dw.com/smil/v-%s' % media_id, media_id,
                    transform_source=lambda s: s.replace(
                        'rtmp://tv-od.dw.de/flash/',
                        'http://tv-download.dw.de/dwtv_video/flv/'))
            self._sort_formats(formats)

            upload_date = hidden_inputs.get('display_date')
            entries = [{
                'id': media_id,
                'thumbnail': url_or_none(hidden_inputs.get('preview_image')),
                'duration': int_or_none(hidden_inputs.get('file_duration')),
                'formats': formats,
            }]

        if not upload_date:
            upload_date = self._html_search_regex(
                r'<span[^>]+class="date">([0-9.]+)\s*\|', webpage,
                'upload date', default=None)
            upload_date = unified_strdate(upload_date)

        title = title.rsplit('|', 2)
        if not upload_date:
            upload_date = unified_strdate(title[-1].strip())
        title = title[0].strip()

        meta = {
            'title': title,
            'description': self._og_search_description(webpage),
            'upload_date': upload_date,
            'uploader': self._og_search_property('site_name', webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
        }
        if len(entries) == 1:
            return merge_dicts(entries[0], meta)
        return merge_dicts(self.playlist_result(entries, media_id), meta)


class DWArticleIE(InfoExtractor):
    IE_NAME = 'dw:article'
    _VALID_URL = r'https?://(?:www\.)?dw\.com/(?:[^/]+/)+a-(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.dw.com/en/no-hope-limited-options-for-refugees-in-idomeni/a-19111009',
        'md5': '8ca657f9d068bbef74d6fc38b97fc869',
        'info_dict': {
            'id': '19105868',
            'ext': 'mp4',
            'title': 'The harsh life of refugees in Idomeni',
            'description': 'md5:196015cc7e48ebf474db9399420043c7',
            'upload_date': '20160310',
        }
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        hidden_inputs = self._hidden_inputs(webpage)
        media_id = hidden_inputs['media_id']
        media_path = self._search_regex(r'href="([^"]+av-%s)"\s+class="overlayLink"' % media_id, webpage, 'media url')
        media_url = compat_urlparse.urljoin(url, media_path)
        return self.url_result(media_url, 'DW', media_id)

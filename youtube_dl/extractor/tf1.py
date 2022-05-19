# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    merge_dicts,
    parse_iso8601,
    try_get,
    unified_strdate,
    url_or_none,
)


class WatIE(InfoExtractor):
    _VALID_URL = r'(?:wat:|https?://(?:www\.)?wat\.tv/video/.*-)(?P<id>[0-9a-z]+)'
    IE_NAME = 'wat.tv'
    IE_DESC = 'Legacy video service formerly used by TF1 etc'
    _TESTS = [
        {
            'url': 'http://www.wat.tv/video/soupe-figues-l-orange-aux-epices-6z1uz_2hvf7_.html',
            'info_dict': {
                'id': '11713067',
                'ext': 'mp4',
                'title': 'Soupe de figues à l\'orange et aux épices',
                'description': 'Retrouvez l\'émission "Petits plats en équilibre", diffusée le 18 août 2014.',
                'upload_date': '20140819',
                'duration': 120,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'expected_warnings': ['HTTP Error 404'],
            'skip': 'This content is no longer available',
        },
        {
            'url': 'http://www.wat.tv/video/gregory-lemarchal-voix-ange-6z1v7_6ygkj_.html',
            'md5': 'b16574df2c3cd1a36ca0098f2a791925',
            'info_dict': {
                'id': '11713075',
                'ext': 'mp4',
                'title': 'Grégory Lemarchal, une voix d\'ange depuis 10 ans (1/3)',
                'upload_date': '20140816',
            },
            'expected_warnings': ["Ce contenu n'est pas disponible pour l'instant."],
            'skip': 'This content is no longer available',
        },
    ]
    _GEO_BYPASS = False

    def _call_api(self, program_id, video_id=None):
        return self._download_json(
            'https://mediainfo.tf1.fr/mediainfocombo/' + program_id,
            video_id or program_id, query={'context': 'MYTF1', 'pver': '4001000'})

    def _extract_video_info(self, video_data, video_id):

        video_info = video_data['media']

        error_desc = video_info.get('error_desc')
        if error_desc:
            if video_info.get('error_code') == 'GEOBLOCKED':
                self.raise_geo_restricted(error_desc, video_info.get('geoList'))
            raise ExtractorError(error_desc, expected=True)

        title = video_info['title']

        formats = []

        def extract_formats(manifest_urls):
            for f, f_url in manifest_urls.items():
                if not f_url:
                    continue
                if f in ('dash', 'mpd'):
                    formats.extend(self._extract_mpd_formats(
                        f_url.replace('://das-q1.tf1.fr/', '://das-q1-ssl.tf1.fr/'),
                        video_id, mpd_id='dash', fatal=False))
                elif f == 'hls':
                    formats.extend(self._extract_m3u8_formats(
                        f_url, video_id, 'mp4',
                        'm3u8_native', m3u8_id='hls', fatal=False))

        delivery = video_data.get('delivery') or {}
        extract_formats({delivery.get('format'): delivery.get('url')})
        if not formats:
            if delivery.get('drm'):
                raise ExtractorError('This video is DRM protected.', expected=True)
            manifest_urls = self._download_json(
                'http://www.wat.tv/get/webhtml/' + video_id, video_id, fatal=False)
            if manifest_urls:
                extract_formats(manifest_urls)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': video_info.get('preview'),
            'upload_date': unified_strdate(try_get(
                video_data, lambda x: x['mediametrie']['chapters'][0]['estatS4'])),
            'duration': int_or_none(video_info.get('duration')),
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # base 36? really?
        video_id = video_id if video_id.isdigit() and len(video_id) > 6 else compat_str(int(video_id, 36))

        video_data = self._call_api(video_id)
        result = self._extract_video_info(video_data, video_id)
        self._sort_formats(result['formats'])

        return result


class TF1IE(WatIE):
    IE_NAME = 'tf1.fr'
    IE_DESC = 'TF1 (etc) videos and catchup'
    _VALID_URL = r'https?://(?:www\.)?tf1\.fr/[^/]+/(?P<program_slug>[^/]+)/videos/(?P<id>[^/?&#]+)\.html'
    _TESTS = [{
        'url': 'https://www.tf1.fr/tmc/quotidien-avec-yann-barthes/videos/quotidien-premiere-partie-11-juin-2019.html',
        'info_dict': {
            'id': 'd7230468-39b8-4c54-a50b-8ca3e3660d6c',
            'ext': 'mp4',
            'title': 'md5:f392bc52245dc5ad43771650c96fb620',
            'description': 'md5:a02cdb217141fb2d469d6216339b052f',
            'upload_date': '20190611',
            'timestamp': 1560273989,
            'duration': 1738,
            # formerly 'Quotidien avec Yann Barthès'
            'series': 'Quotidien',
            'tags': ['intégrale', 'quotidien', 'Replay'],
        },
        'params': {
            # Sometimes wat serves the whole file with the --test option
            'skip_download': True,
            'format': 'bestvideo',
        },
    }, {
        'url': 'http://www.tf1.fr/tf1/koh-lanta/videos/replay-koh-lanta-22-mai-2015.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tf1.fr/hd1/documentaire/videos/mylene-farmer-d-une-icone.html',
        'only_matching': True,
    }, {
        # post-wat.tv episode
        'url': 'https://www.tf1.fr/tmc/quotidien-avec-yann-barthes/videos/quotidien-premiere-partie-du-17-mai-2022-71087892.html',
        'info_dict': {
            'id': 'fc8e953d-811c-4265-87dc-1a1d8d498cee',
            'ext': 'mp4',
            'title': 'Quotidien, première partie du 17 mai 2022',
            'description': 'md5:702b24a6c79ee5d1f21d28998b45abcc',
            'timestamp': 1652808399,
            'upload_date': '20220517',
            'series': 'Quotidien',
            'tags': list,
        },
        'params': {
            'skip_download': True,
            'format': 'bestvideo',
        },
    }]

    def _get_gql_data(self, program_slug, slug):
        video = self._download_json(
            'https://www.tf1.fr/graphql/web', slug, query={
                'id': '9b80783950b85247541dd1d851f9cc7fa36574af015621f853ab111a679ce26f',
                'variables': json.dumps({
                    'programSlug': program_slug,
                    'slug': slug,
                })
            }, fatal=False)
        return try_get(video, lambda x: x['data']['videoBySlug'], dict) or {}

    @staticmethod
    def _extract_gql(video):
        tags = []
        for tag in (video.get('tags') or []):
            label = tag.get('label')
            if not label:
                continue
            tags.append(label)

        decoration = video.get('decoration') or {}

        thumbnails = []
        for source in (try_get(decoration, lambda x: x['image']['sources'], list) or []):
            source_url = url_or_none(source.get('url'))
            if not source_url:
                continue
            thumbnails.append({
                'url': source_url,
                'width': int_or_none(source.get('width')),
            })

        return {
            'title': video.get('title'),
            'thumbnails': thumbnails,
            'description': decoration.get('description'),
            'timestamp': parse_iso8601(video.get('date')),
            'duration': int_or_none(try_get(video, lambda x: x['publicPlayingInfos']['duration'])),
            'tags': tags,
            'series': decoration.get('programLabel'),
            'season_number': int_or_none(video.get('season')),
            'episode_number': int_or_none(video.get('episode')),
        }

    def _old_real_extract(self, program_slug, slug):
        video = self._get_gql_data(program_slug, slug)
        wat_id = video['streamId']

        result = super(TF1IE, self)._real_extract('wat:' + wat_id)
        result.update(self._extract_gql(video))
        return result

    def _real_extract(self, url):
        program_slug, slug = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, slug)

        info = self._search_json_ld(webpage, slug, fatal=False) or {}

        program_id = info and self._search_regex(
            r'"embedUrl"\s*:\s*"https://[\w.]+/player/([\da-f-]{36})"',
            webpage, 'program id', fatal=False)
        if not program_id:
            apollo_state = self._search_regex(
                r'(?s)\b__APOLLO_STATE__\s*=\s*(\{.*?})\s*;?\s*</script',
                webpage, 'Apollo State', fatal=False)
            apollo_state = self._parse_json(apollo_state or '{}', slug, fatal=False)
            program_id = try_get(
                apollo_state,
                lambda x: x['ROOT_QUERY']['videoBySlug({"slug":"%s"})' % (slug, )]['__ref'], compat_str)
            program_id = self._search_regex(r'^Video:([\da-f-]{36})', program_id, 'program id', fatal=False)

        if not program_id:
            # last resort
            return self._old_real_extract(url, program_slug, slug)

        info.update({
            'id': program_id,
            'display_id': slug,
        })

        video_data = self._call_api(program_id, slug)

        result = self._extract_video_info(video_data, slug)
        self._sort_formats(result['formats'])

        gql = self._get_gql_data(program_slug, slug)

        return merge_dicts(info, self._extract_gql(gql), result)

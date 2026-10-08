# -*- coding: utf-8 -*-
"""Page metadata and story beats shared by the Markdown and HTML renderers."""
from __future__ import annotations
from .markup import encode_text, decode_text


class PageDoc:
    __slots__ = ('heading', 'info', 'recap', 'body_title', 'beats',
                 'info_title', 'meta', 'appendix')

    def __init__(self, heading, info, recap, body_title, beats,
                 info_title="关卡信息", meta=None, appendix=None):
        self.heading = heading
        self.info = list(info)
        self.recap = recap
        self.body_title = body_title
        self.beats = beats
        self.info_title = info_title
        self.meta = meta if meta is not None else {'recap': '', 'episode': '', 'title': ''}
        self.appendix = appendix

    def to_dict(self):
        """Encode localized text in the page JSON structure."""
        return encode_text({
            'heading': self.heading,
            'info_title': self.info_title,
            'info': self.info,
            'recap': self.recap,
            'body_title': self.body_title,
            'meta': self.meta,
            'appendix': self.appendix,
            'beats': self.beats,
        })

    @classmethod
    def from_dict(cls, d):
        d = decode_text(d)
        return cls(d['heading'], d['info'], d['recap'], d['body_title'],
                   d['beats'], info_title=d.get('info_title', '关卡信息'),
                   meta=d.get('meta'), appendix=d.get('appendix'))

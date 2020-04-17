#!/bin/sh

xgettext -d base -o locales/base.pot main.py
gsed --in-place locales/base.pot --expression='s/CHARSET/UTF-8/'
msgmerge --update locales/de/LC_MESSAGES/base.po locales/base.pot
msgmerge --update locales/en/LC_MESSAGES/base.po locales/base.pot
msgfmt -o locales/en/LC_MESSAGES/base.mo locales/en/LC_MESSAGES/base
msgfmt -o locales/de/LC_MESSAGES/base.mo locales/de/LC_MESSAGES/base

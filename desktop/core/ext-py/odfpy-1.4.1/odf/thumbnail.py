#!/usr/bin/python
# -*- coding: utf-8 -*-
# This contains a 104x128 px thumbnail in PNG format
# Downloaded from http://da.libreoffice.org/assets/Uploads/Da-Projekt_Billeder/IconLibreOffice.png
# Copyright information: Unless otherwise specified, all text and images on the
# http://da.libreoffice.org website are licensed under the Creative Commons
# Attribution-Share Alike 3.0 License. (As of 2013-01-09)

# Alternative download: http://commons.wikimedia.org/wiki/File:LibreOffice_icon_3.3.1_48_px.svg
import base64

iconstr = """\
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
AAAAAElFTkSuQmCC\
"""

def thumbnail():
    icon = base64.b64decode(iconstr)
    return icon

if __name__ == "__main__":
    icon = thumbnail()
    f = open("thumbnail.png","wb")
    f.write(icon)
    f.close()

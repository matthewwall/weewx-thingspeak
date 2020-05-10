# installer for ThinkSpeak
# Copyright 2014-2020 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)

from weecfg.extension import ExtensionInstaller


def loader():
    return ThingSpeakInstaller()


class ThingSpeakInstaller(ExtensionInstaller):
    def __init__(self):
        super(ThingSpeakInstaller, self).__init__(
            version="0.9",
            name='thingspeak',
            description='Upload weather data to ThingSpeak.',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            restful_services='user.thingspeak.ThingSpeak',
            config={
                'StdRESTful': {
                    'ThingSpeak': {
                        'api_key': 'INSERT_TOKEN_HERE'}}},
            files=[('bin/user', ['bin/user/thingspeak.py'])]
        )

# $Id: install.py 1483 2016-04-25 06:53:19Z mwall $
# installer for ThinkSpeak
# Copyright 2014 Matthew Wall

from setup import ExtensionInstaller

def loader():
    return ThingSpeakInstaller()

class ThingSpeakInstaller(ExtensionInstaller):
    def __init__(self):
        super(ThingSpeakInstaller, self).__init__(
            version="0.7",
            name='thingspeak',
            description='Upload weather data to ThingSpeak.',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            restful_services='user.thingspeak.ThingSpeak',
            config={
                'StdRESTful': {
                    'ThingSpeak': {
                        'token': 'INSERT_TOKEN_HERE'}}},
            files=[('bin/user', ['bin/user/thingspeak.py'])]
            )

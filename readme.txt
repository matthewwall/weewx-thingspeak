thingspeak - weewx extension that sends data to ThingSpeak
Copyright 2014-2020 Matthew Wall
Distributed under the terms of the GNU Public License (GPLv3)

Installation instructions:

1) download

wget -O weewx-thingspeak.zip https://github.com/matthewwall/weewx-thinkspeak/archive/master.zip

2) run the installer:

wee_extension --install weewx-thingspeak.zip

3) modify weewx.conf:

[StdRESTful]
    [[ThingSpeak]]
        api_key = TOKEN

4) restart weewx

sudo /etc/init.d/weewx stop
sudo /etc/init.d/weewx start

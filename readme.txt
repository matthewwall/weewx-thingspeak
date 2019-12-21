thingspeak - weewx extension that sends data to ThingSpeak
Copyright 2014 Matthew Wall

Installation instructions:

1) run the installer:

wee_extension --install weewx-thingspeak.tgz

2) modify weewx.conf:

[StdRESTful]
    [[ThingSpeak]]
        token = TOKEN

3) restart weewx

sudo /etc/init.d/weewx stop
sudo /etc/init.d/weewx start

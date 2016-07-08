#!/usr/bin/env python
# -*- coding: utf-8 -*-

##  Version 05
##      Date    19/05/2016
##      Change  Introduce thresholds for alarms
##  Version 06
##      Date    19/05/2016
##      Change  Introduce tcp socket alarms
##  Version 07
##      Date    24/05/2016
##      Change  Introduce config file
##  Version 08
##      Date    03/06/2016
##      Change  Clean up MC alarm structure
##  Version 09
##      Date    06/06/2016
##      Change  Introduce thresholds for negative alarms
##  Version 11
##      Date    07/06/2016
##      Add sound to pin 12


import _mysql

import sys
import time
import datetime
import serial
import logging
import socket
import re
import ConfigParser
from RF24 import *
import RPi.GPIO as GPIO

DEBUG = 1

if DEBUG == 1: print 'DEBUG IS ON'

config = ConfigParser.ConfigParser();
config.read('/home/pi/tms/tms.conf')

DISPLAY_CLEAR = "v"	#0x76
DISPLAY_COMMAND ="w"	#0x77
DISPLAY_BRIGHTNESS_COMMAND ="z"	#0x7A
DISPLAY_BRIGHTNESS_VALUE = 50
DISPLAY_CENTRE_DP = str(0b00000010)
DISPLAY_LEFT_DP = str(0b00000001)

SYSTEM_NAME = config.get('system','SYSTEM_NAME')
POD_ID = int(config.get('system','POD_ID'))
PROBE_ID = int(config.get('system','PROBE_ID'))

SENSOR_TIMEOUT = int(config.get('system','SENSOR_TIMEOUT'))
SENSOR_TIMEOUT_ALARM_FREQUENCY = int(config.get('system','SENSOR_TIMEOUT_ALARM_FREQUENCY'))

ALARM_LOW_TRIGGER_CRITICAL = float(config.get('system','ALARM_LOW_TRIGGER_CRITICAL'))
ALARM_LOW_TRIGGER_WARNING = float(config.get('system','ALARM_LOW_TRIGGER_WARNING'))
ALARM_HIGH_TRIGGER_CRITICAL = float(config.get('system','ALARM_HIGH_TRIGGER_CRITICAL'))
ALARM_HIGH_TRIGGER_WARNING = float(config.get('system','ALARM_HIGH_TRIGGER_WARNING'))
SERVER_IP = config.get('system','SERVER_IP')
SERVER_PORT = int(config.get('system','SERVER_PORT'))
LOCAL_MYSQL_USERNAME = config.get('system','LOCAL_MYSQL_USERNAME')
LOCAL_MYSQL_PASSWORD = config.get('system','LOCAL_MYSQL_PASSWORD')
LOCAL_MYSQL_DATABASE = config.get('system','LOCAL_MYSQL_USERNAME')

ALARM_STATUS_LOW_CRITICAL=-2
ALARM_STATUS_LOW_WARNING=-1
ALARM_STATUS_NORMAL=0
ALARM_STATUS_HIGH_WARNING=1
ALARM_STATUS_HIGH_CRITICAL=2

ALARM_STATUS=ALARM_STATUS_NORMAL
ALARM_STATUS_SENSOR = 0

logging.basicConfig(filename='/home/pi/tms/tms.log',level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logging.info('*********************************************************')
logging.info('Application initiation')
logging.info('SYSTEM_NAME: ' + str(SYSTEM_NAME))
logging.info('POD_ID: ' + str(POD_ID))
logging.info('PROBE_ID: ' + str(PROBE_ID))
logging.info('SENSOR_TIMEOUT: ' + str(SENSOR_TIMEOUT))
logging.info('SENSOR_TIMEOUT_ALARM_FREQUENCY: ' + str(SENSOR_TIMEOUT_ALARM_FREQUENCY))

logging.info('ALARM_HIGH_TRIGGER_CRITICAL: ' + str(ALARM_HIGH_TRIGGER_CRITICAL))
logging.info('ALARM_HIGH_TRIGGER_WARNING: ' + str(ALARM_HIGH_TRIGGER_WARNING))
logging.info('ALARM_LOW_TRIGGER_WARNING: ' + str(ALARM_LOW_TRIGGER_WARNING))
logging.info('ALARM_LOW_TRIGGER_CRITICAL: ' + str(ALARM_LOW_TRIGGER_CRITICAL))

logging.info('ALARM_STATUS_LOW_CRITICAL: ' + str(ALARM_STATUS_LOW_CRITICAL))
logging.info('ALARM_STATUS_LOW_WARNING: ' + str(ALARM_STATUS_LOW_WARNING))
logging.info('ALARM_STATUS_NORMAL: ' + str(ALARM_STATUS_NORMAL))
logging.info('ALARM_STATUS_HIGH_WARNING: ' + str(ALARM_STATUS_HIGH_WARNING))
logging.info('ALARM_STATUS_HIGH_CRITICAL: ' + str(ALARM_STATUS_HIGH_CRITICAL))

logging.info('SERVER_IP: ' + str(SERVER_IP))
logging.info('SERVER_PORT: ' + str(SERVER_PORT))



########### RADIO CONFIGURATION ###########
# See https://github.com/TMRh20/RF24/blob/master/RPi/pyRF24/readme.md

# CE Pin, CSN Pin, SPI Speed
# Setup for GPIO 22 CE and CE0 CSN for RPi B+ with SPI Speed @ 8Mhz
#radio = RF24(RPI_BPLUS_GPIO_J8_22, RPI_BPLUS_GPIO_J8_24, BCM2835_SPI_SPEED_8MHZ)
radio = RF24(22,0)

pipes = [0xCDCDCDCDB1, 0xCDCDCDCDB3]
radio.begin();
radio.setAutoAck(1);
radio.enableAckPayload();
radio.setRetries(0,15);
radio.setPALevel(RF24_PA_MAX);
radio.openWritingPipe(pipes[0]);
radio.openReadingPipe(1,pipes[1]);
radio.startListening();
if DEBUG == 1: radio.printDetails();
radio.startListening()

########### SETUP DISPLAY ON SERIAL PORT ###############################
port = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=3.0)

DISPLAY_BRIGHTNESS_COMMAND ="z"	#0x7A
DISPLAY_BRIGHTNESS_VALUE = "z"

#port.write(str(0x5))
port.write(DISPLAY_CLEAR)
time.sleep(1)
port.write("0000")
time.sleep(1)
port.write("z")
port.write("1")

try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_IP, SERVER_PORT))
        local_ipaddress = s.getsockname()[0]
        if DEBUG == 1: print 'IP address = ' + local_ipaddress
        logging.info('LOCAL_IP_ADDRESS: ' + local_ipaddress)
        s.send("0:INFO " + SYSTEM_NAME + " STARTUP")
        s.close()

        octets = re.split('\.',local_ipaddress)

	for octet in octets:
                port.write(DISPLAY_CLEAR)
        	time.sleep(1)
		if DEBUG == 1:print 'Octet = ' + octet
        	port.write(octet)
        	time.sleep(1)

except socket.error as msg:
        print msg
        port.write(DISPLAY_CLEAR)
        port.write("ERR")
        logging.error(msg)
        time.sleep(2)
 
def sendalarm(MESSAGE):
    print MESSAGE
    logging.info(MESSAGE)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_IP, SERVER_PORT))
        s.send(MESSAGE)
        s.close()
    except socket.error as msg:
        logging.error(msg)
        print msg

def soundalarm(cycles):
    cnt=0
    while cycles > cnt:
        pwm.start(100)
        time.sleep(1)
        pwm.ChangeDutyCycle(0)
        time.sleep(1)
        cnt += 1

time_last_message_received = datetime.datetime.now()

GPIO.setmode(GPIO.BOARD)

#Setup the piezio pin
GPIO.setup(12, GPIO.OUT)
pwm=GPIO.PWM(12, 500)

#Setup the Power Detect pin
GPIO.setup(16, GPIO.IN)
global POWER_STATUS
POWER_STATUS = GPIO.input(16)
if DEBUG == 1: print 'Power Status = ' + str(POWER_STATUS)


# forever loop
while 1:
    if radio.available():
        while radio.available():
            time_last_message_received = datetime.datetime.now()

            len = radio.getDynamicPayloadSize()
            temperature = radio.read(len)
            display = temperature
            fdisplay = float(display)
            fdisplay *= 100
            idisplay = int(fdisplay)
            port.write(DISPLAY_CLEAR)
            port.write(str('%4s' % idisplay))
            port.write(DISPLAY_COMMAND)
            port.write(DISPLAY_CENTRE_DP)
            temperature = fdisplay / 100
            if DEBUG == 1: print 'Temperature = ' + display
            
            #print ALARM_STATUS
            msg = ""
            if temperature > ALARM_LOW_TRIGGER_WARNING and temperature < ALARM_HIGH_TRIGGER_WARNING and ALARM_STATUS == ALARM_STATUS_NORMAL:
                time.sleep(.1)
            elif temperature >= ALARM_HIGH_TRIGGER_CRITICAL:
                if ALARM_STATUS != ALARM_STATUS_HIGH_CRITICAL:
                    ALARM_STATUS = ALARM_STATUS_HIGH_CRITICAL;
                    msg = '3:CRITICAL OVERHEAT '
            elif temperature <= ALARM_LOW_TRIGGER_CRITICAL:
                if ALARM_STATUS != ALARM_STATUS_LOW_CRITICAL:
                    ALARM_STATUS = ALARM_STATUS_LOW_CRITICAL;
                    msg = '3:CRITICAL UNDERHEAT '
            elif temperature >= ALARM_HIGH_TRIGGER_WARNING:
                if ALARM_STATUS != ALARM_STATUS_HIGH_WARNING:
                    ALARM_STATUS = ALARM_STATUS_HIGH_WARNING;
                    msg = '2:WARNING OVERHEAT '
            elif temperature <= ALARM_LOW_TRIGGER_WARNING:
                if ALARM_STATUS != ALARM_STATUS_LOW_WARNING:
                    ALARM_STATUS = ALARM_STATUS_LOW_WARNING;
                    msg = '2:WARNING UNDERHEAT '
            else:
                ALARM_STATUS = ALARM_STATUS_NORMAL;
                msg = '1:TEMPERATURE CANCEL '

            if msg:
                msg = msg + SYSTEM_NAME + ' ' + display
                #print msg
                sendalarm(msg)
                #logging.info(msg)

            if ALARM_STATUS == 2 or ALARM_STATUS == -2:
                soundalarm(2)
            elif ALARM_STATUS == 1 or ALARM_STATUS == -1 or POWER_STATUS == 0:
                soundalarm(1)


            try:
                conmysql = _mysql.connect('localhost', LOCAL_MYSQL_USERNAME, 'tms', 'tms')
                conmysql.query('INSERT INTO log (POD_ID, PROBE_ID, temperature) VALUES ("%s","%s","%s")' %(POD_ID, PROBE_ID, temperature))
                conmysql.close()

            except _mysql.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                logging.error('local mysql %d: %s',e.args[0], e.args[1])

    sec_since_last_message_received = datetime.datetime.now() - time_last_message_received
    if DEBUG == 1: print "Last Received message " + str(sec_since_last_message_received.seconds)
    if sec_since_last_message_received.seconds > SENSOR_TIMEOUT:
    	if ALARM_STATUS_SENSOR == 0:
		ALARM_STATUS_SENSOR = 1
		sendalarm("0:INFO " + SYSTEM_NAME + " SENSOR TIMOUT")
		SENSOR_TIMEOUT_ALARM_TIMER = datetime.datetime.now()
        	soundalarm(1)
	else:
		sec_since_last_SENSOR_TIMEOUT_ALARM = datetime.datetime.now() - SENSOR_TIMEOUT_ALARM_TIMER
		if DEBUG == 1: print "Last alarm " + str(sec_since_last_SENSOR_TIMEOUT_ALARM.seconds)
		if sec_since_last_SENSOR_TIMEOUT_ALARM.seconds > SENSOR_TIMEOUT_ALARM_FREQUENCY:
			soundalarm(1)
			SENSOR_TIMEOUT_ALARM_TIMER = datetime.datetime.now()

    else:
    	if ALARM_STATUS_SENSOR == 1:
		ALARM_STATUS_SENSOR = 0
		sendalarm("0:INFO " + SYSTEM_NAME + " SENSOR TIMOUT CANCEL")

    if (GPIO.input(16)):
        if (POWER_STATUS == 1):
            if DEBUG == 1:print 'Power ON'
        else:
            if DEBUG == 1:print 'Power Restored!!!'
            POWER_STATUS = 1
            sendalarm('4:CANCEL ' + SYSTEM_NAME + ' POWER ON')
    else:
        if (POWER_STATUS == 1):
            if DEBUG == 1:print 'Power LOST!!!'
            POWER_STATUS = 0
            sendalarm('4:ALARM ' + SYSTEM_NAME + ' POWER OFF')
            soundalarm(1)
        else:
            soundalarm(1)
            if DEBUG == 1:print 'Power OFF'


    time.sleep(1)
 


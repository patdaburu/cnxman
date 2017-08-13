#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. currentmodule:: cnxman.serial
.. moduleauthor:: Pat Daburu <pat@daburu.net>

Let's manage serial port connections!
"""

from cnxman.basics import Connection
import serial
from serial import Serial, SerialException
import threading

class SerialListener(threading.Thread):
    def __init__(self, serial: serial.Serial):
        self._serial = serial
        self._stop_event = threading.Event()

    @property
    def serial(self):
        return self._serial

    def listen(self):
        self.run(self)

    def stop(self):
        self._serial.close()
        self._stop_event.set()

    def run(self):
        if not self._serial.is_open:
            try:
                self._serial.open()
            except:
                print("couldn't open the serial port.")
        while not self._stop_event.is_set():
            try:
                data = self._serial.read()
                print("got some data: ", data)
            except:
                print("an error occurred while we were reading!")
                self.stop()



class SerialConnection(Connection):

    def __init__(self,
                 port: str,
                 baudrate: int=9600,
                 bytesize: int = serial.EIGHTBITS,
                 parity: str=serial.PARITY_NONE,
                 stopbits: int=serial.STOPBITS_ONE,
                 timeout=None):
        # Make copies of the port parameters.
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout

        self._listener = None
        # Create the internal serial port.
        # self._serial = serial.Serial(port=port,
        #                              baudrate=baudrate,
        #                              bytesize=bytesize,
        #                              parity=parity,
        #                              stopbits=stopbits,
        #                              timeout=timeout)

    def try_connect(self) -> bool:
        # If we're already listening and everything is all right...
        if self._listener is not None and self._listener.serial.is_open:
            # ...there's nothing more to do here.
            return True
        try:
            _serial = serial.Serial(port=self._port,
                                    baudrate=self._baudrate,
                                    bytesize=self._bytesize,
                                    parity=self._parity,
                                    stopbits=self._stopbits,
                                    timeout=self._timeout)
            if not _serial.is_open:
                _serial.open()
            self._listener = SerialListener(serial=_serial)
            self._listener.run()

            return True
        except SerialException as sex:
            print("boom boom", sex) # TODO: Proper logging!
            return False

    def disconnect(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def teardown(self):
        self.disconnect()





#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. currentmodule:: cnxman.serial
.. moduleauthor:: Pat Daburu <pat@daburu.net>

Let's manage serial port connections!
"""

from cnxman.basics import Connection
from enum import Enum
from pydispatch import dispatcher
import serial as pyserial
from serial import Serial, SerialException
import threading

class SerialListener(threading.Thread):

    class Signals(Enum):
        """
        These are the used by serial listener objects.

        :seealso:  :py:func:`pydispatch.dispatcher`
        """
        DATA_RECEIVED = 'data-received'  # We received some data! Hooray!
        READ_ERROR = 'read-error'  # We couldn't read from the connection.

    def __init__(self, serial: pyserial.Serial):
        super().__init__()
        # Threads of this type run as daemons.
        self.daemon = True
        self._serial = serial  # the serial connection we're monitoring
        self._terminate_event = threading.Event()  # a threading event to tell us when its time to stop

    @property
    def serial(self):
        return self._serial

    def terminate(self):
        self._serial.close()
        self._terminate_event.set()

    def run(self):
        if not self._serial.is_open:
            try:
                self._serial.open()
            except:
                print("couldn't open the serial port.")
        while not self._terminate_event.is_set():
            try:
                data = self._serial.read()
                # Notify interested parties that we got something!
                dispatcher.send(signal=SerialListener.Signals.DATA_RECEIVED, sender=self, data=data)
                #print("got some data: ", data)
            except:
                print("an error occurred while we were reading!")
                self.terminate()
                # Let any interested parties know.
                dispatcher.send(signal=SerialListener.Signals.READ_ERROR, sender=self)
                # Bail out.
                return


class SerialConnection(Connection):

    class Signals(Enum):
        """
        These are the used by serial listener objects.

        :seealso:  :py:func:`pydispatch.dispatcher`
        """
        DATA_RECEIVED = 'data-received'  # We received some data! Hooray!

    def __init__(self,
                 port: str,
                 baudrate: int=9600,
                 bytesize: int = pyserial.EIGHTBITS,
                 parity: str=pyserial.PARITY_NONE,
                 stopbits: int=pyserial.STOPBITS_ONE,
                 timeout=None):
        super().__init__()
        # Make copies of the port parameters so that we may construct serial ports.
        self._port = port  # To what port are we connecting?
        self._baudrate = baudrate  # What's the rate on the port?
        self._bytesize = bytesize  # How much is a byte?
        self._parity = parity  # What's the parity on the port?
        self._stopbits = stopbits  # How many stop bits?
        self._timeout = timeout  # What's the timeout interval.
        self._listener: SerialListener = None  # the background thread serial monitor


    def try_connect(self) -> bool:
        # If we're already listening and everything is all right...
        if self._listener is not None and self._listener.serial.is_open:
            # ...there's nothing more to do here.
            return True
        try:
            serial = Serial(port=self._port,
                            baudrate=self._baudrate,
                            bytesize=self._bytesize,
                            parity=self._parity,
                            stopbits=self._stopbits,
                            timeout=self._timeout)
            # If the serial connection didn't open automatically...
            if not serial.is_open:
                # ...open it now.
                serial.open()
            # So far so good.  Set up a background thread.
            self._listener = SerialListener(serial=serial)
            # We want to be notified if the connection sends data.
            dispatcher.connect(self._handle_listener_data_received,
                               signal=SerialListener.Signals.DATA_RECEIVED,
                               sender=self._listener)
            # We want to be notified if there is a read error, also.
            dispatcher.connect(self._handle_listener_read_error,
                               signal=SerialListener.Signals.READ_ERROR,
                               sender=self._listener)
            self._listener.run()
            # If we got this far, the connection succeeded.
            return True
        except SerialException as sex:
            print("boom boom", sex)  # TODO: Proper logging!
            return False

    def disconnect(self):
        if self._listener is not None:
            # Disconnect from any further signals sent by the listener.
            dispatcher.disconnect(dispatcher.Any, self._listener)
            # Stop the listener.
            self._listener.stop()
            self._listener = None

    def teardown(self):
        self.disconnect()

    def _handle_listener_data_received(self, data):
        print("The SerialConnection heard: ", data)

    def _handle_listener_read_error(self):
        # Raise the alarm!
        self.raise_alarm()





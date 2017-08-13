#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. currentmodule:: cnxman.basics
.. moduleauthor:: Pat Daburu <pat@daburu.net>

This module contains the base classes and basic utilities.
"""

from abc import ABCMeta, abstractmethod
from automat import MethodicalMachine
from enum import Enum
import time
from pydispatch import dispatcher


class ConnectionException(Exception):
    """
    Raised when an error occurs within a connection.
    """
    def __init__(self, message: str, inner: Exception):
        """

        :param message: the original message
        :type message:  ``str``
        :param inner: the exception responsible for the raising of this exception.
        :type inner:  :py:class:`Exception`
        """
        super().__init__(message)
        self._inner = inner

    @property
    def inner(self) -> Exception or None:
        """
        This is the original exception responsible for raising this connection exception.
        """
        return self._inner

    @staticmethod
    def from_exception(ex: Exception):
        """
        This is a convenience method that can be used to create a connection exception from another exception, using
        default logic to populate the constructor arguments.

        :param ex: the original exception
        :type ex:  :py:class:`Exception`
        :return: a new connection exception
        :rtype:  :py:class:`ConnectionException`
        """
        return ConnectionException(
            message='A(n) {extyp} was raised: {msg}'.format(extyp=type(ex), msg=repr(ex)),
            inner=ex)  # TODO: Improve this!


class Connection(object):
    """
    Extend this class to define a logical connection to something.  The expectations we have of a connection are these:

    * It can attempt create a connection and report on whether or not the connection was successful.
    * It can (at least by all appearances) gracefully disconnect.
    * It can release all its resources upon request.

    :seealso:  :py:func:`Connection.try_connect`
    :seealso:  :py:func:`Connection.disconnect`
    :seealso:  :py:func:`Connection.teardown`
    """
    __metaclass__ = ABCMeta

    class Signals(Enum):
        """
        These are the used by connection objects.

        :seealso:  :py:func:`pydispatch.dispatcher`
        """
        RAISE_ALARM = 'raise-alarm'  # Something has gone awry with the connection.

    @abstractmethod
    def try_connect(self) -> bool:
        """
        Override this method to define the logic by which a connection is make.

        :return:  ``True`` if and only if the connection attempt is successful, otherwise ``False``.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Override this method to take the steps required to gracefully disconnect.
        """
        pass

    @abstractmethod
    def teardown(self):
        """
        Override this method to release resources when requested.
        """
        pass

    def raise_alarm(self):
        """
        Raise the alarm to notify anyone who might be interested (like a :py:class:`ConnectionManager`) that there is
        trouble with the connection.
        """
        dispatcher.send(signal=Connection.Signals.RAISE_ALARM, sender = self)


class ConnectionManager(object):
    """
    Extend this class to create your own object with the know-how to establish and maintain a connection to something.
    """
    __metaclass__ = ABCMeta
    _machine = MethodicalMachine()  # This is the class state machine.

    def __init__(self, connection: Connection):
        self._connection = connection
        # We want to be notified if the connection raises the alarm.
        dispatcher.connect(self._handle_connection_raise_alarm,
                           signal=Connection.Signals.RAISE_ALARM,
                           sender=self._connection)

    @_machine.state(initial=True)
    def ready(self):
        """We haven't connected yet, but we're ready to try."""

    @_machine.input()
    def connect(self):
        """Let's get connected."""

    @_machine.output()
    def _connect(self):
        """
        This is the output method mapped to the :py:func:`ConnectionManager.connect` input method.
        """
        # If there is no function to call, we simply cannot connect, so...
        if self._connection is None:
            self._raise_alarm()
            return
        else:
            # Give it a try!
            connected = self._connection.try_connect()
            # How'd it go?
            if connected:
                self._silence_alarm()  # Great!
            else:
                self._raise_alarm()  # OK.  Not so great.

    @_machine.input()
    def _raise_alarm(self):
        """
        There is trouble with the connection.  Raise the alarm!
        """

    @_machine.input()
    def _silence_alarm(self):
        """
        Everything is fine with the connection.
        """

    def _handle_connection_raise_alarm(self):
        """
        This is a handler for the connection's 'raise alarm' signal.

        :seealso:  :py:class:`Connection.Signals`
        """
        self._raise_alarm()

    @_machine.state()
    def connecting(self):
        """We're trying to connect."""

    @_machine.state()
    def connected(self):
        """We're connected."""

    @_machine.state()
    def recovering(self):
        """We're waiting to try to reconnect."""

    # TODO: Improve the _recover method!
    @_machine.output()
    def _recover(self):
        """
        Attempt to recover the connection.
        """
        print("Waiting to retry.")
        time.sleep(5)
        print("Here we go.")
        self.connect()

    @_machine.state()
    def disconnected(self):
        """The connection has been disconnected."""

    @_machine.input()
    def disconnect(self):
        """
        Release the connection.
        """

    @_machine.output()
    def _disconnect(self):
        """
        This is the output method mapped to the :py:func:`ConnectionManager.disconnect` input method.
        """
        self._connection.disconnect()

    @_machine.state(terminal=True)
    def torndown(self):
        """The connection manager has been torn down.  It's over."""

    @_machine.input()
    def teardown(self):
        """
        Release any resources held by the connection.
        """

    @_machine.output()
    def _teardown(self):
        """
        This is the output method mapped to the :py:func:`ConnectionManager.teardown` input method.
        """
        self._connection.teardown()

    # From the 'ready' state, we can connect.
    ready.upon(connect, enter=connecting, outputs=[_connect])
    # From the 'connecting' state, we can either go into an "everything's OK" state by silencing any alarms...
    connecting.upon(_silence_alarm, enter=connected, outputs=[])
    # ...or we can raise the alarm.
    connecting.upon(_raise_alarm, enter=recovering, outputs=[_recover])
    # From the 'recovering' state, we can try to connect.
    recovering.upon(connect, enter=connecting, outputs=[_connect])
    # If we're recovering, we don't need to change state if the alarm sounds because we're already in a recovery
    # condition.
    recovering.upon(_raise_alarm, enter=recovering, outputs=[])
    # When we're connected, we can, of course, go to the 'disconnected' state.
    connected.upon(disconnect, enter=disconnected, outputs=[_disconnect])
    # When we're connected, we can go right to the 'torndown' state if requested.
    connected.upon(teardown, enter=torndown, outputs=[_disconnect, _teardown])
    # When we're in the 'connected' state, raising an alarm puts us into the 'recovering' state.
    connected.upon(_raise_alarm, enter=recovering, outputs=[_recover])
    # When we're in the 'connected' state, silencing an alarm puts us into the 'connected' state.
    connected.upon(_silence_alarm, enter=connected, outputs=[])
    # From the 'disconnected' state, we can to the 'torndown' state.
    disconnected.upon(teardown, enter=torndown, outputs=[_teardown])


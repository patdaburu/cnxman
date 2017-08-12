#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. currentmodule:: cnxman.basics
.. moduleauthor:: Pat Daburu <pat@daburu.net>

This module contains the base classes.
"""

from abc import ABCMeta, abstractmethod
from automat import MethodicalMachine
from enum import Enum
from functools import wraps
import inspect
import time
from typing import Callable, List


class ConnectException(Exception):
    """
    Raised when a parsing attempt fails.

    :param message: the exception message
    :type message:  ``str``
    """

    def __init__(self, message: str, inner: Exception):
        super().__init__(message)
        self._inner = inner

    @property
    def inner(self) -> Exception or None:
        return self._inner


class _ManagedConnectionDelegateTypes(Enum):
    CONNECTOR = 'connector',
    DESTRUCTOR = 'destructor'

class _ManagedConnectionDelegate(object):
    def __init__(self, delegate_type: _ManagedConnectionDelegateTypes, delegate_function):
        self._delegate_type = delegate_type
        self._delegate_function = delegate_function

    @property
    def delegate_type(self):
        return self._delegate_type

    @property
    def delegate_function(self):
        return self._delegate_function

def destructor(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return f(*args, **kwargs)
    return _ManagedConnectionDelegate(delegate_type=_ManagedConnectionDelegateTypes.DESTRUCTOR,
                                      delegate_function=wrapped)

def connector(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as ex:
            raise ConnectException(
                message='A(n) {extyp} was raised: {msg}'.format(extyp=type(ex), msg=repr(ex)),
                inner=ex)  # TODO: Improve this!
    return _ManagedConnectionDelegate(delegate_type=_ManagedConnectionDelegateTypes.CONNECTOR,
                                      delegate_function=wrapped)


class ConnectionManager(object):
    __metaclass__ = ABCMeta
    _machine = MethodicalMachine()  # This is the class state machine.

    def __init__(self):
        # Let's establish a couple of properties that we're going to populate below via inspection.
        self.__connector: Callable[[], bool] = None  # the method we'll call when we need to connect.
        self.__destructors: List[Callable] = None  # all of the destructor methods we'll call when we tear down.

        # Get all the managed connection delegates defined for this class.
        delegates = [t[1] for t in inspect.getmembers(self) if isinstance(t[1], _ManagedConnectionDelegate)]
        # From the list of delegates, get just those we want to call when we're attempting a connection.
        connector_delegates = [delegate for delegate in delegates
                               if delegate.delegate_type == _ManagedConnectionDelegateTypes.CONNECTOR]
        # If we have exactly one (1) connector delegate, that's the one we'll use!
        if len(connector_delegates) == 1:
            self.__connector = connector_delegates[0].delegate_function
        # We can grab all of the destructor delegates.
        self.__destructors = [delegate.delegate_function for delegate in delegates
                              if delegate.delegate_type == _ManagedConnectionDelegateTypes.DESTRUCTOR]

    @_machine.state(initial=True)
    def ready(self):
        """We're presently not connected."""

    @_machine.input()
    def connect(self):
        """Let's get connected."""

    @_machine.output()
    def _connect(self):
        """
        This is the output method mapped to the :py:func:`ConnectionManager.connect` input method.
        """
        # If there is no function to call, we simply cannot connect, so...
        if self.__connector is None:
            self._upon_connect_fail()
            return
        else:
            # Give it a try!
            connected = self.__connector(self)
            # How'd it go?
            if connected:
                self._notify_connected()  # Great!
            else:
                self._notify_connect_failed()  # OK.  Not so great.

    @_machine.input()
    def _notify_connected(self):
        """"""

    @_machine.input()
    def _notify_connect_failed(self):
        """"""

    @_machine.input()
    def alarm(self):
        """
        Call this method when the connection experiences an unexpected interruption.
        """

    @_machine.state()
    def connecting(self):
        """We're trying to connect."""


    @_machine.state()
    def connected(self):
        """We're connected."""

    @_machine.state()
    def recovering(self):
        """We're waiting to try to reconnect."""

    @_machine.output()
    def _recover(self):
        print("Waiting to retry.")
        time.sleep(5)
        print("Here we go.")
        self.connect()

    @_machine.state()
    def disconnected(self):
        """The connection has been disconnected."""


    @_machine.input()
    def disconnect(self):
        """"""

    @_machine.output()
    def _disconnect(self):
        """"""

    @_machine.state(terminal=True)
    def torndown(self):
        """The connection manager has been torn down.  It's over."""

    @_machine.input()
    def teardown(self):
        """"""

    @_machine.output()
    def _teardown(self):
        """"""
        for destructor in self.__destructors:
            destructor(self)

    ready.upon(connect, enter=connecting, outputs=[_connect])
    connecting.upon(_notify_connected, enter=connected, outputs=[])
    connecting.upon(_notify_connect_failed, enter=recovering, outputs=[_recover])
    recovering.upon(connect, enter=connecting, outputs=[_connect])
    connected.upon(disconnect, enter=disconnected, outputs=[_disconnect])
    connected.upon(teardown, enter=torndown, outputs=[_disconnect, _teardown])
    disconnected.upon(teardown, enter=torndown, outputs=[_teardown])


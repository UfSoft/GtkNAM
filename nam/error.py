'''
Created on 22 Aug 2010

@author: vampas
'''

class NAMError(Exception):
    pass

class NoCoreError(NAMError):
    pass

class DaemonRunningError(NAMError):
    pass

class InvalidPathError(NAMError):
    pass



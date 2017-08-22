#!/usr/bin/env python
#
# Helper module for handling binary file I/O
# - written by Eliot Quon (eliot.quon@nrel.gov)
#
# Sample Usage
# ------------
# from binario import binaryfile
# with binaryfile(fname) as f:
#     i = f.read_int4()
#     f = f.read_float()
#     someArray = f.read_float(10)
#
import struct
import numpy as np

class binaryfile:
    def __init__(self,path):
        self.path = path
        self.f = open(path,'rb')

    def __enter__(self):
        # Called when used with the 'with' statement
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ Cleandown code, called when used with the 'with' statement
            ref: http://stackoverflow.com/questions/22417323/how-do-enter-and-exit-work-in-python-decorator-classes
        """
        # clean up
        self.f.close()
        # handle exceptions
        if exc_type is not None:
            print exc_type, exc_value, traceback
           #return False # uncomment to pass exception through
        return self

    def read(self,N=1): return self.f.read(N)

    # integers
    def read_int1(self,N=1):
        if N==1: return struct.unpack('b',self.f.read(1))[0] #short
        else: return struct.unpack('{:d}b',self.f.read(N*1))[0:N] #short
    def read_int2(self,N=1):
        if N==1: return struct.unpack('h',self.f.read(2))[0] #short
        else: return struct.unpack('{:d}h'.format(N),self.f.read(N*2))[0:N] #short
    def read_int4(self,N=1):
        if N==1: return struct.unpack('i',self.f.read(4))[0] #int
        else: return struct.unpack('{:d}i'.format(N),self.f.read(N*4))[0:N] #int
    def read_int8(self,N=1):
        if N==1: return struct.unpack('l',self.f.read(8))[0] #long
        else: return struct.unpack('{:d}l'.format(N),self.f.read(N*8))[0:N] #long

    # floats
    def read_float(self,N=1,dtype=float):
        if N==1: return dtype( struct.unpack('f',self.f.read(4))[0] )
        else: return [ dtype(val) for val in struct.unpack('{:d}f'.format(N),self.f.read(N*4))[0:N] ]
    def read_double(self,N=1):
        if N==1: return struct.unpack('d',self.f.read(8))[0]
        else: return struct.unpack('{:d}d'.format(N),self.f.read(N*8))[0:N]
    def read_real4(self,N=1):
        return self.read_float(N,dtype=np.float32)
    def read_real8(self,N=1):
        return self.read_float(N,dtype=np.float64)

    # aliases
    def read_int(self,N=1): return self.read_int4(N)



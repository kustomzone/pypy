MAXDIMS = 32

BOOL = 0
BYTE = 1
UBYTE = 2
SHORT = 3
USHORT = 4
INT = 5
UINT = 6
LONG = 7
ULONG = 8
LONGLONG = 9
ULONGLONG = 10
FLOAT = 11
DOUBLE = 12
LONGDOUBLE = 13
CFLOAT = 14
CDOUBLE = 15
CLONGDOUBLE = 16
OBJECT = 17
STRING = 18
UNICODE = 19
VOID = 20
DATETIME = 21
TIMEDELTA = 22
HALF = 23
NTYPES = 24
NOTYPE = 25
CHAR = 26
USERDEF = 256

BOOLLTR = '?'
BYTELTR = 'b'
UBYTELTR = 'B'
SHORTLTR = 'h'
USHORTLTR = 'H'
INTLTR = 'i'
UINTLTR = 'I'
LONGLTR = 'l'
ULONGLTR = 'L'
LONGLONGLTR = 'q'
ULONGLONGLTR = 'Q'
HALFLTR = 'e'
FLOATLTR = 'f'
DOUBLELTR = 'd'
LONGDOUBLELTR = 'g'
CFLOATLTR = 'F'
CDOUBLELTR = 'D'
CLONGDOUBLELTR = 'G'
OBJECTLTR = 'O'
STRINGLTR = 'S'
STRINGLTR2 = 'a'
UNICODELTR = 'U'
VOIDLTR = 'V'
DATETIMELTR = 'M'
TIMEDELTALTR = 'm'
CHARLTR = 'c'

INTPLTR = 'p'
UINTPLTR = 'P'

GENBOOLLTR = 'b'
SIGNEDLTR = 'i'
UNSIGNEDLTR = 'u'
FLOATINGLTR = 'f'
COMPLEXLTR = 'c'

SEARCHLEFT = 0
SEARCHRIGHT = 1

ANYORDER = -1
CORDER = 0
FORTRANORDER = 1
KEEPORDER = 2

CLIP = 0
WRAP = 1
RAISE = 2

# These can be requested in constructor functions and tested for
ARRAY_C_CONTIGUOUS = 0x0001
ARRAY_F_CONTIGUOUS = 0x0002
ARRAY_ALIGNED      = 0x0100
ARRAY_WRITEABLE    = 0x0400
ARRAY_UPDATEIFCOPY = 0x1000 # base contains a ref to an array, update it too
# These can be tested for
ARRAY_OWNDATA     = 0x004
# These can be requested in constructor functions
ARRAY_FORECAST    = 0x0010 # causes a cast to occur even if not safe to do so
ARRAY_ENSURECOPY  = 0x0020 # returned array will be CONTIGUOUS, ALIGNED, WRITEABLE
ARRAY_ENSUREARRAY = 0x0040 # return only ndarray, not subtype
ARRAY_ELEMENTSTRIDES = 0x0080 # strides  are units of the dtype element size
ARRAY_NOTSWAPPED  = 0x0200 #native byte order

LITTLE = '<'
BIG = '>'
NATIVE = '='
SWAP = 's'
IGNORE = '|'

import sys
if sys.byteorder == 'big':
    NATBYTE = BIG
    OPPBYTE = LITTLE
else:
    NATBYTE = LITTLE
    OPPBYTE = BIG
del sys

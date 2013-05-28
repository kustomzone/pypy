"""The builtin bytes implementation"""

from pypy.interpreter.buffer import StringBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std import slicetype
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.stringtype import (
    joined2, sliced, stringendswith, stringstartswith, wrapstr)
from rpython.rlib import jit
from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, specialize)
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import StringBuilder


class W_AbstractStringObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractStringObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.bytes_w(self) is space.bytes_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.bytes_w(self)))


class W_StringObject(W_AbstractStringObject):
    from pypy.objspace.std.stringtype import str_typedef as typedef
    _immutable_fields_ = ['_value']

    def __init__(w_self, str):
        assert str is not None
        w_self._value = str

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self, space):
        return w_self._value

    def bytes_w(w_self, space):
        return w_self._value

    def listview_str(w_self):
        return _create_list_from_string(w_self._value)

def _create_list_from_string(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_str
    return [s for s in value]

registerimplementation(W_StringObject)

W_StringObject.EMPTY = W_StringObject('')
W_StringObject.PREBUILT = [W_StringObject(chr(i)) for i in range(256)]
del i

@specialize.arg(2)
def _is_generic(space, w_self, fun):
    v = w_self._value
    if len(v) == 0:
        return space.w_False
    if len(v) == 1:
        c = v[0]
        return space.newbool(fun(c))
    else:
        return _is_generic_loop(space, v, fun)

@specialize.arg(2)
def _is_generic_loop(space, v, fun):
    for idx in range(len(v)):
        if not fun(v[idx]):
            return space.w_False
    return space.w_True

def _upper(ch):
    if ch.islower():
        o = ord(ch) - 32
        return chr(o)
    else:
        return ch

def _lower(ch):
    if ch.isupper():
        o = ord(ch) + 32
        return chr(o)
    else:
        return ch

_isspace = lambda c: c.isspace()
_isdigit = lambda c: c.isdigit()
_isalpha = lambda c: c.isalpha()
_isalnum = lambda c: c.isalnum()

def str_isspace__String(space, w_self):
    return _is_generic(space, w_self, _isspace)

def str_isdigit__String(space, w_self):
    return _is_generic(space, w_self, _isdigit)

def str_isalpha__String(space, w_self):
    return _is_generic(space, w_self, _isalpha)

def str_isalnum__String(space, w_self):
    return _is_generic(space, w_self, _isalnum)

def str_isupper__String(space, w_self):
    """Return True if all cased characters in S are uppercase and there is
at least one cased character in S, False otherwise."""
    v = w_self._value
    if len(v) == 1:
        c = v[0]
        return space.newbool(c.isupper())
    cased = False
    for idx in range(len(v)):
        if v[idx].islower():
            return space.w_False
        elif not cased and v[idx].isupper():
            cased = True
    return space.newbool(cased)

def str_islower__String(space, w_self):
    """Return True if all cased characters in S are lowercase and there is
at least one cased character in S, False otherwise."""
    v = w_self._value
    if len(v) == 1:
        c = v[0]
        return space.newbool(c.islower())
    cased = False
    for idx in range(len(v)):
        if v[idx].isupper():
            return space.w_False
        elif not cased and v[idx].islower():
            cased = True
    return space.newbool(cased)

def str_istitle__String(space, w_self):
    """Return True if S is a titlecased string and there is at least one
character in S, i.e. uppercase characters may only follow uncased
characters and lowercase characters only cased ones. Return False
otherwise."""
    input = w_self._value
    cased = False
    previous_is_cased = False

    for pos in range(0, len(input)):
        ch = input[pos]
        if ch.isupper():
            if previous_is_cased:
                return space.w_False
            previous_is_cased = True
            cased = True
        elif ch.islower():
            if not previous_is_cased:
                return space.w_False
            cased = True
        else:
            previous_is_cased = False

    return space.newbool(cased)

def str_upper__String(space, w_self):
    self = w_self._value
    return space.wrapbytes(self.upper())

def str_lower__String(space, w_self):
    self = w_self._value
    return space.wrapbytes(self.lower())

def str_swapcase__String(space, w_self):
    self = w_self._value
    builder = StringBuilder(len(self))
    for i in range(len(self)):
        ch = self[i]
        if ch.isupper():
            o = ord(ch) + 32
            builder.append(chr(o))
        elif ch.islower():
            o = ord(ch) - 32
            builder.append(chr(o))
        else:
            builder.append(ch)

    return space.wrapbytes(builder.build())


def str_capitalize__String(space, w_self):
    input = w_self._value
    builder = StringBuilder(len(input))
    if len(input) > 0:
        ch = input[0]
        if ch.islower():
            o = ord(ch) - 32
            builder.append(chr(o))
        else:
            builder.append(ch)

        for i in range(1, len(input)):
            ch = input[i]
            if ch.isupper():
                o = ord(ch) + 32
                builder.append(chr(o))
            else:
                builder.append(ch)

    return space.wrapbytes(builder.build())

def str_title__String(space, w_self):
    input = w_self._value
    builder = StringBuilder(len(input))
    prev_letter = ' '

    for pos in range(len(input)):
        ch = input[pos]
        if not prev_letter.isalpha():
            ch = _upper(ch)
            builder.append(ch)
        else:
            ch = _lower(ch)
            builder.append(ch)

        prev_letter = ch

    return space.wrapbytes(builder.build())

def str_split__String_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    length = len(value)
    i = 0
    while True:
        # find the beginning of the next word
        while i < length:
            if not value[i].isspace():
                break   # found
            i += 1
        else:
            break  # end of string, finished

        # find the end of the word
        if maxsplit == 0:
            j = length   # take all the rest of the string
        else:
            j = i + 1
            while j < length and not value[j].isspace():
                j += 1
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        # the word is value[i:j]
        res_w.append(sliced(space, value, i, j, w_self))

        # continue to look from the character following the space after the word
        i = j + 1

    return space.newlist(res_w)

def str_split__String_ANY_ANY(space, w_self, w_by, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    value = w_self._value
    by = space.bufferstr_w(w_by)
    bylen = len(by)
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))

    start = 0
    if bylen == 1 and maxsplit < 0:
        # fast path: uses str.rfind(character) and str.count(character)
        by = by[0]    # annotator hack: string -> char
        count = value.count(by)
        res_w = [None] * (count + 1)
        end = len(value)
        while count >= 0:
            assert end >= 0
            prev = value.rfind(by, 0, end)
            start = prev + 1
            assert start >= 0
            res_w[count] = sliced(space, value, start, end, w_self)
            count -= 1
            end = prev
    else:
        res_w = []
        while maxsplit != 0:
            next = value.find(by, start)
            if next < 0:
                break
            res_w.append(sliced(space, value, start, next, w_self))
            start = next + bylen
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0
        res_w.append(sliced(space, value, start, len(value), w_self))

    return space.newlist(res_w)

def str_rsplit__String_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    i = len(value)-1
    while True:
        # starting from the end, find the end of the next word
        while i >= 0:
            if not value[i].isspace():
                break   # found
            i -= 1
        else:
            break  # end of string, finished

        # find the start of the word
        # (more precisely, 'j' will be the space character before the word)
        if maxsplit == 0:
            j = -1   # take all the rest of the string
        else:
            j = i - 1
            while j >= 0 and not value[j].isspace():
                j -= 1
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        # the word is value[j+1:i+1]
        j1 = j + 1
        assert j1 >= 0
        res_w.append(sliced(space, value, j1, i+1, w_self))

        # continue to look from the character before the space before the word
        i = j - 1

    res_w.reverse()
    return space.newlist(res_w)

def make_rsplit_with_delim(funcname, sliced):
    from rpython.tool.sourcetools import func_with_new_name

    if 'Unicode' in funcname:
        def unwrap_sep(space, w_by):
            return w_by._value
    else:
        def unwrap_sep(space, w_by):
            return space.bufferstr_w(w_by)

    def fn(space, w_self, w_by, w_maxsplit=-1):
        maxsplit = space.int_w(w_maxsplit)
        res_w = []
        value = w_self._value
        end = len(value)
        by = unwrap_sep(space, w_by)
        bylen = len(by)
        if bylen == 0:
            raise OperationError(space.w_ValueError, space.wrap("empty separator"))

        while maxsplit != 0:
            next = value.rfind(by, 0, end)
            if next < 0:
                break
            res_w.append(sliced(space, value, next+bylen, end, w_self))
            end = next
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        res_w.append(sliced(space, value, 0, end, w_self))
        res_w.reverse()
        return space.newlist(res_w)

    return func_with_new_name(fn, funcname)

str_rsplit__String_ANY_ANY = make_rsplit_with_delim(
    'str_rsplit__String_ANY_ANY', sliced)

def str_join__String_ANY(space, w_self, w_list):
    list_w = space.listview(w_list)
    size = len(list_w)

    if size == 0:
        return W_StringObject.EMPTY

    if size == 1:
        w_s = list_w[0]
        # only one item,  return it if it's not a subclass of str
        if space.is_w(space.type(w_s), space.w_str):
            return w_s

    return _str_join_many_items(space, w_self, list_w, size)

@jit.look_inside_iff(lambda space, w_self, list_w, size:
                     jit.loop_unrolling_heuristic(list_w, size))
def _str_join_many_items(space, w_self, list_w, size):
    self = w_self._value
    reslen = len(self) * (size - 1)
    for i in range(size):
        w_s = list_w[i]
        try:
            item = space.bufferstr_w(w_s)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            msg = "sequence item %d: expected bytes, %T found"
            raise operationerrfmt(space.w_TypeError, msg, i, w_s)
        reslen += len(item)

    sb = StringBuilder(reslen)
    for i in range(size):
        if self and i != 0:
            sb.append(self)
        sb.append(space.bufferstr_w(list_w[i]))
    return space.wrapbytes(sb.build())

def str_rjust__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_arg = space.int_w(w_arg)
    u_self = w_self._value
    fillchar = space.bytes_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("rjust() argument 2 must be a single character"))

    d = u_arg - len(u_self)
    if d > 0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_self = d * fillchar + u_self

    return space.wrapbytes(u_self)


def str_ljust__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_self = w_self._value
    u_arg = space.int_w(w_arg)
    fillchar = space.bytes_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("ljust() argument 2 must be a single character"))

    d = u_arg - len(u_self)
    if d > 0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_self += d * fillchar

    return space.wrapbytes(u_self)

@specialize.arg(4)
def _convert_idx_params(space, w_self, w_start, w_end, upper_bound=False):
    self = w_self._value
    lenself = len(self)

    start, end = slicetype.unwrap_start_stop(
            space, lenself, w_start, w_end, upper_bound=upper_bound)
    return (self, start, end)

def contains__String_ANY(space, w_self, w_sub):
    self = w_self._value
    sub = space.bufferstr_w(w_sub)
    return space.newbool(self.find(sub) >= 0)

def contains__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    return space.newbool(self.find(sub) >= 0)

def contains__String_Long(space, w_self, w_char):
    self = w_self._value
    try:
        char = space.int_w(w_char)
    except OperationError, e:
        if e.match(space, space.w_OverflowError):
            char = 256 # arbitrary value which will trigger the ValueError
                       # condition below
        else:
            raise
    if 0 <= char < 256:
        return space.newbool(self.find(chr(char)) >= 0)
    else:
        raise OperationError(space.w_ValueError,
                             space.wrap("character must be in range(256)"))

def str_find__String_ANY_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.find(space.bufferstr_w(w_sub), start, end)
    return space.wrap(res)

def str_find__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.find(w_sub._value, start, end)
    return space.wrap(res)

def str_rfind__String_ANY_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.rfind(space.bufferstr_w(w_sub), start, end)
    return space.wrap(res)

def str_rfind__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.rfind(w_sub._value, start, end)
    return space.wrap(res)

def str_partition__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    if not sub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = self.find(sub)
    if pos == -1:
        return space.newtuple([w_self, space.wrapbytes(''), space.wrapbytes('')])
    else:
        return space.newtuple([sliced(space, self, 0, pos, w_self),
                               w_sub,
                               sliced(space, self, pos+len(sub), len(self),
                                      w_self)])

def str_rpartition__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    if not sub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = self.rfind(sub)
    if pos == -1:
        return space.newtuple([space.wrapbytes(''), space.wrapbytes(''), w_self])
    else:
        return space.newtuple([sliced(space, self, 0, pos, w_self),
                               w_sub,
                               sliced(space, self, pos+len(sub), len(self), w_self)])


def str_index__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.find(w_sub._value, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return space.wrap(res)


def str_rindex__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.rfind(w_sub._value, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return space.wrap(res)

def _string_replace(space, input, sub, by, maxsplit):
    if maxsplit == 0:
        return space.wrapbytes(input)

    if not sub:
        upper = len(input)
        if maxsplit > 0 and maxsplit < upper + 2:
            upper = maxsplit - 1
            assert upper >= 0

        try:
            result_size = ovfcheck(upper * len(by))
            result_size = ovfcheck(result_size + upper)
            result_size = ovfcheck(result_size + len(by))
            remaining_size = len(input) - upper
            result_size = ovfcheck(result_size + remaining_size)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("replace string is too long")
            )
        builder = StringBuilder(result_size)
        for i in range(upper):
            builder.append(by)
            builder.append(input[i])
        builder.append(by)
        builder.append_slice(input, upper, len(input))
    else:
        # First compute the exact result size
        count = input.count(sub)
        if count > maxsplit and maxsplit > 0:
            count = maxsplit
        diff_len = len(by) - len(sub)
        try:
            result_size = ovfcheck(diff_len * count)
            result_size = ovfcheck(result_size + len(input))
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("replace string is too long")
            )

        builder = StringBuilder(result_size)
        start = 0
        sublen = len(sub)

        while maxsplit != 0:
            next = input.find(sub, start)
            if next < 0:
                break
            builder.append_slice(input, start, next)
            builder.append(by)
            start = next + sublen
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        builder.append_slice(input, start, len(input))

    return space.wrapbytes(builder.build())


def str_replace__String_ANY_ANY_ANY(space, w_self, w_sub, w_by, w_maxsplit):
    return _string_replace(space, w_self._value, space.buffer_w(w_sub).as_str(),
                           space.buffer_w(w_by).as_str(),
                           space.int_w(w_maxsplit))

def str_replace__String_String_String_ANY(space, w_self, w_sub, w_by, w_maxsplit=-1):
    input = w_self._value
    sub = w_sub._value
    by = w_by._value
    maxsplit = space.int_w(w_maxsplit)
    return _string_replace(space, input, sub, by, maxsplit)

def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    u_chars = space.bufferstr_w(w_chars)

    lpos = 0
    rpos = len(u_self)

    if left:
        #print "while %d < %d and -%s- in -%s-:"%(lpos, rpos, u_self[lpos],w_chars)
        while lpos < rpos and u_self[lpos] in u_chars:
            lpos += 1

    if right:
        while rpos > lpos and u_self[rpos - 1] in u_chars:
            rpos -= 1

    assert rpos >= lpos    # annotator hint, don't remove
    return sliced(space, u_self, lpos, rpos, w_self)

def _strip_none(space, w_self, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value

    lpos = 0
    rpos = len(u_self)

    if left:
        #print "while %d < %d and -%s- in -%s-:"%(lpos, rpos, u_self[lpos],w_chars)
        while lpos < rpos and u_self[lpos].isspace():
           lpos += 1

    if right:
        while rpos > lpos and u_self[rpos - 1].isspace():
           rpos -= 1

    assert rpos >= lpos    # annotator hint, don't remove
    return sliced(space, u_self, lpos, rpos, w_self)

def str_strip__String_ANY(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=1, right=1)

def str_strip__String_None(space, w_self, w_chars):
    return _strip_none(space, w_self, left=1, right=1)

def str_rstrip__String_ANY(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=0, right=1)

def str_rstrip__String_None(space, w_self, w_chars):
    return _strip_none(space, w_self, left=0, right=1)


def str_lstrip__String_ANY(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=1, right=0)

def str_lstrip__String_None(space, w_self, w_chars):
    return _strip_none(space, w_self, left=1, right=0)



def str_center__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_self = w_self._value
    u_arg  = space.int_w(w_arg)
    fillchar = space.bytes_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("center() argument 2 must be a single character"))

    d = u_arg - len(u_self)
    if d>0:
        offset = d//2 + (d & u_arg & 1)
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_centered = offset * fillchar + u_self + (d - offset) * fillchar
    else:
        u_centered = u_self

    return wrapstr(space, u_centered)

def str_count__String_String_ANY_ANY(space, w_self, w_arg, w_start, w_end):
    u_self, u_start, u_end = _convert_idx_params(space, w_self, w_start, w_end)
    return wrapint(space, u_self.count(w_arg._value, u_start, u_end))

def _suffix_to_str(space, w_suffix, funcname):
    try:
        return space.bufferstr_w(w_suffix)
    except OperationError as e:
        if e.match(space, space.w_TypeError):
            msg = ("%s first arg must be bytes or a tuple of bytes, "
                   "not %T")
            raise operationerrfmt(space.w_TypeError, msg, funcname, w_suffix)

def str_endswith__String_ANY_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    (u_self, start, end) = _convert_idx_params(space, w_self, w_start,
                                               w_end, True)
    return space.newbool(stringendswith(
            u_self, _suffix_to_str(space, w_suffix, 'endswith'), start, end))

def str_endswith__String_String_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    (u_self, start, end) = _convert_idx_params(space, w_self, w_start,
                                               w_end, True)
    return space.newbool(stringendswith(u_self, w_suffix._value, start, end))

def str_endswith__String_ANY_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    u_self, start, end = _convert_idx_params(space, w_self, w_start, w_end,
                                             True)
    if not space.isinstance_w(w_suffix, space.w_tuple):
        suffix = _suffix_to_str(space, w_suffix, 'endswith')
        return space.newbool(stringendswith(u_self, suffix, start, end))

    for w_item in space.fixedview(w_suffix):
        suffix = space.bufferstr_w(w_item)
        if stringendswith(u_self, suffix, start, end):
            return space.w_True
    return space.w_False

def str_startswith__String_String_ANY_ANY(space, w_self, w_prefix, w_start, w_end):
    (u_self, start, end) = _convert_idx_params(space, w_self, w_start,
                                               w_end, True)
    return space.newbool(stringstartswith(u_self, w_prefix._value, start, end))

def str_startswith__String_ANY_ANY_ANY(space, w_self, w_prefix, w_start, w_end):
    u_self, start, end = _convert_idx_params(space, w_self, w_start, w_end,
                                             True)
    if not space.isinstance_w(w_prefix, space.w_tuple):
        prefix = _suffix_to_str(space, w_prefix, 'startswith')
        return space.newbool(stringstartswith(u_self, prefix, start, end))

    for w_item in space.fixedview(w_prefix):
        prefix = space.bufferstr_w(w_item)
        if stringstartswith(u_self, prefix, start, end):
            return space.w_True
    return space.w_False

def _tabindent(u_token, u_tabsize):
    "calculates distance behind the token to the next tabstop"

    if u_tabsize <= 0:
        return u_tabsize

    distance = u_tabsize
    if u_token:
        distance = 0
        offset = len(u_token)

        while 1:
            #no sophisticated linebreak support now, '\r' just for passing adapted CPython test
            if u_token[offset-1] == "\n" or u_token[offset-1] == "\r":
                break
            distance += 1
            offset -= 1
            if offset == 0:
                break

        #the same like distance = len(u_token) - (offset + 1)
        #print '<offset:%d distance:%d tabsize:%d token:%s>' % (offset, distance, u_tabsize, u_token)
        distance = (u_tabsize-distance) % u_tabsize
        if distance == 0:
            distance = u_tabsize

    return distance


def str_expandtabs__String_ANY(space, w_self, w_tabsize):
    u_self = w_self._value
    u_tabsize = space.int_w(w_tabsize)

    u_expanded = ""
    if u_self:
        split = u_self.split("\t")
        try:
            ovfcheck(len(split) * u_tabsize)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("new string is too long")
            )
        u_expanded = oldtoken = split.pop(0)

        for token in split:
            #print  "%d#%d -%s-" % (_tabindent(oldtoken,u_tabsize), u_tabsize, token)
            u_expanded += " " * _tabindent(oldtoken, u_tabsize) + token
            oldtoken = token

    return wrapstr(space, u_expanded)


def str_splitlines__String_ANY(space, w_self, w_keepends):
    u_keepends = space.int_w(w_keepends)  # truth value, but type checked
    data = w_self._value
    selflen = len(data)
    strs_w = []
    i = j = 0
    while i < selflen:
        # Find a line and append it
        while i < selflen and data[i] != '\n' and data[i] != '\r':
            i += 1
        # Skip the line break reading CRLF as one line break
        eol = i
        i += 1
        if i < selflen and data[i-1] == '\r' and data[i] == '\n':
            i += 1
        if u_keepends:
            eol = i
        strs_w.append(sliced(space, data, j, eol, w_self))
        j = i

    if j < selflen:
        strs_w.append(sliced(space, data, j, len(data), w_self))
    return space.newlist(strs_w)

def str_zfill__String_ANY(space, w_self, w_width):
    input = w_self._value
    width = space.int_w(w_width)

    num_zeros = width - len(input)
    if num_zeros <= 0:
        # cannot return w_self, in case it is a subclass of str
        return space.wrapbytes(input)

    builder = StringBuilder(width)
    if len(input) > 0 and (input[0] == '+' or input[0] == '-'):
        builder.append(input[0])
        start = 1
    else:
        start = 0

    builder.append_multiple_char('0', num_zeros)
    builder.append_slice(input, start, len(input))
    return space.wrapbytes(builder.build())


def hash__String(space, w_str):
    s = w_str._value
    x = compute_hash(s)
    return wrapint(space, x)

def lt__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 < s2:
        return space.w_True
    else:
        return space.w_False

def le__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 <= s2:
        return space.w_True
    else:
        return space.w_False

def eq__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 == s2:
        return space.w_True
    else:
        return space.w_False

def ne__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 != s2:
        return space.w_True
    else:
        return space.w_False

def gt__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 > s2:
        return space.w_True
    else:
        return space.w_False

def ge__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 >= s2:
        return space.w_True
    else:
        return space.w_False

def getitem__String_ANY(space, w_str, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    str = w_str._value
    slen = len(str)
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        raise OperationError(space.w_IndexError,
                             space.wrap("string index out of range"))
    return space.wrap(ord(str[ival]))

def getitem__String_Slice(space, w_str, w_slice):
    s = w_str._value
    length = len(s)
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        return W_StringObject.EMPTY
    elif step == 1:
        assert start >= 0 and stop >= 0
        return sliced(space, s, start, stop, w_str)
    else:
        str = "".join([s[start + i*step] for i in range(sl)])
    return wrapstr(space, str)

def mul_string_times(space, w_str, w_times):
    try:
        mul = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if mul <= 0:
        return W_StringObject.EMPTY
    input = w_str._value
    if len(input) == 1:
        s = input[0] * mul
    else:
        s = input * mul
    return W_StringObject(s)

def mul__String_ANY(space, w_str, w_times):
    return mul_string_times(space, w_str, w_times)

def mul__ANY_String(space, w_times, w_str):
    return mul_string_times(space, w_str, w_times)

def add__String_String(space, w_left, w_right):
    right = w_right._value
    left = w_left._value
    return joined2(space, left, right)

def add__String_ANY(space, w_left, w_right):
    left = w_left._value
    try:
        right = space.buffer_w(w_right)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    return joined2(space, left, right.as_str())

def len__String(space, w_str):
    return space.wrap(len(w_str._value))

def str__String(space, w_str):
    if space.sys.get_flag('bytes_warning'):
        space.warn(space.wrap("str() on a bytes instance"),
                   space.w_BytesWarning)
    return repr__String(space, w_str)

def ord__String(space, w_str):
    u_str = w_str._value
    if len(u_str) != 1:
        raise operationerrfmt(
            space.w_TypeError,
            "ord() expected a character, but string "
            "of length %d found", len(u_str))
    return space.wrap(ord(u_str[0]))

def getnewargs__String(space, w_str):
    return space.newtuple([wrapstr(space, w_str._value)])

def repr__String(space, w_str):
    return space.wrap(string_escape_encode(w_str._value, True))

def string_escape_encode(s, quotes):
    buf = StringBuilder(len(s) + 3 if quotes else 0)

    quote = "'"
    if quotes:
        if quote in s and '"' not in s:
            quote = '"'
            buf.append('b"')
        else:
            buf.append("b'")

    startslice = 0

    for i in range(len(s)):
        c = s[i]
        use_bs_char = False # character quoted by backspace

        if c == '\\' or c == quote:
            bs_char = c
            use_bs_char = True
        elif c == '\t':
            bs_char = 't'
            use_bs_char = True
        elif c == '\r':
            bs_char = 'r'
            use_bs_char = True
        elif c == '\n':
            bs_char = 'n'
            use_bs_char = True
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\x')
            buf.append("0123456789abcdef"[n>>4])
            buf.append("0123456789abcdef"[n&0xF])

        if use_bs_char:
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\')
            buf.append(bs_char)

    if len(s) != startslice:
        buf.append_slice(s, startslice, len(s))

    if quotes:
        buf.append(quote)

    return buf.build()


DEFAULT_NOOP_TABLE = ''.join([chr(i) for i in range(256)])

def str_translate__String_ANY_ANY(space, w_string, w_table, w_deletechars=''):
    """charfilter - unicode handling is not implemented

    Return a copy of the string where all characters occurring
    in the optional argument deletechars are removed, and the
    remaining characters have been mapped through the given translation table,
    which must be a string of length 256"""

    if space.is_w(w_table, space.w_None):
        table = DEFAULT_NOOP_TABLE
    else:
        table = space.bufferstr_w(w_table)
        if len(table) != 256:
            raise OperationError(
                space.w_ValueError,
                space.wrap("translation table must be 256 characters long"))

    string = w_string._value
    deletechars = space.bytes_w(w_deletechars)
    if len(deletechars) == 0:
        buf = StringBuilder(len(string))
        for char in string:
            buf.append(table[ord(char)])
    else:
        buf = StringBuilder()
        deletion_table = [False] * 256
        for c in deletechars:
            deletion_table[ord(c)] = True
        for char in string:
            if not deletion_table[ord(char)]:
                buf.append(table[ord(char)])
    return W_StringObject(buf.build())

def str_decode__String_ANY_ANY(space, w_string, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodetype import _get_encoding_and_errors, \
        decode_object
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    return decode_object(space, w_string, encoding, errors)

def buffer__String(space, w_string):
    return space.wrap(StringBuffer(w_string._value))

# register all methods
from pypy.objspace.std import stringtype
register_all(vars(), stringtype)

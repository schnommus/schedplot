from enum import Enum
from bitstruct import unpack

class KernelEntryType(Enum):
    Interrupt = 0
    UnknownSyscall = 1
    UserLevelFault = 2
    DebugFault = 3
    VMFault = 4
    Syscall = 5
    UnimplementedDevice = 6

class SyscallType(Enum):
    Call = 1
    ReplyRecv = 2
    NBSendRecv = 3
    NBSendWait = 4
    Send = 5
    NBSend = 6
    Recv = 7
    NBRecv = 8
    Wait = 9
    NBWait = 10
    Yield = 11

class FaultType(Enum):
    NullFault = 0
    CapFault = 1
    UnknownSyscall = 2
    UserException = 3
    Timeout = 5
    VMFault = 6

def decode_kernel_path(entry_type, word_int):
    if entry_type == KernelEntryType.Interrupt:
        return "IRQ #{}".format(word_int)
    elif entry_type == KernelEntryType.UnknownSyscall:
        return "word = {}".format(word_int)
    elif entry_type == KernelEntryType.VMFault:
        return "fault_type = {}".format(word_int)
    elif entry_type == KernelEntryType.UserLevelFault:
        return "fault_number = {}".format(word_int)
    elif entry_type == KernelEntryType.DebugFault:
        return "fault_vaddr = {}".format(hex(word_int))
    elif entry_type == KernelEntryType.Syscall:
        word_int <<= 3
        word_bytes = word_int.to_bytes(4, byteorder='big')
        tuple_of_data = unpack("u19u1u5u4u3", word_bytes)
        (invoc_tag, is_fastpath, cap_type, syscall_no, _) = tuple_of_data
        return "{} - [fp:{},ct:{}]".format(SyscallType(syscall_no), is_fastpath, cap_type)

    return "Unknown"

from enum import Enum
from bitstruct import unpack

# WARNING: A lot of these are automatically generated when the kernel is built
# You'll need to update them with any significant kernel changes.

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
    SchedplotUnknown = 7

class CapType(Enum):
    null_cap = 0
    untyped_cap = 2
    endpoint_cap = 4
    notification_cap = 6
    reply_cap = 8
    cnode_cap = 10
    thread_cap = 12
    small_frame_cap = 1
    frame_cap = 3
    asid_pool_cap = 5
    page_table_cap = 7
    page_directory_cap = 9
    asid_control_cap = 11
    irq_control_cap = 14
    irq_handler_cap = 30
    zombie_cap = 46
    domain_cap = 62
    sched_context_cap = 78
    sched_control_cap = 94

def get_kernel_path_tag(entry_type, word_int, capreg_int):
    if entry_type == KernelEntryType.UnknownSyscall:
        if word_int == 540:
            return chr(capreg_int)
    return None

def decode_kernel_path(entry_type, word_int, capreg_int):
    if entry_type == KernelEntryType.Interrupt:
        return "IRQ #{}".format(word_int)
    elif entry_type == KernelEntryType.UnknownSyscall:
        if word_int == 540:
            return "DebugPutChar: {}".format(chr(capreg_int))
        else:
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
        return "{} - [{}, fp:{}]".format(SyscallType(syscall_no), CapType(cap_type), is_fastpath)

    return "Unknown"

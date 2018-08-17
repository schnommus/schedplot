from enum import Enum, auto
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
    VCPUFault = 7
    SchedplotUnknown = 8

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
    #anything below this doesn't seem to be used anyway
    DebugPutChar = 12,
    DebugDumpScheduler = 13,
    DebugHalt = 14,
    DebugCapIdentify = 15,
    DebugSnapshot = 16,
    DebugNameThread = 17,
    SchedplotUnknown18 = 18, #?
    BenchmarkFlushCaches = 19,
    BenchmarkResetLog = 20,
    BenchmarkFinalizeLog = 21,
    BenchmarkSetLogBuffer = 22,
    BenchmarkNullSyscall = 23,
    SchedplotUnknown = 24

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


class InvocationType(Enum):
    InvalidInvocation = 0
    UntypedRetype = auto()
    TCBReadRegisters = auto()
    TCBWriteRegisters = auto()
    TCBCopyRegisters = auto()
    TCBConfigure = auto()
    TCBSetPriority = auto()
    TCBSetMCPriority = auto()
    TCBSetSchedParams = auto()
    TCBSetTimeoutEndpoint = auto()
    TCBSetIPCBuffer = auto()
    TCBSetSpace = auto()
    TCBSuspend = auto()
    TCBResume = auto()
    TCBBindNotification = auto()
    TCBUnbindNotification = auto()
    TCBSetAffinity = auto()
    CNodeRevoke = auto()
    CNodeDelete = auto()
    CNodeCancelBadgedSends = auto()
    CNodeCopy = auto()
    CNodeMint = auto()
    CNodeMove = auto()
    CNodeMutate = auto()
    CNodeRotate = auto()
    IRQIssueIRQHandler = auto()
    IRQAckIRQ = auto()
    IRQSetIRQHandler = auto()
    IRQClearIRQHandler = auto()
    DomainSetSet = auto()
    SchedControlConfigure = auto()
    SchedContextBind = auto()
    SchedContextUnbind = auto()
    SchedContextUnbindObject = auto()
    SchedContextConsumed = auto()
    SchedContextYieldTo = auto()
    SchedContextYieldToTimeout = auto()
    nInvocationLabels = auto()

def get_kernel_path_tag(entry_type, word_int, capreg_int):
    if entry_type == KernelEntryType.UnknownSyscall:
        if word_int in [540, 556, 636]:
            return chr(capreg_int)
    return None

def decode_kernel_path(entry_type, word_int, capreg_int):
    if entry_type == KernelEntryType.Interrupt:
        return "IRQ #{}".format(word_int)
    elif entry_type == KernelEntryType.UnknownSyscall:
        if word_int in [540, 556, 636]:
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
        tuple_of_data = unpack("u17u1u7u4u3", word_bytes)
        (invoc_tag, is_fastpath, cap_type, syscall_no, _) = tuple_of_data
        return "{} - [{}, fp:{}, {}]".format(SyscallType(syscall_no), CapType(cap_type), is_fastpath, InvocationType(invoc_tag))

    return "Unknown"

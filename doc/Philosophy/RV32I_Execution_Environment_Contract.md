# RV32I Execution-Environment Contract

**Scope:** Reset, boot, memory mapping, software startup, fault policy, ordering, and platform-profile completeness

**Status:** Frozen mechanism and profile-compliance rules; numerical deployment values are profile-resolved

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Memory boundary:** [RV32I Memory Subsystem Design Contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)

**Roadmap:** [RV32I Exceptions, Traps, and Extensions Roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

**Deferred decisions:** [RV32I Execution-Environment Deferred Decisions Register](RV32I_Execution_Environment_Deferred_Decisions.md)

**Normative clarification:** [RV32I Execution-Environment Configuration/Profile Amendment](../RV32I_Execution_Environment_Profile_Amendment.md)

## 1. Purpose and Decision Classes

This contract freezes the execution-environment mechanisms needed to integrate Core and link software without promoting one simulator memory configuration into a universal architectural constant.

Execution-environment decisions belong to three classes:

1. **frozen mechanism** defines behavior that every current profile shall preserve;
2. **profile-resolved value** is software-visible and shall be fixed coherently for each concrete build or deployment; and
3. **implementation-local choice** may vary without becoming a software dependency.

Stage 1 of the exceptions roadmap is complete because these boundaries and the profile-completion rule are frozen. Before software is linked, the selected build profile shall resolve every linker-visible value required by Section 3. Different coherent profiles may select different numerical maps without reopening Core architecture.

The terms **shall**, **shall not**, **should**, and **may** denote a requirement, prohibition, recommendation, and permitted implementation choice, respectively.

## 2. Frozen Architectural and Environment Mechanisms

The following mechanisms are frozen across current profiles:

| Property | Frozen mechanism |
| --- | --- |
| Hart count | One |
| XLEN | 32 |
| ISA exposed to software | RV32I plus Zicsr |
| Initial/current privilege scope | Machine mode only |
| Endianness | Little-endian |
| Software ABI | Freestanding RV32 ILP32 |
| Instruction size/alignment | 32-bit instructions, `IALIGN=32` |
| Execution model | In order, one instruction in flight |
| Architectural addresses | Full 32-bit byte addresses |
| Core memory boundary | Logical Harvard IMEM and DMEM request paths |
| Transaction concurrency | At most one transaction per interface; the baseline Core contract does not overlap IMEM and DMEM requests |
| Mapping ownership | Platform adapters own range checking, mapping/rebasing, routing, backend timing, and backend error reporting |

Core and LSU shall remain memory-map agnostic. A physical deployment may use unified RAM, separate instruction and data memories, ROM plus RAM, BRAM plus external memory, or another adapter-backed topology without changing their architectural interfaces.

Software shall be built for `rv32i_zicsr` and the ILP32 ABI unless the build system uses an equivalent toolchain spelling. Software shall not emit unsupported ISA extensions.

## 3. Profile-Resolved Configuration

### 3.1 Required values

Every concrete simulation build or platform profile shall resolve the following from one coherent configuration source:

| Profile item | Required resolution |
| --- | --- |
| Reset | Aligned `ResetVector`, reset/boot ownership, and fetchable reset target |
| IMEM | Base, size, executable/read permissions, and routing |
| DMEM | Base, size, read/write permissions, and routing |
| Physical topology | Unified or separate backends, ROM/RAM composition, and any aliases |
| Application/startup entry | Exact entry address and its relationship to reset or bootloader handoff |
| Stack | Writable region, top, reserved depth, and non-overlap rule |
| Image placement | Link and load addresses for every allocated section |
| MMIO | Every range, device ABI, and supported access width, or an explicit statement that none exists |
| Required devices | Host communication, timer, and interrupt facilities, or explicit absence |

The RTL adapter parameters, linker script, startup definitions, image loader or boot path, and platform headers shall agree with the selected values. A build is non-compliant when these artifacts disagree even if each artifact is individually valid.

Generated linker fragments, generated symbols, or deliberately synchronized per-profile files should be preferred over duplicated handwritten constants.

### 3.2 Current default direct-preload simulation values

For near-term bring-up, current shared synchronous-RAM adapter defaults and the direct-entry convention provide this convenient example configuration:

```text
ResetVector              = 0x0000_0000
UnifiedRamBaseAddr       = 0x0000_0000
UnifiedRamSizeBytes      = 0x0004_0000
ImemBaseAddr             = 0x0000_0000
ImemSizeBytes            = 0x0004_0000
DmemBaseAddr             = 0x0000_0000
DmemSizeBytes            = 0x0004_0000
application entry        = ResetVector
boot                     = direct preload
MMIO                     = absent
timer/interrupt devices  = absent
```

With these defaults, IMEM and DMEM expose the same physical 256 KiB RAM at `0x0000_0000`–`0x0003_FFFF`. This is evidence of the current adapter configuration, not a Core/LSU invariant or a permanent baseline address map.

The active linker profile shall derive stack placement from configured writable memory and reserved regions. Its stack top equals `0x0004_0000` only when the selected writable region and reservations make that value valid; it is not frozen by this contract.

A smaller simulation memory, larger FPGA BRAM, separate memories, a boot ROM, or external memory may replace these defaults when the complete RTL/software profile changes coherently.

## 4. Reset Contract

On hart reset release, hardware shall guarantee:

| State | Reset-visible guarantee |
| --- | --- |
| Privilege | Machine mode |
| PC | Configured `ResetVector` |
| `ResetVector` alignment | `ResetVector[1:0] == 2'b00` |
| Reset target | Fetchable under the active profile |
| `x0` | Zero |
| `x1`–`x31` | No software-visible value is guaranteed |
| Machine CSRs | Values defined by the [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md) |
| Pending Core intent | No pending GPR, CSR, memory, or trap commit |

The integrated Core shall initialize the PC from the active profile's `ResetVector` and should retain it as a configuration parameter. A direct-entry profile normally sets the linked startup entry equal to `ResetVector`. A bootloader profile may reset into boot code and transfer control to a distinct application entry.

Reset does not establish a C runtime, stack pointer, global pointer, trap handler, argument vector, or process environment.

## 5. Image and Link Contract

The active profile shall generate or supply linker regions corresponding to its configured executable and writable ranges. The following block is only an example for the current default shared-RAM configuration:

```text
MEMORY
{
    RAM (rwx) : ORIGIN = 0x00000000, LENGTH = 0x00040000
}
```

It shall not be copied into another profile unless that profile deliberately selects the same values.

The profile-independent link/startup requirements are:

| Item | Requirement |
| --- | --- |
| Entry symbol | Conventionally `_start`; another explicit symbol may be selected by the profile |
| Entry address | Equals the direct reset target or the address receiving bootloader handoff |
| Text and read-only data | Placed in profile-declared executable/readable memory |
| Writable data and bss | Placed in profile-declared writable memory |
| Stack | Writable, non-overlapping, and reserved by the linker/profile |
| Stack alignment | `sp` is 16-byte aligned at standard ABI procedure entry |
| Heap | Optional; shall not collide with image, stack, or reserved regions |
| Trap vector | Image/platform-defined, four-byte aligned, and in configured executable memory |
| Load/run addresses | Equal unless the profile defines and implements relocation or copying |

The linker shall reject an image that exceeds any selected region or overlaps reserved runtime storage. A flat image, ELF file, hex file, or another lossless container may be used, but load addresses shall match the active profile.

## 6. Startup and ABI Contract

Before entering ordinary C code, startup software shall establish, as applicable:

1. a valid `sp` with 16-byte alignment at the ABI procedure entry;
2. `gp` when required by the selected code model and linker relaxation;
3. `.data` in its linked initial state;
4. a zeroed `.bss`;
5. any platform state required by the active profile;
6. an aligned `mtvec` before software depends on trap recovery;
7. any software trap-frame state; and
8. entry to `main` according to the standard RV32 ILP32 calling convention.

Hardware does not initialize the C runtime. No `argc`, `argv`, environment block, C library initialization, or operating-system service is implied. If `main` returns, startup software shall enter a defined local terminal loop unless the active profile defines another termination service.

ECALL remains an architectural Machine-mode exception. It is not a process-exit or semihosting convention unless a profile explicitly defines such an ABI.

## 7. Boot and Instruction Visibility

Direct preloading is the preferred first simulation mechanism:

```text
simulation harness loads image according to linked load addresses
    -> platform establishes instruction visibility
    -> hart reset is released
    -> PC = configured ResetVector
```

For a direct-entry image, the linker entry and `ResetVector` shall agree. The harness and memory backend shall ensure that the image is present after memory-reset effects and before the first fetch. ELF versus binary versus hex and the preload mechanism itself are implementation-local choices.

A later bootloader profile may use different reset and application entries. Its loader shall establish instruction visibility before handoff and shall define any required relocation, validation, or copying.

Runtime self-modifying code is unsupported. Software shall not rely on a DMEM write becoming executable instruction state. `FENCE.I` and Zifencei are not implemented. Physical use of unified writable memory does not imply runtime instruction/data coherence.

## 8. Access, Fault, and Misalignment Policy

The active profile shall publish every visible instruction, data, and MMIO range and its permissions. Unmapped, permission-invalid, malformed, and backend-failed transactions shall complete as errors and shall never silently return zero, coerce an access, or discard a store.

| Condition | Architectural outcome | `tval` |
| --- | --- | --- |
| Instruction fetch outside configured executable IMEM or backend failure | Instruction access fault | Architectural fetch address |
| Load outside configured readable DMEM/MMIO or backend failure | Load access fault | Effective address |
| Store outside configured writable DMEM/MMIO or backend failure | Store/AMO access fault | Effective address |
| Misaligned halfword load/store | Corresponding address-misaligned exception | Effective address |
| Misaligned word load/store | Corresponding address-misaligned exception | Effective address |
| Taken control target not four-byte aligned | Instruction-address-misaligned exception | Attempted target |

Byte data accesses are naturally aligned. Halfword accesses require `address[0] == 0`; word accesses require `address[1:0] == 2'b00`. The LSU shall reject misaligned data operations locally without issuing DMEM requests. Misaligned-access emulation is not provided.

Each MMIO device shall state its supported widths. Initial MMIO profiles should prefer aligned 32-bit word accesses. Unsupported widths or operations shall fault rather than be silently transformed.

## 9. Ordering and FENCE

The baseline Core contract specifies one hart, one instruction in flight, no speculation, no cache, no store buffer, no out-of-order execution, and no overlapping instruction/data request. A memory operation completes before its instruction can commit and before a later memory operation proceeds.

Under these constraints, base `FENCE` is a legal serialization no-op:

- no GPR write;
- no CSR write;
- no LSU request; and
- sequential PC progression.

Any cache, store buffer, independent DMA master, weaker device ordering, pipelining, speculation, or increased transaction concurrency shall trigger review of FENCE and instruction-visibility semantics.

## 10. First Pure-Core Simulation Milestone

The first integrated pure-Core simulation requires only synchronous exceptions. It requires no UART, timer, MMIO device, host-communication ABI, interrupt source, or interrupt controller. The current default direct-preload profile declares all of those facilities absent.

When no timer is present, any exposed machine-timer pending view shall remain inactive. Machine Timer Interrupt remains the first planned interrupt source, but its timebase, MMIO representation, clock-domain behavior, synchronization, and sampling point remain future platform work.

A testbench may observe completion out of band, but a magic PC, signal, or timeout is not a software-visible ABI unless a later profile explicitly promotes it into one.

## 11. Profile Compliance and Closure

Every concrete simulation or FPGA profile shall publish, in one coherent profile or generated configuration:

1. exact reset and boot vectors;
2. every instruction, data, ROM, RAM, and MMIO range with permissions;
3. supported access widths and fault behavior for every MMIO device;
4. linker regions, image entry, stack placement/reservation, and load/run addresses;
5. image-loading and instruction-visibility guarantees;
6. startup assumptions and any host-termination ABI;
7. required UART or other host communication;
8. timer source, frequency, counter/compare model, and pending generation if present; and
9. all interrupt sources, synchronization, priority, and controller behavior.

An absent facility shall be stated as absent rather than left unspecified. A profile is closed for a particular build only when:

1. the profile records every applicable concrete value;
2. RTL parameters and adapters agree;
3. linker scripts, startup code, and platform headers agree;
4. the image loader or boot path agrees; and
5. directed verification demonstrates the declared map, access, fault, reset, and handoff behavior.

A different deployment may resolve different values without reopening Core architecture. Implementation-local choices and absent future facilities are classified in the [deferred decisions register](RV32I_Execution_Environment_Deferred_Decisions.md).

## 12. Stage 1 Coverage

This contract answers every Stage 1 roadmap question by freezing either a mechanism or a per-profile resolution obligation:

| Stage 1 question | Frozen rule | Current default/example resolution |
| --- | --- | --- |
| Reset vector | Configured, four-byte aligned, and fetchable | `0x0000_0000` |
| Instruction/data ranges | Profile publishes full ranges and permissions; adapters own mapping | Shared `0x0000_0000`–`0x0003_FFFF` views |
| RAM/ROM/MMIO windows | Profile publishes topology and every visible range | 256 KiB shared RAM; no ROM or MMIO |
| Unmapped behavior | Architectural access fault; never silent success | Same |
| MMIO widths | Every device declares supported widths | No MMIO device |
| Misaligned accesses | Trap locally; no hardware emulation | Same |
| FENCE assumptions | Serialized Core; base FENCE is a legal no-op | Same |
| Self-modifying code | Unsupported; no FENCE.I | Same |
| Initial privilege | Machine mode | Same |
| Startup ABI | Freestanding RV32 ILP32; entry and stack are profile-resolved | Direct entry at `ResetVector`; stack derived from writable-memory configuration |
| Host/timer/interrupt devices | Profile declares presence or absence; none required for first pure-Core integration | Absent |

Stage 1 is complete because the execution-environment mechanism is frozen and every concrete build/profile shall resolve a complete, internally consistent memory/reset/link configuration before software is linked. The current direct-preload simulation may use the existing zero-based 256 KiB shared-RAM defaults, but those values are not Core architectural invariants.

## 13. Change Control

Changing a frozen mechanism requires an explicit revision to this contract. Changing a profile-resolved value requires a coherent profile/build update and verification, not a Core architecture revision.

Architectural review is required before adding runtime self-modifying code, Zifencei, cache, memory protection, lower privilege modes, multiple harts, speculative or out-of-order memory execution, multiple outstanding transactions, DMA/coherent masters, or a general interrupt controller.

The governing rule is:

```text
Core architecture freezes mechanisms.
Platform profiles freeze concrete software-visible values.
Build tooling binds the two coherently.
Backend implementation choices remain invisible unless promoted into a profile.
```

## Related Documents

- [Configuration/profile amendment](../RV32I_Execution_Environment_Profile_Amendment.md)
- [Core architecture](RV32I_Core_Architecture.md)
- [Execution-environment deferred decisions](RV32I_Execution_Environment_Deferred_Decisions.md)
- [Core implementation](../Roadmap/RV32I_Core_Implementation.md)
- [Exceptions, traps, and extensions roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)
- [Memory subsystem contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)
- [LSU contract](../Implementation/Execution/RV32I_LSU_Contract.md)
- [Core-owned state contract](../Implementation/State/RV32I_Core_Owned_State_Design_Contract.md)
- [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md)

## Metadata

- Document type: execution-environment mechanism and profile-compliance contract
- Authority: reset, mapping, boot, startup ABI, fault, ordering, profile-resolution, and build-closure rules
- Current-default memory-map evidence: `rtl/mem/rv32_shared_sync_ram_adapter.sv`; Core reset-vector integration remains pending
- Required software artifacts per build: coherent profile values, linker script, startup code, and image loader or boot configuration

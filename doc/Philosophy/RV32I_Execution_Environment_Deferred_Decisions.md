# RV32I Execution-Environment Deferred Decisions Register

**Scope:** Profile-resolved values, implementation-local choices, and genuinely deferred execution-environment facilities

**Mechanism contract:** [RV32I Execution-Environment Contract](RV32I_Execution_Environment_Contract.md)

**Normative clarification:** [RV32I Execution-Environment Configuration/Profile Amendment](../RV32I_Execution_Environment_Profile_Amendment.md)

**Roadmap:** [RV32I Exceptions, Traps, and Extensions Roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose and Classification

This register prevents three different classes of open work from being conflated:

1. a **profile-resolved value** has a frozen mechanism but receives a concrete software-visible value from each build/platform profile;
2. an **implementation-local choice** may remain unspecified because software shall not depend on it; and
3. a **deferred facility** is absent from the current scope and requires later platform or architecture work.

A profile-resolved value is not an unresolved Core architectural decision. Different deployments may choose different values while preserving the same Core and LSU semantics.

## 2. Frozen Mechanism, Profile-Resolved Value

| Decision | Frozen mechanism | Profile-resolved value |
| --- | --- | --- |
| Reset vector | Core starts in M-mode at configured, aligned, fetchable `ResetVector` | Exact address |
| Instruction map | Adapter owns executable ranges and mapping; Core/LSU issue full addresses | Bases, sizes, permissions, and routing |
| Data map | Adapter owns readable/writable ranges and mapping; Core/LSU issue full addresses | Bases, sizes, permissions, and routing |
| Physical memory topology | Logical IMEM and DMEM paths remain distinct at the Core boundary | Unified/separate RAM, ROM, BRAM, external memory, and aliases |
| Application entry | Image entry agrees with direct reset or bootloader handoff | Exact address and symbol placement |
| Stack | Writable, non-overlapping, and 16-byte aligned at ABI procedure entry | Region, top, and reserved depth |
| Image placement | Allocated sections obey declared permissions and capacity | Link addresses and any distinct load addresses |
| Trap handler | Four-byte aligned, executable, and installed in `mtvec` before use | Exact symbol/address |
| MMIO | Every device has an explicit ABI; unsupported accesses fault | Bases, register maps, permissions, and access widths |
| Platform devices | Presence or absence is explicit | Required UART, host, timer, and interrupt facilities |

The active profile shall resolve every applicable row before software is linked. The current adapter defaults of zero-based 256 KiB shared RAM and `ResetVector = 0x0000_0000` are convenient simulation values, not cross-profile invariants. Stack placement shall be derived from the active writable-memory configuration and reservations rather than fixed universally at `0x0004_0000`.

## 3. Implementation-Local Unspecified Choices

| Decision | Frozen boundary |
| --- | --- |
| Image container | Preserves linked addresses and image data |
| RAM initialization mechanism | Establishes image visibility before reset release or boot handoff |
| Top-level reset wiring | Satisfies the Core reset contract and selected profile sequencing |
| Linker section order | Satisfies entry, permissions, capacity, startup, and ABI constraints |
| Trap-handler symbol name | Resolves to the profile-compliant executable handler address |
| Heap/allocator implementation | Remains within writable profile memory and avoids reserved regions |
| C library | Is compatible with the declared freestanding ISA and ABI |
| Test completion observation | Is not software-visible unless a profile defines an ABI |
| Memory latency | Obeys the memory-interface transaction contract |
| Internal backend organization | Does not alter the published architectural map or transaction behavior |

These choices shall not become undocumented software dependencies. If software must know one, it shall be promoted into the active profile or another governing contract.

## 4. Deferred Platform Facilities

The following facilities are not required by the first pure-Core simulation milestone:

| Deferred facility | Required before support is claimed |
| --- | --- |
| FPGA board/profile | Board identity, clocks, reset source, and exact top-level configuration |
| Boot ROM or bootloader | Reset entry, image format, transport, validation, placement, application entry, visibility, and handoff |
| UART or other console | MMIO address, register map, access widths, clock/baud policy, and fault behavior |
| Software-visible completion service | Exact MMIO, semihosting, ECALL, or other ABI and its error behavior |
| General MMIO device set | Every range, device ABI, access width, side effect, ordering rule, and unmapped behavior |
| Timer | Timebase, counter/compare semantics, clock-domain handling, MMIO map, and pending generation |
| Interrupt integration | Sources, synchronization, eligibility, priority, sampling point, and controller behavior |
| DDR or other external memory | Map, initialization, latency, failure model, and instruction-visibility behavior |
| DMA or independent memory masters | Arbitration, ordering, visibility, and FENCE/coherency implications |

An additional deployment shall resolve every facility it includes in a named profile. A facility not included shall be declared absent rather than left implicit.

## 5. Deferred Architectural Scope

The following changes require architectural review rather than only new profile values:

- runtime self-modifying code and Zifencei;
- caches, store buffers, speculation, or out-of-order memory execution;
- multiple outstanding transactions or multiple harts;
- lower privilege modes, PMP, MMU, or virtual memory;
- software and external interrupt families or a general interrupt controller; and
- coherent or cache-visible independent masters.

Introducing one of these features shall trigger review of the Core architecture, memory-subsystem contract, FENCE semantics, fault policy, and execution-environment contract.

## 6. Closure Rules

A profile-resolved item is closed for a particular build/profile only when:

1. the profile records its concrete value;
2. RTL parameters and adapters agree;
3. linker scripts, startup code, and platform headers agree;
4. the image loader or boot path agrees; and
5. directed verification demonstrates the declared access, fault, reset, and handoff behavior.

An implementation-local choice remains open only while it preserves its frozen boundary and stays invisible to software. A deferred facility is closed only after its governing profile or architecture contract and verification evidence exist.

Stage 1 remains complete at the mechanism level while each concrete build remains responsible for profile closure. A different deployment may legitimately resolve different numerical values without reopening Core architecture.

## Metadata

- Document type: profile-resolution and deferred-decision register
- Authority: classification and closure of open execution-environment work
- Mechanism authority: [RV32I Execution-Environment Contract](RV32I_Execution_Environment_Contract.md)

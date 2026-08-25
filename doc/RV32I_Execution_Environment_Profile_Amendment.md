# RV32I Execution-Environment Contract — Configuration/Profile Amendment

**Applies to:**
- [RV32I Execution-Environment Contract](Philosophy/RV32I_Execution_Environment_Contract.md)
- [RV32I Execution-Environment Deferred Decisions Register](Philosophy/RV32I_Execution_Environment_Deferred_Decisions.md)

**Status:** Normative amendment, incorporated into both named documents. If a residual conflict remains, this amendment takes precedence.

## 1. Purpose

The execution-environment documents currently mix three different classes of decision:

1. architectural/environment mechanisms that must be stable for Core integration;
2. values resolved by a particular simulation or FPGA platform profile; and
3. implementation-local choices that software must not depend upon.

This amendment separates those classes and removes accidental promotion of the current simulation RAM parameters into permanent baseline architectural constants.

Stage 1 remains complete when a concrete build/profile resolves the required linker-visible values coherently. Stage 1 does **not** require all future deployments to use one fixed numerical memory map.

---

## 2. Normative profile model

The execution-environment contract shall distinguish:

### 2.1 Frozen mechanism

The following mechanisms are frozen across current profiles:

- one RV32 hart, initially Machine mode only;
- RV32I + Zicsr software-visible ISA, subject to later explicitly documented additions;
- ILP32 psABI-compatible freestanding software environment;
- `IALIGN=32`;
- full 32-bit architectural byte addresses;
- logical Harvard IMEM and DMEM request paths;
- adapter-owned architectural range checking, rebasing/mapping, backend timing, and backend error reporting;
- access faults for unmapped/failed transactions;
- locally trapped misaligned accesses with no hardware emulation;
- strongly serialized baseline memory execution, making base `FENCE` a legal serialization no-op;
- no runtime self-modifying-code guarantee and no Zifencei / `FENCE.I`;
- C-runtime initialization performed by startup software rather than hardware;
- no required UART, timer, MMIO device, or interrupt source for the first pure-Core simulation milestone.

These rules are architectural/environment policy and do not vary merely because memory capacity changes.

### 2.2 Profile-resolved values

Every concrete build or platform profile shall resolve, from one coherent configuration source:

```text
ResetVector
IMEM base
IMEM size
DMEM base
DMEM size
executable/data permissions
application/startup entry
stack location/reservation
MMIO ranges, if any
load/run addresses, if distinct
```

These are not universal constants of the Core.

The RTL adapter parameters, linker script, startup definitions, simulation loader, and platform headers shall agree with the resolved profile values.

### 2.3 Implementation-local choices

The following may remain unspecified unless software-visible behavior depends on them:

```text
ELF vs binary vs hex image container
simulation RAM preload mechanism
top-level reset polarity/adaptation
backend memory latency
internal BRAM organization
linker section ordering beyond required ABI/startup constraints
choice of freestanding C library
presence and implementation of a heap
out-of-band simulation completion observation
```

---

## 3. Amendment to the frozen Execution-Environment Contract

### 3.1 Status and purpose

Replace the interpretation:

> “Frozen for the baseline simulation profile” means the numerical map currently used by the simulator is permanently frozen.

with:

> The execution-environment **mechanism and profile requirements** are frozen. A concrete baseline simulation build shall resolve a complete map before linking, but numerical memory bases, capacities, entry addresses, and stack addresses are profile values and may change between coherent deployment configurations.

A build is compliant only when its resolved RTL and software configuration agree.

### 3.2 Baseline memory map

The fixed 256 KiB region

```text
0x0000_0000 - 0x0003_FFFF
```

shall no longer be normative for all baseline simulation builds.

Instead, the baseline simulation profile shall be described symbolically:

```text
UnifiedRamBaseAddr / UnifiedRamSizeBytes
or
ImemBaseAddr / ImemSizeBytes
DmemBaseAddr / DmemSizeBytes
```

depending on the selected adapter topology.

The currently implemented/default shared-RAM values:

```text
base = 0x0000_0000
size = 0x0004_0000
```

may be documented as a **current default/example configuration**, not as an architectural requirement.

A smaller simulation memory, a larger FPGA BRAM allocation, or a later external-memory region may replace these values without changing Core/LSU semantics.

### 3.3 Unified versus separate memory

The current shared synchronous-RAM adapter is one deployment implementation, not a permanent environment requirement.

The frozen requirement is:

```text
logical IMEM path
logical DMEM path
```

A profile may map them onto:

- the same physical RAM;
- separate RAMs;
- ROM plus RAM;
- BRAM plus external memory; or
- another adapter-backed organization.

Any such profile shall publish the visible ranges and permissions.

### 3.4 Reset vector

`ResetVector = 0x0000_0000` is demoted from universal baseline requirement to current/default simulation-profile value.

The normative requirement is:

```text
PC on hart reset release = configured ResetVector
ResetVector[1:0] = 2'b00
configured ResetVector is fetchable in that profile
```

The integrated Core should retain `ResetVector` as a configuration parameter.

Future FPGA profiles may reset into a boot ROM/loader at another address without changing CPU architectural semantics.

### 3.5 `_start` and image entry

The entry symbol may conventionally remain `_start`, but its numerical address shall not be universally fixed to zero.

The normative relationship is:

```text
link/startup entry address
    ==
the address to which the selected boot/reset mechanism transfers control
```

For direct-preload simulation this may equal `ResetVector`.

For a future bootloader profile, the bootloader reset entry and application entry may differ.

### 3.6 Stack placement

`0x0004_0000` shall not be a universal stack-top requirement.

The normative requirements are:

```text
stack lies in writable memory defined by the active profile
stack does not overlap allocated image/runtime regions
sp is 16-byte aligned at standard ABI procedure entry
```

The linker/profile shall derive the concrete stack location from the active writable-memory configuration and any reserved regions.

### 3.7 Linker MEMORY block

The literal block:

```text
RAM (rwx) : ORIGIN = 0x00000000, LENGTH = 0x00040000
```

shall be treated only as an example/current simulation configuration.

The baseline software deliverable shall instead obtain `ORIGIN`, `LENGTH`, and stack placement from the same profile values used to configure the memory adapter.

The project should prefer a generated linker fragment, generated symbols, or a deliberately synchronized per-profile linker script over duplicated handwritten constants.

### 3.8 Trap-handler address

The trap-handler policy is frozen as:

```text
image/platform-defined
four-byte aligned
located in memory executable by the active profile
startup writes its address to mtvec before software depends on trap recovery
```

It shall not be described specifically as residing in RAM unless a particular profile requires that.

### 3.9 Startup ABI

The following are frozen independently of numerical memory placement:

Before entering ordinary C code, startup software shall establish as applicable:

```text
sp valid and 16-byte aligned
gp initialized when required by the selected code/link model
.data in its linked initial state
.bss zeroed
required platform state initialized
mtvec initialized before software depends on a trap handler
main entered according to the standard RV32 ILP32 calling convention
```

Hardware does not initialize the C runtime.

The reset values of GPRs other than `x0` remain unspecified to software.

### 3.10 Direct-preload simulation boot

Direct preloading remains the preferred first simulation mechanism, but its addresses are profile-resolved:

```text
simulation harness loads image according to linked load addresses
image becomes fetch-visible
hart reset is released
PC = configured ResetVector
```

For a direct-entry image, the linker entry and ResetVector shall agree.

The preload mechanism itself remains implementation-local.

### 3.11 Instruction visibility and self-modifying code

A profile may physically use unified writable RAM for IMEM and DMEM without advertising runtime self-modifying-code support.

The contract remains:

```text
runtime software shall not rely on a DMEM write becoming executable instruction state
FENCE.I / Zifencei are unsupported
```

Pre-reset or bootloader-controlled image loading is permitted only when the platform establishes instruction visibility before handoff.

If later software is allowed to modify executable memory while running, this contract and FENCE/instruction-visibility semantics shall be revisited.

### 3.12 MMIO

The first simulation profile may contain no MMIO.

For a later MMIO profile:

- addresses and register semantics are profile ABI;
- initial device policy should prefer aligned 32-bit word accesses;
- every device shall state supported widths;
- unsupported accesses shall fault rather than be silently coerced.

No universal MMIO base address is frozen here.

### 3.13 Timer and interrupts

The first integrated simulation profile requires only synchronous exceptions.

Timer and interrupt hardware may be absent; if absent, any exposed pending view selected for future timer integration shall remain inactive.

Machine Timer Interrupt remains the first planned interrupt source, but its timer source, MMIO representation, clock semantics, and synchronization remain platform work.

Richer interrupt sources remain a future extension and shall not be precluded by Core trap arbitration interfaces.

### 3.14 Stage 1 completion wording

Replace the Stage 1 claim that software is linked against one permanently fixed 256 KiB map with:

> Stage 1 is complete because the execution-environment mechanism is frozen and every concrete build/profile must resolve a complete, internally consistent memory/reset/link configuration before software is linked. The current direct-preload simulation profile may use the existing 0-based 256 KiB RAM configuration, but that value is not a Core architectural invariant.

---

## 4. Amendment to the Deferred-Decisions Register

The register shall use three categories instead of treating every unresolved item identically.

### 4.1 Frozen mechanism, unresolved profile value

The following are no longer architecturally unspecified; their **mechanism is frozen while the value remains profile-resolved**:

| Decision | Frozen mechanism | Profile-resolved value |
| --- | --- | --- |
| Reset vector | Core starts at configured aligned `ResetVector` in M-mode | Exact address |
| Instruction/data map | Adapters own ranges and mapping; Core/LSU use full addresses | Base, size, permissions |
| Application entry | Link/boot handoff and image entry must agree | Exact address/symbol placement |
| Stack | Writable, non-overlapping, 16-byte-aligned at ABI entry | Top and reserved depth |
| Trap handler | Executable, aligned, startup-installed in `mtvec` when needed | Exact symbol/address |
| MMIO | Explicit per-platform device ABI; unsupported accesses fault | Bases/register maps/access widths |

These items should not be described as lacking an architectural decision.

### 4.2 Implementation-local unspecified choices

Retain as implementation-local:

| Decision | Boundary |
| --- | --- |
| Image container | Must preserve linked addresses/data |
| RAM initialization mechanism | Image fetch-visible before reset release/handoff |
| Top-level reset wiring | Must satisfy Core reset contract |
| Section ordering | Must satisfy linker/startup/ABI constraints |
| Heap/allocator | Must remain within writable profile memory |
| C library | Must be compatible with the declared freestanding ISA/ABI |
| Test completion observation | Not software-visible unless a later profile defines an ABI |
| Memory latency | Must obey the memory-interface transaction contract |

### 4.3 Deferred facilities

Retain as genuinely deferred platform/architecture work:

```text
FPGA board/profile identity
boot ROM / UART bootloader protocol and implementation
UART console/MMIO
software-visible host completion service
general MMIO device set
timer source and timer MMIO
interrupt integration beyond current synchronous traps
DDR/external memory
DMA/independent memory masters
runtime self-modifying code / Zifencei
caches/store buffers/speculation
lower privilege modes/PMP/MMU
multiple harts
general interrupt controller
```

### 4.4 Remove conflicting fixed-value statements

The deferred register shall not state as universal baseline facts:

```text
hart reset PC = 0x0000_0000
_start = 0x0000_0000
stack top = 0x0004_0000
RAM size = 256 KiB
```

If those values remain useful, label them explicitly:

```text
current default direct-preload simulation profile
```

and keep them outside the cross-profile frozen boundary.

### 4.5 Closure rule

A profile-resolved item is closed for a particular build/profile when:

1. the profile records its concrete value;
2. RTL parameters/adapters agree;
3. linker/startup/platform headers agree;
4. the loader/boot path agrees; and
5. directed verification demonstrates the declared access, fault, reset, and handoff behavior.

A different deployment may legitimately resolve different values without reopening Core architecture.

---

## 5. Current default simulation profile

For convenience, the project may continue to use the current implementation values during near-term Core bring-up:

```text
ResetVector              = 0x0000_0000
UnifiedRamBaseAddr       = 0x0000_0000
UnifiedRamSizeBytes      = 0x0004_0000   # 256 KiB
direct-preload boot      = yes
MMIO                     = absent
timer/interrupt devices  = absent
application entry        = ResetVector
stack                    = derived from configured writable-memory end/reservation
```

These values constitute a convenient **default simulation profile**, not a permanent execution-environment or Core invariant.

A smaller simulation memory may be selected when sufficient for the linked image. The linker/profile must change coherently with the RTL configuration.

---

## 6. Additional consistency corrections

The following wording should also be normalized when the parent documents are next consolidated:

- Refer to a trap handler as residing in **configured executable memory**, not necessarily “executable RAM”.
- Refer to the current shared-RAM adapter as one implementation/profile, not as the architectural memory topology.
- Keep the logical Harvard interface requirement separate from physical unified-memory implementation.
- Treat `ECALL` only as a Machine-mode exception unless a separate semihosting/host ABI is explicitly defined.
- Do not make simulation completion through a magic PC, signal, or timeout into an undocumented software ABI.
- Do not infer runtime instruction/data coherence merely because a simulation backend happens to use one physical RAM.
- Keep UART boot, timer semantics, and richer peripheral interrupts deferred until their platform profiles are designed.

---

## 7. Resulting design rule

The final rule is:

```text
Core architecture freezes mechanisms.
Platform profiles freeze concrete software-visible values.
Build tooling binds the two coherently.
Backend implementation choices remain invisible unless promoted into a profile.
```

This permits the current small direct-preload simulation, a BRAM-based FPGA system, and a later DDR-backed platform to reuse the same Core without treating changes in memory capacity or boot placement as architectural redesigns.

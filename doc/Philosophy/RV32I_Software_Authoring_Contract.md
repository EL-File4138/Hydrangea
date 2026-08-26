# RV32I Software Authoring Contract

**Scope:** Deployment-programmed images, linker layout, startup-shim behavior, runtime handoff, and platform binding

**Status:** Normative software-authoring contract

**Execution environment:** [RV32I Execution-Environment Contract](RV32I_Execution_Environment_Contract.md)

**Platform roadmap:** [RV32I SoC and Platform Roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md)

**Core architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

## 1. Purpose and Authority

This contract defines what a deployment-programmed software image may choose and what it shall consume from the SoC/platform. It separates image construction from physical memory and device implementation.

The software image owns section placement, runtime storage reservation, startup initialization, trap-handler installation, and application handoff. It does not define physical RAM capacity, executable/read/write accessibility, MMIO decoding, peripheral behavior, or the Core reset PC. Those remain SoC/platform or Core-parameter authorities.

The terms **shall**, **shall not**, **should**, and **may** denote a requirement, prohibition, recommendation, and permitted choice, respectively.

## 2. Baseline Software Model

Baseline software shall target:

| Property | Requirement |
| --- | --- |
| ISA | RV32I plus Zicsr |
| ABI | Freestanding RV32 ILP32 |
| Endianness | Little-endian |
| Canonical image | ELF32 little-endian RISC-V executable |
| C runtime | Startup shim followed by an explicit application handoff |
| C library | None required |
| Process environment | None implied |

Compiler-runtime support such as `libgcc` may be linked when generated code requires it. A compatible freestanding C library may be added by an application without changing the hardware contract.

Binary or hexadecimal derivatives may be generated from the canonical ELF for a simulator, FPGA initialization flow, or later bootloader transport. Such derivatives shall preserve the ELF load addresses and initialized bytes.

## 3. Authority Matrix

| Property | Deployment-Programmed Image Scope | Authority |
| --- | ---: | --- |
| `_start` placement | Yes | `link.ld` |
| `.text/.rodata/.data/.bss` layout | Yes | `link.ld` |
| Stack location/size | Yes | Linker symbols plus `start.S` |
| Initial `sp` | Yes | `start.S` |
| Heap location/size | Yes, including no heap | Linker/runtime |
| Trap-handler location | Yes | Linker |
| Initial `mtvec` | Yes | `start.S` |
| `gp` initialization | Yes | Linker plus `start.S` |
| `.bss` initialization | Yes | `start.S` |
| `.data` relocation policy | Yes | Linker/startup |
| Application entry after startup | Yes | Startup/runtime |
| MMIO symbolic addresses used by drivers | Yes, provided they match the platform | Platform header/linker configuration |
| Physical RAM base/size | No | SoC/platform |
| Actual MMIO decode/ranges | No | SoC/platform |
| Peripheral existence/register behavior | No | SoC/platform |
| Core reset PC | No, not at runtime | `ResetVector` hardware parameter |
| Executable/read/write accessibility | No | SoC/memory implementation |

An image may consume SoC-generated linker regions, symbols, headers, or a discoverable platform structure. Consuming those values does not transfer authority for the physical map to software. A linked image is valid only for platforms whose published ranges and permissions admit every load and run address it uses.

## 4. Linker and Image Layout

The canonical linker order is:

1. `_start` and the startup shim at the selected startup entry;
2. executable code and trap/vector material;
3. read-only data;
4. initialized writable data;
5. zero-initialized data;
6. an optional heap after static allocation; and
7. a stack reservation growing downward from the high end of a selected writable region.

Exact addresses remain platform-derived and image-programmed. The execution-environment contract does not assign universal text, data, heap, stack, trap, or application-entry addresses.

The linker shall:

- keep `_start` at the selected startup entry;
- reject section overflow and overlap;
- export symbols for data relocation, BSS initialization, heap bounds when present, and stack limits;
- keep the stack 16-byte aligned at standard ABI procedure entry;
- reserve executable storage for `__mtvec_base`; and
- preserve any platform-reserved loader, configuration, MMIO, or firmware regions.

The baseline runtime requires no heap and no allocator. An application that needs one may reserve it between the end of static allocation and the stack or another platform-provided writable limit.

A discovery-aware startup shim may calculate stack or heap bounds dynamically from the platform description reached through `mconfigptr`. In that mode, the linker and platform ABI shall still reserve non-overlapping maximum regions so that runtime selection cannot collide with loaded sections or platform storage.

## 5. Startup Shim Contract

The startup shim begins at `_start` after direct reset or a boot-stage handoff. Before transferring control to the application, it shall perform every operation required by the selected image mode:

1. establish `gp` when required by the code model and linker relaxation;
2. obtain static platform symbols or inspect the platform description referenced by `mconfigptr`;
3. select and align the initial stack pointer;
4. relocate `.data` when load and run addresses differ;
5. zero `.bss`;
6. establish any selected heap bounds;
7. write the address of `__mtvec_base` to `mtvec` before software relies on trap recovery;
8. establish any software trap-frame state;
9. complete any selected boot-time UART programming flow; and
10. transfer control to the image-selected application entry using the RV32 ILP32 calling convention.

The application entry is a software handoff after startup; it is not the Core reset PC. A direct-entry image may place `_start` at `ResetVector`. A boot or programming shim may instead receive control first and transfer to a distinct application entry.

If the application entry returns, the baseline shim shall enter a defined local halt loop. It shall not infer a process-exit service from ECALL.

## 6. Platform Discovery and Binding

Platform discovery is rooted at the read-only Machine-mode `mconfigptr` CSR. A nonzero supported value shall identify a versioned, readable platform-description structure defined by the SoC/platform contract. That structure describes physical memory topology and Core-aware MMIO behavior needed by generic startup or drivers. Software shall not attempt to write the pointer.

Software shall treat zero as “no discoverable configuration” and may then run only when statically linked against a matching platform configuration. The structure format, versioning, addressability, and trust rules remain work in the [SoC and platform roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md#5-platform-discovery-roadmap).

MMIO symbols used by software shall come from the matching platform description, generated header, or linker configuration. Software shall not invent an address and thereby make it part of the Core contract.

## 7. UART Self-Programming and Image Loading

UART self-programming belongs to the startup-shim architecture, but it is platform-coupled. A deployment that enables it shall provide a SoC-defined UART ABI, writable destination storage, image framing and validation rules, and an instruction-visibility handoff.

The shim shall not assume a UART address, baud policy, register layout, or destination memory map until the SoC contract supplies them. Loading executable bytes before application handoff is a boot operation, not permission for application runtime self-modifying code. Because Zifencei is absent, the platform shall establish instruction visibility before control reaches newly loaded code without requiring the application to execute `FENCE.I`.

## 8. Trap and Interrupt Software

`__mtvec_base` is the standard trap-entry symbol. `start.S` shall write its address to `mtvec` before enabling or depending on traps.

Under the baseline Direct-mode trap contract, `__mtvec_base` names one handler entry. As a project milestone choice, the first timer-interrupt milestone shall deliver Vectored-mode support before timer support is claimed. When that mode is selected, the same symbol names the aligned vector-table base.

Trap software shall preserve the ABI state it uses, inspect `mcause`, `mepc`, and `mtval`, update `mepc` only under a defined recovery policy, and return with MRET. Timer-interrupt software shall not be claimed until the SoC timer source, Core interrupt sampling, Vectored-mode behavior, and platform ABI are all implemented and tested.

## 9. Runtime and Test Policies

- No production software-visible exit ABI is defined.
- Simulation testbenches may observe completion out of band.
- A test package may define a `__test_done` symbol or halt loop, but it is not a platform ABI.
- Runtime self-modifying code is out of scope. Writable physical memory does not create an instruction-coherence guarantee.
- Software shall not emit `FENCE.I` until Zifencei is implemented and documented.
- No operating-system process model, arguments, environment, or system-call ABI is implied.

## 10. Conformance and Change Control

A deployment image is conforming only when:

1. its ELF class, endianness, ISA, and ABI match this contract;
2. every section and runtime reservation fits a published platform range with the required permissions;
3. `_start` is reached by reset or a documented handoff;
4. startup establishes all state used by the application;
5. MMIO symbols match the selected SoC/platform;
6. image-loading establishes instruction visibility before execution; and
7. directed software tests cover the selected startup, trap, loading, and handoff paths.

Changing linker layout or runtime policy does not change Core architecture while these boundaries hold. Adding a software-visible device ABI, boot protocol, discovery structure, or exit service requires a matching SoC/platform contract update.

## Related Documents

- [Execution-environment contract](RV32I_Execution_Environment_Contract.md)
- [SoC and platform roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md)
- [Exceptions, traps, and extensions roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)
- [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md)

## Metadata

- Document type: software-authoring and deployment-image contract
- Software authority: this contract; each deployment supplies conforming linker, startup, runtime, generated-platform, and image-building artifacts
- Hardware authority: Core, memory, and future SoC contracts linked above

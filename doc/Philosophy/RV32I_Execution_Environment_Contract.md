# RV32I Execution-Environment Contract

**Scope:** Core reset, architectural address model, memory transaction/fault boundary, startup handoff, and authority separation

**Status:** Frozen cross-boundary mechanisms; SoC/platform hardware and deployment-image values close under their own authorities

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Software contract:** [RV32I Software Authoring Contract](RV32I_Software_Authoring_Contract.md)

**Platform roadmap:** [RV32I SoC and Platform Roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md)

**Memory boundary:** [RV32I Memory Subsystem Design Contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)

## 1. Purpose and Authority Classes

This contract freezes the mechanisms that Core, SoC/platform hardware, and a deployment-programmed image shall share. It does not assign one simulator's addresses or one linker's section layout to every deployment.

Decisions belong to four authority classes:

1. **Core/environment mechanism** is invariant across the supported deployment class;
2. **SoC/platform-resolved hardware** defines reset integration, the physical map, permissions, devices, and error behavior;
3. **deployment-programmed image** defines section layout, runtime reservations, startup state, trap installation, and application handoff; and
4. **implementation-local choice** may vary while remaining invisible across the relevant boundary.

The [software contract](RV32I_Software_Authoring_Contract.md) owns image-programmed values. The [SoC and platform roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md) owns undecided surrounding hardware. This contract owns only the rules that bind them to Core.

The terms **shall**, **shall not**, **should**, and **may** denote a requirement, prohibition, recommendation, and permitted implementation choice, respectively.

## 2. Frozen Core and Environment Mechanisms

| Property | Frozen mechanism |
| --- | --- |
| Hart count | One |
| XLEN | 32 |
| ISA exposed to software | RV32I plus Zicsr |
| Privilege scope | Machine mode only |
| Endianness | Little-endian |
| Software ABI | Freestanding RV32 ILP32 |
| Instruction size/alignment | 32-bit instructions, `IALIGN=32` |
| Execution model | In order, one instruction in flight |
| Architectural address model | One unified 32-bit byte-address space used by instruction fetches and data accesses |
| Core memory boundary | Separate logical IMEM and DMEM requester interfaces |
| Harvard status | Logical interface separation is microarchitectural, not two software-visible address spaces |
| Transaction concurrency | At most one transaction per interface; baseline Core does not overlap IMEM and DMEM transactions |
| Mapping ownership | SoC/platform adapters own ranges, permissions, decoding, routing, local-address translation, and backend errors |
| Fault boundary | External memory errors are converted by LSU/Core into architectural access-fault exceptions |

Core and LSU shall issue ordinary full-width architectural addresses and remain unaware of RAM, ROM, MMIO, aliases, and physical topology. A platform may route both logical paths to one unified RAM or to different physical backends while preserving one coherent architectural map.

Software shall be built for `rv32i_zicsr` and ILP32 unless the toolchain uses an equivalent spelling. It shall not emit unsupported extensions.

## 3. Authority-Resolved Configuration

### 3.1 Core parameter and platform scope

| Item | Authority | Cross-boundary requirement |
| --- | --- | --- |
| `ResetVector` | SoC/platform configures the Core parameter | Four-byte aligned and fetchable when reset is released |
| Physical RAM/ROM | SoC/platform | Published in the unified address map with permissions |
| MMIO and peripherals | SoC/platform | Explicit decode, register behavior, widths, and errors |
| Unmapped regions | SoC/platform | Complete with external error; never silent success |
| Physical topology | SoC/platform | Invisible to Core and compatible with the published map |
| Platform discovery | SoC/platform through read-only `mconfigptr` | Versioned description when implemented; zero means unavailable |
| Image sections and reservations | Deployment image | Fit and obey the selected platform map |
| Startup and application entry | Deployment image | `_start` is reached by reset or documented handoff; application follows startup |
| Stack, heap, and trap handler | Deployment image | Established without overlap and within permitted memory |
| Image transport | Platform plus deployment image | Preserve load addresses and establish instruction visibility |

`ResetVector = 0x0000_0000` is a usable default profile value. It is not a portable Core invariant and software cannot change it at runtime.

The execution-environment contract does not require universal numerical values for instruction/data sections, stack, heap, `mtvec`, trap handlers, or application entry. Those values are deployment-programmed under the software contract and constrained by the selected SoC/platform.

### 3.2 Deployment binding and image scope

The deployment image owns `_start`, section layout, stack and optional heap reservations, initial `sp` and `gp`, data/BSS initialization, `__mtvec_base`, initial `mtvec`, and application handoff. The complete authority matrix is in [Section 3 of the software contract](RV32I_Software_Authoring_Contract.md#3-authority-matrix).

A linker or startup shim may consume generated platform values or discover bounds through `mconfigptr`. It shall not redefine the physical map. Dynamic stack or heap sizing is permitted only within platform-published regions reserved against collision.

## 4. Reset Contract

The SoC shall configure `ResetVector[1:0] == 2'b00`. On reset release, hardware shall guarantee:

| State | Reset-visible guarantee |
| --- | --- |
| Privilege | Machine mode |
| PC | Configured `ResetVector` |
| Reset target | Fetchable in the SoC/platform map |
| `x0` | Zero |
| `x1`–`x31` | No software-visible value guaranteed |
| Machine CSRs | Values defined by the [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md) |
| Pending Core intent | No pending GPR, CSR, memory, or trap commit |

The SoC shall preserve the active-low Core-facing `rst_ni` convention, place Core and adapters in their specified reset states, and release execution only after the configured reset target is visible. Exact board wiring, clock/reset sources, synchronization, and sequencing belong to the SoC/platform contract.

Reset does not establish a stack, global pointer, C runtime, trap handler, arguments, or process environment. The startup shim owns those operations.

## 5. Unified Address, Access, and Fault Contract

Instruction fetches and data operations use one architectural address space. Separate IMEM and DMEM interfaces identify transaction role and permit different routing or permissions; they do not grant software separate pointer domains.

The SoC/platform shall publish every RAM, ROM, MMIO, alias, reserved, and unmapped range and the applicable instruction/read/write permissions. An adapter shall return `ready && err` for any unmapped, permission-invalid, unsupported-width, malformed, or backend-failed transaction.

LSU/Core shall convert that error according to the transaction role:

| External failure | Architectural outcome | `tval` |
| --- | --- | --- |
| Instruction fetch | Instruction access fault | Architectural fetch address |
| Load | Load access fault | Effective address |
| Store | Store/AMO access fault | Effective address |

The platform shall not silently return zero, coerce an unsupported access, or discard a failed store.

The LSU owns natural-alignment checks before DMEM issue. Byte accesses are naturally aligned; halfword accesses require `address[0] == 0`; word accesses require `address[1:0] == 2'b00`. Misaligned data operations trap locally and do not issue an external request. Taken control targets remain subject to `IALIGN=32` checks.

Specific MMIO design remains deferred to the SoC/platform roadmap. Each future device shall define supported widths and return an error for unsupported operations.

## 6. Startup, ABI, and Application Handoff

The canonical deployment image is an ELF32 little-endian RISC-V executable. Binary and hexadecimal forms are transport derivatives. Detailed linker and startup requirements are normative in the [software authoring contract](RV32I_Software_Authoring_Contract.md).

The startup shim runs before the application and, as selected by the image, establishes `gp`, `sp`, data relocation, BSS initialization, trap entry through `__mtvec_base`, optional heap bounds, and any platform binding. It then transfers control to an image-selected application entry using RV32 ILP32.

The startup entry and application entry are distinct roles even when a minimal image places them together. A direct-reset deployment normally places `_start` at `ResetVector`; a bootloader or programming shim may hand control to `_start` at another platform-valid address.

UART self-programming is assigned to the startup-shim architecture and depends on a SoC definition of UART MMIO, destination storage, image validation, and instruction-visibility behavior.

No libc, heap, host-exit ABI, semihosting convention, or operating-system service is required. ECALL remains an architectural Machine-mode exception unless a future platform explicitly defines another software ABI.

## 7. Platform Discovery Through `mconfigptr`

Platform discovery shall use the read-only Machine-mode `mconfigptr` CSR as its root. A nonzero supported value points to a versioned platform-description structure containing the physical-memory and Core-aware MMIO information made discoverable to software. Software writes shall not populate or relocate this pointer.

Zero denotes that no discoverable platform structure is provided. Software shall then use only a statically matched linker/header configuration.

The SoC/platform roadmap owns the structure format, pointer value, storage, versioning, trust model, and agreement tests. Adding the structure requires coherent changes to SoC RTL, CSR behavior, generated software inputs, startup parsing, and documentation.

## 8. Image Loading and Instruction Visibility

A simulation deployment using direct ELF preload shall load each `PT_LOAD` segment at its linked load address before reset release. A harness that injects raw test words is a verification mechanism, not evidence of ELF-image loading.

An FPGA first-deployment flow shall place the ELF-derived image into designed executable storage through the selected configuration/JTAG mechanism. BRAM initialization may be part of the FPGA configuration image; external DRAM requires a platform-defined initialization or loading path.

A later bootloader transport belongs to the SoC/platform contract. It shall define image format, validation, placement, failure behavior, instruction visibility, and handoff.

Physical writable/executable memory may permit bytes to be changed, but application runtime self-modifying code is out of scope. The baseline excludes Zifencei and `FENCE.I`, so software shall not rely on a DMEM write becoming executable instruction state. Platform-controlled loading before reset release or application handoff is allowed only when the platform establishes visibility without requiring unsupported instructions.

## 9. Memory Ordering and FENCE

The baseline Core has one hart, one instruction in flight, no cache, no store buffer, no speculation, no out-of-order execution, and no overlapping IMEM/DMEM request. A memory instruction completes before normal commit and before a later memory operation proceeds.

Under these constraints, base FENCE is a legal serialization no-op:

- no GPR write;
- no CSR write;
- no LSU request; and
- sequential PC progression.

No cache, store buffer, speculative memory path, parallel Core transaction, multiple hart, coherent/cache-visible independent master, PMP, MMU, virtual memory, or lower privilege mode is in baseline scope. These are explicit non-goals rather than unassigned profile choices.

## 10. Minimal Platform Contract

A minimal Core deployment requires only executable/readable/writable memory and synchronous exceptions. UART, MMIO devices, timers, interrupt sources, platform discovery, and a production host ABI may all be absent.

A testbench may observe completion out of band. A test-only `__test_done` symbol or halt loop may be standardized by a test package, but it shall not become a production platform ABI implicitly.

The machine timer interrupt is the first planned asynchronous source. Its SoC device and Core integration are separate roadmap obligations. As a project milestone choice, Vectored-mode trap support shall be delivered with and treated as a prerequisite for claiming timer support; this is not an ISA requirement that timer interrupts use Vectored mode. The baseline trap contract remains Direct-mode only until that milestone closes.

## 11. Cross-Authority Closure

A concrete deployment is closed only when all applicable authorities agree:

### 11.1 Core/environment closure

- `ResetVector`, transaction protocol, address width, alignment, and fault conversion obey this contract; and
- Core/module verification covers the selected behavior.

### 11.2 SoC/platform closure

- reset, clock, unified map, permissions, routing, devices, errors, and image visibility are published and verified; and
- discovery data, when present, matches the implemented platform.

### 11.3 Deployment-image closure

- linker regions and symbols fit the selected platform;
- startup establishes all state consumed by the application;
- MMIO symbols match the platform; and
- the canonical ELF and any transport derivatives preserve placement.

### 11.4 Integration closure

- the loader or boot path agrees with ELF load addresses;
- executable bytes are visible before reset release or handoff;
- unsupported accesses produce external errors and architectural faults; and
- directed tests demonstrate reset, startup, memory, trap, and application handoff.

The execution-environment contract itself no longer carries every deployment's numerical software layout or SoC map.

## 12. Decision Disposition

| Question | Disposition |
| --- | --- |
| Reset PC | Platform-configured Core parameter; zero is only a default example |
| Instruction/data address spaces | One architectural address space; two logical Core interfaces |
| RAM/ROM/MMIO ranges | SoC/platform contract and roadmap |
| Unmapped/unsupported access | External error, converted to the applicable access fault |
| Physical topology | SoC/platform; invisible to Core |
| Platform discovery | Read-only root through `mconfigptr`; zero denotes unavailable |
| Section and runtime layout | Deployment image under the software contract |
| Stack/heap sizing | Linker/startup, optionally discovery-informed |
| Trap entry symbol | `__mtvec_base`; baseline Direct mode, Vectored mode delivered with the first interrupt |
| Image format | ELF32 little-endian canonical; binary/hex derivatives allowed |
| UART programming | Startup-shim responsibility blocked on SoC UART/loader ABI |
| Runtime self-modifying code | Out of scope until Zifencei is deliberately implemented |
| Cache/speculation/concurrency/multihart/VM | Explicit baseline non-goals |

## 13. Change Control

Changing a frozen Core/environment mechanism requires revision here. Changing a platform map or device requires a SoC/platform contract update. Changing linker/runtime policy requires a software-contract update. All cross-boundary changes require renewed integration closure.

The governing rule is:

```text
Core freezes execution mechanisms and generic interfaces.
SoC/platform freezes physical hardware and software-visible devices.
The deployment image programs software layout and startup policy.
Generated configuration and tests prove that the selected authorities agree.
```

## Related Documents

- [Core architecture](RV32I_Core_Architecture.md)
- [Software authoring contract](RV32I_Software_Authoring_Contract.md)
- [SoC and platform roadmap](../Roadmap/RV32I_SoC_and_Platform_Roadmap.md)
- [Core design contract](../Implementation/RV32I_Core_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](../Roadmap/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)
- [Memory subsystem contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)
- [LSU contract](../Implementation/Execution/RV32I_LSU_Contract.md)
- [CSR register-bank contract](../Implementation/State/RV32I_CSR_Register_Bank_Design_Contract.md)

## Metadata

- Document type: cross-boundary execution-environment contract
- Core authority: reset behavior, address/protocol boundary, and architectural fault conversion
- Platform authority: future SoC contracts governed by the SoC/platform roadmap
- Software authority: RV32I Software Authoring Contract and selected image artifacts

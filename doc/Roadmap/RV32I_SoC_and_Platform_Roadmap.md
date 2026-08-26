# RV32I SoC and Platform Roadmap

**Scope:** Surrounding-system address map, reset/clock integration, physical memory, MMIO, platform discovery, image transport, and interrupt-producing devices

**Status:** Plan of record; listed facilities require a concrete SoC contract and verification before support is claimed

**Execution environment:** [RV32I Execution-Environment Contract](../Philosophy/RV32I_Execution_Environment_Contract.md)

**Software contract:** [RV32I Software Authoring Contract](../Philosophy/RV32I_Software_Authoring_Contract.md)

**Core roadmap:** [RV32I Exceptions, Traps, and Extensions Roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose and Boundary

This roadmap owns undecided hardware outside `rv32_core`. It does not make a platform feature supported merely by listing it.

The SoC/platform owns:

- the single unified architectural address map;
- RAM, ROM, MMIO, permissions, aliases, and unmapped regions;
- routing of the logical IMEM and DMEM Core interfaces into physical storage and devices;
- clock, reset source, reset sequencing, and executable-memory visibility;
- physical backend timing and transaction-error generation;
- the platform-description structure referenced by `mconfigptr`;
- FPGA image placement, later boot transports, and UART hardware;
- timer and other interrupt-producing devices; and
- any software-visible platform ABI.

Core and LSU remain unaware of physical ranges and peripheral registers. Software consumes a selected platform description but does not define the physical implementation.

## 2. Frozen Integration Mechanisms

Platform work shall preserve these established boundaries:

| Mechanism | Platform obligation |
| --- | --- |
| Core reset | Configure an aligned, fetchable `ResetVector`; `0x0000_0000` is an allowed default, not a portable invariant |
| Address model | One 32-bit architectural byte-address space for instruction fetches and data accesses |
| Core ports | Retain separate logical IMEM and DMEM `rv32_mem_if` paths as a microarchitectural boundary |
| Physical topology | May merge both paths into unified RAM or route them to different backends while preserving one published address space |
| Completion | Return `ready` for every accepted completion and assert `err` with `ready` for unsupported or failed transactions |
| Fault conversion | Let LSU/Core translate external errors into instruction, load, or store access-fault exceptions |
| Reset release | Hold Core/adapters in their reset states until executable memory is visible |
| Latency | Permit immediate or arbitrary delayed completion while request fields remain stable |

Instruction and data permissions may differ within the unified address space. A physical alias or split backend shall not create a second software-visible address universe.

## 3. Required SoC Contract Contents

Each named SoC/platform contract shall define:

- `ResetVector`, clock sources, reset sources, and release sequencing;
- the unified address map, permissions, aliases, and unmapped behavior;
- IMEM/DMEM routing and physical memory topology;
- executable-image initialization or transport;
- every implemented MMIO device and software binding;
- platform-discovery presence or explicit absence;
- interrupt-producing devices and synchronization when present; and
- verification evidence for reset, access, fault, loading, and handoff.

## 4. Roadmap Order

The recommended order is:

1. define a versioned SoC/platform contract and generated configuration schema;
2. close and verify a minimal preload simulation platform;
3. define and expose platform discovery through `mconfigptr`;
4. close one FPGA reset, clock, memory, and first-deployment image path;
5. define UART hardware and startup-shim self-programming;
6. add the machine timer source together with Core Vectored-mode and interrupt integration; and
7. add other devices or external memories only from explicit application requirements.

## 5. Platform Discovery Roadmap

`mconfigptr` is the read-only architectural root for platform discovery. Zero denotes that no discoverable structure is supplied; a nonzero value shall be provided by the platform rather than written by software.

Before discovery support is claimed, the SoC contract shall define:

- the nonzero pointer value and accessible address range;
- structure signature, version, size, and compatibility rules;
- byte order and field widths;
- RAM/ROM ranges and permissions;
- MMIO device identification, ranges, register ABI references, and supported access widths;
- clock/timebase information needed by software;
- optional feature and absence representation;
- whether the structure is immutable, ROM-backed, or constructed at boot; and
- validation and trust rules for startup software.

The CSR implementation, address map, linker/platform headers, startup parser, and directed tests shall change coherently. Whenever `mconfigptr == 0`, software shall use a statically matched platform configuration and treat discovery as unavailable.

## 6. Memory, Reset, and Image Milestones

### Milestone A: Named Simulation Platform

Deliverables:

- one named map for the selected simulation memory;
- explicit permissions and unmapped-error behavior;
- parameter, loader, and linker agreement;
- reset-release ordering; and
- access-fault and delayed-response tests.

### Milestone B: FPGA First Deployment

Deliverables:

- board, part, clock, and reset-source identity;
- Core and adapter reset sequencing;
- physical BRAM, DRAM, ROM, or other storage selection;
- a JTAG/configuration flow that places the first ELF-derived image into executable storage;
- instruction visibility before reset release or handoff; and
- reproducible generated platform/linker configuration.

BRAM initialization may be carried in the FPGA configuration image. External DRAM requires a SoC-defined initialization or JTAG-visible loading path; it shall not be assumed to acquire executable contents from a bitstream without supporting platform logic.

### Milestone C: Boot and UART Programming

Deliverables:

- UART MMIO address and register behavior;
- clock/baud and reset policy;
- image framing, integrity checks, rejection behavior, and destination-range validation;
- protected loader/shim storage and failure recovery;
- instruction-visibility and application-handoff rules; and
- matching startup-shim and end-to-end tests.

A boot ROM, persistent loader, or alternate transport remains optional. Any selected design shall receive its own SoC contract rather than being inferred from the Core interface.

## 7. MMIO and Device Roadmap

Specific MMIO remains deferred until SoC integration. Every implemented device shall define:

- address range and alignment;
- supported access widths;
- register read/write and side-effect behavior;
- reset values;
- ordering requirements;
- error behavior for unsupported accesses; and
- generated software symbols or discovery records.

Unmapped, permission-invalid, or unsupported transactions shall complete with the external memory error indication. They shall not silently read as zero or discard writes.

## 8. Timer and Interrupt Platform Work

The machine timer interrupt is the first planned asynchronous source. SoC work includes:

- timer timebase and clock-domain ownership;
- counter/compare behavior and MMIO representation;
- synchronization of the pending condition into the Core domain;
- hardware ownership of `mip.MTIP`; and
- platform discovery/header exposure.

Core work remains in the exceptions roadmap and includes Vectored-mode `mtvec` support as a project milestone prerequisite, interrupt eligibility, sampling, priority, precise entry, and MRET-based return. This Vectored-mode dependency is a project choice, not an ISA requirement for timer interrupts. Timer support requires both roadmaps to close; completing only the device or only the Core path is insufficient.

Machine software, machine external, or a general interrupt-controller design may be considered only after the timer path and concrete external hardware requirements are established. They are not baseline support commitments.

## 9. Deferred Platform Facilities

| Facility | Required before support is claimed |
| --- | --- |
| Additional FPGA board/profile | Board identity, clocks, reset, storage, pins, and complete top-level configuration |
| Boot ROM or bootloader | Entry, transport, validation, placement, visibility, failure behavior, and handoff |
| UART or console | MMIO ABI, access widths, clock/baud, reset, and error behavior |
| Software-visible completion service | Exact device or call ABI and failure behavior; not part of the production baseline |
| General MMIO set | Complete ranges, semantics, ordering, errors, and software binding |
| Timer | Timebase, compare model, MMIO, synchronization, and pending generation |
| Interrupt integration | Source set, synchronization, eligibility, priority, sampling, and controller behavior |
| DDR or external memory | Map, controller initialization, latency, failure model, and instruction visibility |
| DMA or independent masters | Explicit architectural reconsideration; coherent/cache-visible masters are out of scope |

## 10. Explicit Non-Goals

The baseline platform shall not introduce caches, store buffers, speculation, out-of-order memory execution, multiple harts, parallel Core transactions, coherent/cache-visible independent masters, PMP, MMU, virtual memory, or lower privilege modes. These conflict with the simply explainable Core scope and are not ordinary deferred platform options.

Runtime application self-modifying code is out of scope while Zifencei is absent. Boot-time image programming remains possible only through a platform-controlled visibility and handoff sequence.

## 11. Platform Closure Evidence

A platform is closed only when:

1. its address map, permissions, reset vector, clocks, and reset sequence are published;
2. RTL parameters, routing, and backend behavior match that publication;
3. generated linker/platform inputs match the software image;
4. the loader or initialization path places all image segments correctly;
5. executable memory is visible before reset release or handoff;
6. unsupported accesses return errors and produce the expected architectural faults;
7. every included device has a tested software-visible ABI; and
8. discovery data, when present, matches the actual platform.

## Related Documents

- [Execution-environment contract](../Philosophy/RV32I_Execution_Environment_Contract.md)
- [Software authoring contract](../Philosophy/RV32I_Software_Authoring_Contract.md)
- [Memory subsystem contract](../Implementation/IO/RV32I_Memory_Subsystem_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## Metadata

- Document type: SoC/platform implementation roadmap
- Authority: sequencing and closure criteria for hardware outside `rv32_core`
- Support policy: planned features require an implemented SoC contract and passing integration evidence

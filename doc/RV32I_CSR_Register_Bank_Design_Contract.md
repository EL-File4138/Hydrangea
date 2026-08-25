# RV32I CSR Register Bank Design Contract

**Scope:** Parameterized CSR storage, address dispatch, field semantics, atomic transactions, and the current implemented CSR set

**Status:** Implemented, regression-tested, and frozen for Core integration

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**CSR controller:** [RV32I CSR/SYSTEM Design Contract](RV32I_CSR_SYSTEM_Design_Contract.md)

**Core integration:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

## 1. Purpose

This document freezes the CSR-register architectural and structural decisions for the RV32I FPGA core. It is authoritative for the register-bank topology and supersedes earlier CSR-bank assumptions where they conflict.

The governing principle remains specification compliance with deliberate implementation margin: the current core implements only a small M-mode subset, but the CSR register-bank structure shall not unnecessarily prevent future ratified CSR-related behavior.

---

## 2. Architectural Scope

The current core remains:

- RV32I, M-mode only.
- Zicsr supported.
- Direct-mode trap vector only.
- Machine timer interrupt is the only planned interrupt source for the current thesis scope.
- No S-mode, H-mode, PMP, debug, MMU, cache, or privilege delegation support is required by the current implementation.

The CSR bank shall nevertheless be structured with enough generic transaction capacity to accommodate substantially richer future machine/privileged CSR behavior without redesigning the bank topology.

---

## 3. CSR Transaction Capacity

### 3.1 Read capacity

The CSR bank shall provide a parameterized multi-read interface.

```systemverilog
parameter int unsigned ReadPorts = 4;
```

The default implementation shall therefore provide **4 combinational CSR read ports**.

All read ports observe the same current CSR-bank state. A multi-read operation is therefore an atomic combinational snapshot from the perspective of the consuming extension/control logic.

Zicsr itself requires only one CSR read per instruction. The additional ports are implementation margin for future privileged or extension logic that may need several CSR values concurrently.

### 3.2 Write capacity

The CSR bank shall provide a parameterized multi-write interface.

```systemverilog
parameter int unsigned WritePorts = 8;
```

The default implementation shall therefore provide **8 synchronous write lanes** forming one atomic write transaction.

An ordinary Zicsr write is the degenerate one-lane case. There is no separate single-write path dedicated to Zicsr.

The write-side contract is:

- zero enabled lanes: no CSR state update;
- one enabled lane: ordinary single-CSR write;
- multiple enabled lanes: one atomic compound CSR update;
- all enabled lanes commit on the same rising edge;
- the transaction is all-or-nothing.

A CSR-specific write lane is described by the shared write type, conceptually:

```systemverilog
typedef struct packed {
    logic        en;
    logic [11:0] addr;
    logic [31:0] wdata;
} csr_write_t;
```

### 3.3 Atomic-write validation

Before commitment, every enabled lane shall be semantically dispatched and validated.

The complete atomic transaction is legal only if:

1. every enabled lane resolves to a legal CSR operation; and
2. no two enabled lanes resolve to the same physical CSR cell.

Duplicate physical-cell writes are an interface-contract violation and shall not be resolved by lane priority.

The global write-enable/commit signal is distinct from the per-lane semantic `wr_en` request. Per-lane `wr_en` tells the CSR implementation to evaluate a write operation; the bank-level global write-enable determines whether the already-evaluated atomic transaction is committed.

---

## 4. CSR Bank Structural Model

The CSR register bank is intentionally kept simple. It is not a semantic trap engine and does not centralize all privileged-state behavior.

Its responsibilities are:

- hold physical CSR storage cells;
- provide 4R/8W transaction plumbing;
- dispatch architectural CSR addresses to the appropriate CSR implementation function;
- return read results and operation legality;
- validate atomic multi-write transactions;
- commit legal write transactions synchronously;
- invoke per-CSR reset semantics.

The bank does **not** own the meaning of trap entry, MRET, Zicsr instruction semantics, or future extension-specific architectural events. Those producers construct CSR write requests and present them through the common bank interface.

All CSR writes use the same bank transaction interface, but not all writes must pass through the Zicsr/CSR instruction controller.

Examples:

- Zicsr writes are produced by the CSR instruction controller;
- trap-entry writes may be produced directly by Core trap logic;
- MRET-related `mstatus` updates are produced by the CSR/SYSTEM controller;
- future extension logic may construct its own atomic read/write transactions.

The parent integration logic selects the transaction source presented to the bank.

---

## 5. Physical Storage Organization

The CSR bank shall use dense storage indexed only by implemented CSR cells. It shall **not** instantiate a 4096 × 32 storage array indexed directly by the 12-bit architectural CSR address.

Conceptually:

```systemverilog
typedef enum int unsigned {
    IDX_MSTATUS,
    IDX_MISA,
    IDX_MIE,
    IDX_MTVEC,
    IDX_MSTATUSH,
    IDX_MSCRATCH,
    IDX_MEPC,
    IDX_MCAUSE,
    IDX_MTVAL,
    IDX_MIP,
    IDX_MVENDORID,
    IDX_MARCHID,
    IDX_MIMPID,
    IDX_MHARTID,
    IDX_MCONFIGPTR,
    NUM_CSRS
} csr_idx_t;

logic [31:0] reg_cell [0:NUM_CSRS-1];
```

The architectural address enum and the physical-cell index enum are distinct concepts.

---

## 6. Address Dispatch

The bank shall contain one reusable CSR address-dispatch function.

Its role is to map:

```text
architectural CSR address
    -> implemented CSR semantic function
    -> physical CSR cell index
```

Conceptually:

```systemverilog
function automatic csr_rsp_t csr_dispatch(
    input logic [11:0] addr,
    input csr_req_t    req,
    const ref logic [31:0] reg_cell [0:NUM_CSRS-1]
);
```

Each implemented CSR address dispatches to its dedicated implementation function using the corresponding current physical cell value.

Unimplemented CSR addresses have no dispatch target. The `default` case returns an illegal/invalid CSR response. There is no separate runtime distinction inside the bank between “nonexistent”, “unimplemented”, and “illegal address”; the absence of an implemented dispatch entry is sufficient.

The dispatcher is bank-topology logic and therefore remains with the CSR bank rather than with the per-CSR implementation package.

---

## 7. Per-CSR Semantic Implementation

CSR-specific behavior shall be separated into a dedicated implementation package/file, for example:

```text
rv32_csr_pkg.sv
    common CSR types and enums

rv32_csr_impl_pkg.sv
    csr_mstatus()
    csr_misa()
    csr_mie()
    csr_mtvec()
    csr_mscratch()
    csr_mepc()
    csr_mcause()
    csr_mtval()
    csr_mip()
    identification/configuration CSR functions

rv32_csrreg.sv
    physical storage
    address dispatch
    read/write port handling
    atomic validation
    sequential commit
```

Each CSR implementation function receives only:

- a semantic CSR request; and
- the current physical register value.

It returns:

- whether the requested operation is legal;
- the architectural read value; and
- the candidate next physical state.

Conceptually:

```systemverilog
typedef struct packed {
    logic        legal;
    logic [31:0] rdata;
    logic [31:0] next;
    logic        cell_valid;
    csr_idx_t    cell_idx;
} csr_rsp_t;
```

The per-CSR implementation function does not commit state directly. The parent bank is the sole owner of the `always_ff` storage update.

---

## 8. CSR Request Semantics

The shared request type shall include at least:

```systemverilog
typedef struct packed {
    logic        wr_en;
    logic        rst_en;
    logic [31:0] wdata;
} csr_req_t;
```

The intended meanings are:

- `wr_en`: evaluate this access as a CSR write operation;
- `rst_en`: evaluate the implementation-defined reset behavior for this CSR;
- `wdata`: candidate write data for a normal write operation.

`wr_en` and `rst_en` are mutually exclusive semantic operations.

A pure read uses both deasserted.

The candidate `rsp.next` value does **not** itself imply a state write. It is only the state that would result if the parent bank commits a valid write/reset operation.

Normal state commitment occurs only when the bank-level transaction is enabled and the atomic transaction is legal.

---

## 9. Reset Ownership

Per-CSR reset semantics shall reside with the corresponding CSR implementation function, adjacent to that CSR's read/write semantics.

The bank shall not maintain a separate table of CSR-specific reset values.

During reset, the bank constructs internal requests with:

```systemverilog
req = '0;
req.rst_en = 1'b1;
```

and invokes the same CSR dispatcher for every implemented CSR cell. The resulting `rsp.next` values are synchronously loaded into `reg_cell[]` by the bank's reset branch.

This keeps the parent sequential logic generic while allowing each CSR implementation to define its own architecturally correct reset state.

A separate external reset-enable signal is not required; `rst_en` is an internal member of `csr_req_t` used to select per-CSR reset semantics.

The current reset values are frozen as follows:

| CSR | Reset value |
| --- | ---: |
| `mstatus` | `0x0000_1800` |
| `misa` | `0x4000_0100` |
| `mie`, `mtvec`, `mstatush`, `mscratch`, `mepc`, `mcause`, `mtval`, `mip` | `0x0000_0000` |
| `mvendorid`, `marchid`, `mimpid`, `mhartid`, `mconfigptr` | `0x0000_0000` |

---

## 10. CSR Field Semantic Vocabulary

The CSR common package shall provide a small semantic vocabulary corresponding to specification-required field behavior.

The frozen enum is:

```systemverilog
typedef enum logic [2:0] {
    RW,
    RO,
    WPRI,
    WARL,
    WLRL
} csr_sem_t;
```

The semantic categories are interpreted as follows:

- `RW`: implemented read/write field;
- `RO`: implemented read-only field;
- `WPRI`: writes preserve or ignore a reserved field as required;
- `WARL`: writes are accepted but transformed to an implemented legal value;
- `WLRL`: only legal values are architecturally meaningful, with compliant handling for illegal writes.

This enum is specification vocabulary used by CSR implementation code. It does **not** require a generic metadata interpreter.

Each per-CSR semantic function remains explicit and is responsible for applying the appropriate field semantics.

Implementation-specific details such as whether a field is stored, hardware-driven, reconstructed, aliased, or hardwired are not part of the generic bank abstraction. A fixed field is therefore expressed directly by its CSR function rather than by an additional generic semantic category.

---

## 11. Read/Write Legality Model

There shall be no redundant `exists` or global `write_allowed` property in the bank.

The model is:

```text
address dispatch
    -> no matching implementation: operation illegal
    -> matching implementation: invoke CSR-specific function

CSR-specific function
    -> determines whether the requested read/write operation is legal
    -> returns architectural read value
    -> returns candidate next state
```

For a writable CSR containing RO, WPRI, WARL, WLRL, or implementation-fixed fields, a CSR write is not automatically illegal. The field semantics determine which bits change, remain fixed, are ignored, or are legalized.

A whole-CSR write is rejected only where the architectural CSR operation itself is illegal.

---

## 12. Read Transaction Implementation

Each read port constructs a read request with no write/reset action and invokes the common dispatcher.

All read ports are combinational.

The returned `legal` value indicates whether the addressed CSR read is implemented and architecturally permitted. The returned `rdata` is the architectural CSR value after per-field read semantics have been applied.

The four read ports are independent but observe the same pre-edge CSR state.

---

## 13. Write Transaction Implementation

Each enabled write lane constructs a request using:

```systemverilog
req.wr_en = wr_i[w].en;
req.rst_en = 1'b0;
req.wdata = wr_i[w].wdata;
```

The global bank transaction-enable signal shall **not** be folded into `req.wr_en`; semantic evaluation and transaction commitment are separate concerns.

Each lane is dispatched combinationally. After all lane responses are available, the bank computes whole-transaction legality from:

- per-lane `rsp.legal`; and
- duplicate physical-cell detection.

If the whole transaction is legal and globally enabled, every enabled lane commits its `rsp.next` value to its resolved physical cell on the same rising edge.

---

## 14. Current Required CSR Set

The following CSRs are selected for the current core.

### 14.1 Core trap/interrupt CSRs

| CSR | Address | Current purpose |
|---|---:|---|
| `mstatus` | `0x300` | MIE/MPIE and reduced M-mode trap state |
| `mie` | `0x304` | at least MTIE |
| `mtvec` | `0x305` | Direct mode only |
| `mstatush` | `0x310` | fixed-zero RV32 MRW view |
| `mscratch` | `0x340` | standard M-mode scratch register |
| `mepc` | `0x341` | trap return PC |
| `mcause` | `0x342` | trap cause |
| `mtval` | `0x343` | trap auxiliary value |
| `mip` | `0x344` | at least hardware-owned MTIP |

### 14.2 ISA/configuration CSR

| CSR | Address | Current purpose |
|---|---:|---|
| `misa` | `0x301` | expose RV32 base-ISA implementation; fixed/restricted implementation is acceptable |

### 14.3 Machine identification/configuration CSRs

| CSR | Address | Current implementation |
|---|---:|---|
| `mvendorid` | `0xF11` | hardwired zero initially |
| `marchid` | `0xF12` | hardwired zero initially |
| `mimpid` | `0xF13` | hardwired zero initially |
| `mhartid` | `0xF14` | hardwired zero for single-hart implementation |
| `mconfigptr` | `0xF15` | hardwired zero when no configuration structure is provided |

These low-cost CSRs shall be implemented now because they improve specification-facing completeness with minimal RTL complexity.

---

## 15. CSR Field Decisions for Current Core

### `mstatus`

Current reduced implementation:

- `MIE`: mutable RW state;
- `MPIE`: mutable RW state;
- `MPP`: fixed to Machine mode as `2'b11`;
- unsupported fields: implemented according to their permitted fixed/WPRI/WARL behavior, normally reading as zero where appropriate.

Trap entry performs:

```text
MPIE <- MIE
MIE  <- 0
MPP  <- M
```

MRET performs:

```text
MIE  <- MPIE
MPIE <- 1
PC   <- mepc
```

### `mtvec`

- Direct mode only;
- `MODE[1:0] = 00`;
- BASE is writable subject to the implementation's legal alignment;
- trap target is `{mtvec[31:2], 2'b00}`.

### `mepc`

- writable trap-return PC;
- hardware trap entry writes the current faulting/interrupted instruction PC;
- with `IALIGN=32`, low two bits are constrained to zero.

### `mcause`

- hardware trap entry writes `{interrupt, code}`;
- software-visible and writable according to the selected implementation policy;
- Exception Code field obeys WLRL semantics.

### `mtval`

- hardware trap entry writes `trap.tval`;
- software-visible and writable.

### `mie`

- at minimum, `MTIE` is implemented as mutable state;
- unsupported interrupt-enable fields behave according to their permitted unimplemented semantics.

### `mip`

- `MTIP` is the only selected pending bit;
- software writes are legal no-ops because `MTIP` is hardware-owned and every other field is fixed zero;
- the current reset view is zero; and
- later timer integration may drive or update `MTIP` through a hardware-owned path rather than ordinary software storage.

### `mstatush`

- implemented as an RV32 MRW CSR with a dense physical cell;
- every field reads as zero for the current M-mode-only, little-endian feature set; and
- software writes are legal no-ops.

### `mscratch`

- ordinary XLEN-wide RW storage;
- no special semantic transformation is required.

### `misa`

- expose RV32 and the implemented base ISA as `0x4000_0100`;
- implemented as an MRW/WARL CSR whose supported value is fixed;
- software writes are legal and retain the supported value; and
- unsupported extensions are not advertised.

### Identification/configuration CSRs

The initial implementation shall use specification-permitted fixed values, primarily zero, unless a later thesis/platform requirement assigns meaningful identifiers.

---

## 16. Deferred Counter CSRs

The following standard machine counters are worthwhile but are deferred until Core commit/retirement signaling is stable:

| CSR | Address |
|---|---:|
| `mcycle` | `0xB00` |
| `minstret` | `0xB02` |
| `mcycleh` | `0xB80` |
| `minstreth` | `0xB82` |

These require autonomous state update and, on RV32, split access to 64-bit architectural counters.

`mcountinhibit` should be considered together with the counter implementation rather than implemented in isolation.

---

## 17. Explicit Non-Goals for Current CSR Set

The implementation shall not add CSRs merely to make the address table appear more complete when the associated architectural feature is absent.

In particular, the current M-only core does not require:

- `medeleg` / `mideleg` without lower privilege modes;
- supervisor/hypervisor CSRs;
- PMP CSRs;
- debug CSRs;
- HPM event/counter families beyond the deferred base counters;
- extension-specific CSR families whose corresponding extension is not implemented.

Unimplemented CSR addresses fall through the dispatch default and therefore produce an illegal CSR access.

---

## 18. CSR Controller Boundary

The CSR instruction controller remains responsible for Zicsr and SYSTEM instruction semantics, including:

- CSRRW/CSRRS/CSRRC and immediate forms;
- Zicsr read/write suppression rules;
- SYSTEM decoding behavior delegated from the instruction decoder;
- detecting illegal accesses based on bank responses;
- ECALL/EBREAK/MRET execution semantics as appropriate.

The CSR register bank does not need to understand instruction encodings.

Conversely, the CSR controller is not a mandatory transit point for every CSR write in the machine.

---

## 19. Validation Status

The dedicated CSR register-bank regression at `testbench/cocotb/test-rv32_csrreg.py` passes **6/6** tests. It verifies:

- contract-defined reset values;
- writable-field filtering and address alignment;
- simultaneous commitment of distinct legal write lanes;
- all-or-nothing rejection of illegal or duplicate lanes; and
- illegal unimplemented reads and fixed-value MRW writes.

The bank is frozen except for bug fixes, new CSR implementations, or an explicit contract change.

## 20. Design Invariants

The following invariants are frozen by this contract:

1. The CSR bank uses parameterized **4R/8W** default capacity.
2. Zicsr uses the same generic write transaction mechanism as all other CSR updates.
3. Multi-write updates are atomic and all-or-nothing.
4. Duplicate writes to one physical CSR cell in one atomic transaction are forbidden.
5. All CSR state mutation occurs in the parent bank's sequential logic.
6. Per-CSR implementation functions are pure combinational semantic transforms from `(request, current)` to `response`.
7. Per-CSR reset behavior resides with the per-CSR implementation function and is selected using `csr_req_t.rst_en`.
8. Architectural CSR addresses are dispatched through one reusable `case` function.
9. Physical CSR storage is dense and contains only implemented cells; the 4096-address architectural CSR space is not instantiated as storage.
10. Unimplemented CSR addresses are handled by dispatch fall-through and yield an illegal access.
11. Field semantic vocabulary is kept small and specification-oriented; implementation storage/source details are not generalized into the bank interface.
12. The dispatcher remains part of the bank, while CSR-specific implementation functions reside in a dedicated implementation package/file.

## Related Documents

- [Core architecture](RV32I_Core_Architecture.md)
- [Core implementation](RV32I_Core_Implementation.md)
- [CSR/SYSTEM controller contract](RV32I_CSR_SYSTEM_Design_Contract.md)
- [Instruction decoder contract](RV32I_Instruction_Decoder_Design_Contract.md)
- [Exceptions, traps, and extensions roadmap](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## Metadata

- Document type: module contract
- Authority: CSR register-bank topology, transaction semantics, implemented address set, and per-CSR storage boundary
- RTL authority: `rtl/core/reg/rv32_csrreg.sv`, `rtl/core/type/rv32_csr_pkg.sv`, and `rtl/core/type/rv32_csr_impl_pkg.sv`
- Verification authority: `testbench/cocotb/test-rv32_csrreg.py` and later Core integration tests

# RV32I Core-Owned State Design Contract

**Scope:** Persistent instruction-lifetime, pending-result, trap, and sequencing state owned directly by `rv32_core`

**Status:** Implemented in Core RTL; directed state-lifetime regressions pass

**Governing architecture:** [RV32I Core Architecture](../../Philosophy/RV32I_Core_Architecture.md)

**Core contract:** [RV32I Core Design Contract](../RV32I_Core_Design_Contract.md)

**Register file:** [RV32I Register File Design Contract](RV32I_Register_File_Design_Contract.md)

**CSR bank:** [RV32I CSR Register Bank Design Contract](RV32I_CSR_Register_Bank_Design_Contract.md)

## 1. Ownership Boundary

Core-owned state sequences one in-flight instruction but is not architectural storage owned by the register file, CSR bank, or memory backend.

The implemented persistent set is:

```systemverilog
core_state_e state_q;
logic [31:0] pc_q;
logic [31:0] next_pc_q;
logic [31:0] instruction_q;
logic [31:0] rd_value_q;
rv32_trap_pkg::trap_req_t trap_q;
```

Core does not retain separate decoded semantics, source operands, destination intent, ordinary CSR candidates, or LSU request fields. Those values may remain combinational when they are deterministic functions of state that cannot change before final use.

## 2. Lifetime Rules

`pc_q` and `instruction_q` shall identify the same active instruction from successful fetch capture until normal commit or trap entry supersedes it.

Every non-retained value consumed across states shall remain a deterministic function of invariant retained state. In the current implementation:

- decoder semantics derive from stable `instruction_q`;
- register-file source addresses derive from those stable semantics;
- source values remain stable because no normal GPR write occurs before commit;
- LSU request fields derive from stable semantics, source values, and immediate; and
- ordinary CSR/SYSTEM candidates derive from stable instruction/operand state and current bank responses.

Explicit request or operand registers are optional while these stability properties hold.

`next_pc_q` and `rd_value_q` retain normal values only when entering `ST_COMMIT`. `trap_q` captures the complete accepted report before entering `ST_TRAP` and remains stable through trap-entry qualification.

## 3. State Update Boundaries

| State/boundary | Permitted Core-owned update or architectural authorization |
| --- | --- |
| Reset | Select `ST_FETCH`, initialize `pc_q` from configured `ResetVector`, and clear `trap_q` |
| `ST_FETCH` | Capture a returned instruction or accepted fetch trap |
| `ST_EXECUTE` | Capture pending normal results or an accepted trap |
| `ST_IO_WAIT` | Preserve derived request inputs; capture successful data result or accepted data trap |
| `ST_COMMIT` | Authorize normal PC, GPR, and instruction-directed CSR state updates |
| `ST_TRAP` | Authorize trap-entry CSR state and exceptional PC update |

Uninitialized `instruction_q`, `next_pc_q`, and `rd_value_q` values are invalidated by the FSM after reset. They shall not be consumed until a valid producer transition has written them.

## 4. Separation from Architectural State

The register file owns GPR cells and architectural `x0` preservation. The CSR bank owns CSR cells, legality, and atomic commitment. Core-owned state retains only instruction identity and candidates needed to authorize those state owners at the correct boundary.

Combinational outputs are not persistent state, but they may be consumed in later states when their retained basis remains invariant. Capturing a candidate does not itself constitute architectural commitment.

## 5. Verification

Verification shall demonstrate:

- instruction/PC coherence;
- derived request stability under backpressure;
- valid-before-use behavior after reset;
- single normal commit;
- trap retention and fail-stop behavior on illegal trap entry;
- mutual exclusion of `ST_COMMIT` and `ST_TRAP`; and
- suppression of every normal effect after a qualified trap.

The canonical directed-test results are maintained in [Section 12 of the Core contract](../RV32I_Core_Design_Contract.md#12-verification-status-and-obligations). Current regressions cover ordinary state progression, fail-closed trap retention, and delayed memory completion. Assertions for valid-before-use, commit exclusivity, and retained-basis stability remain open.

## Metadata

- Document type: implemented Core state contract
- RTL authority: `rtl/core/rv32_core.sv`
- Verification authority: Core integration, fail-closed, and backpressure suites listed by the Core design contract, plus future assertions

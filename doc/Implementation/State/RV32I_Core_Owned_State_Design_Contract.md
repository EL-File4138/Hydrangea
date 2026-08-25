# RV32I Core-Owned State Design Contract

**Scope:** Persistent instruction-lifetime, pending-result, trap, and sequencing state owned directly by `rv32_core`

**Status:** Contracted; Core RTL integration pending

**Execution environment:** [RV32I Execution-Environment Contract](../../Philosophy/RV32I_Execution_Environment_Contract.md)

**Governing architecture:** [RV32I Core Architecture](../../Philosophy/RV32I_Core_Architecture.md)

**Register file:** [RV32I Register File Design Contract](RV32I_Register_File_Design_Contract.md)

**CSR bank:** [RV32I CSR Register Bank Design Contract](RV32I_CSR_Register_Bank_Design_Contract.md)

**Core implementation:** [RV32I Core Implementation](../../Roadmap/RV32I_Core_Implementation.md)

## 1. Ownership Boundary

Core-owned state is state required to sequence one in-flight instruction but not owned by the register file, CSR bank, memory backend, or a combinational execution/controller module.

The minimum retained set comprises:

- architectural instruction PC;
- current instruction and decoded semantic record;
- retained source operands and destination/write intent;
- pending normal GPR result and next PC;
- pending CSR write candidate where required;
- retained `trap_req_t` report;
- active memory-request fields while a transaction is outstanding; and
- the Core FSM state.

Concrete register names and packing may differ from the implementation plan, but ownership and lifetime shall remain explicit.

## 2. Instruction-Lifetime Rules

The retained PC and instruction shall identify the same instruction throughout `EXECUTE` and `LSU_WAIT`. Once an instruction or data request is active, every request field shall remain stable until completion.

Core may capture operand values and pending normal results before `COMMIT`, but capture shall not itself constitute architectural commitment. A qualified trap shall invalidate or supersede every pending normal effect from the faulting instruction.

The selected trap report shall be retained before leaving its reporting state and shall remain stable through trap-entry qualification in `TRAP`.

## 3. State Update Boundaries

- Reset shall select `FETCH`, initialize the PC from the configured reset vector, and clear pending normal and trap intent.
- `FETCH` may capture a successfully returned instruction or a fetch trap, but shall not commit a normal instruction result.
- `EXECUTE` may capture operands, normal candidates, an LSU request, or a selected trap report.
- `LSU_WAIT` shall retain the active request and may capture only its successful result or trap completion.
- `COMMIT` is the only normal path that may update the architectural PC, GPR file, or instruction-directed CSR state.
- `TRAP` is the only path that may authorize the selected trap-entry CSR transaction and exceptional PC update.

The architectural PC shall change only on reset, accepted normal commit, or accepted trap entry.

## 4. Separation from Other State Owners

The [register-file contract](RV32I_Register_File_Design_Contract.md) owns GPR cell behavior. The [CSR-bank contract](RV32I_CSR_Register_Bank_Design_Contract.md) owns CSR cells and atomic commitment. Core-owned registers retain only the metadata and candidates needed to authorize those state owners at the correct boundary.

Combinational ALU, CTRL, CSR/SYSTEM, decoder, and trap-controller outputs shall not be treated as persistent state unless Core explicitly captures them.

## 5. Invariants and Verification

Verification shall demonstrate instruction/PC coherence, request stability under backpressure, single normal commit, trap retention, mutual exclusion of `COMMIT` and `TRAP`, suppression of all normal effects after a qualified trap, and reset clearing of pending intent.

Assertions should encode these lifetime and update-boundary properties directly in `rv32_core`.

## Metadata

- Document type: Core state contract
- RTL authority: future integrated `rtl/core/rv32_core.sv`
- Verification authority: future Core state-machine, stability, commit, and trap-integration tests

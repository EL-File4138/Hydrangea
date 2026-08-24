# RV32I Instruction Decoder Design Contract

**Scope:** Instruction-to-semantic-record translation

**Governing architecture:** [RV32I Core Architecture](RV32I_Core_Architecture.md)

**Core integration:** [RV32I Core Implementation](RV32I_Core_Implementation.md)

## 1. Purpose

This document defines the semantic boundary of `rv32_instdec`. RTL and decoder tests are authoritative for accepted instruction encodings, field widths, enum values, and the current packed-record layout. This contract defines field validity, ownership, and downstream interpretation.

The terms **shall**, **shall not**, and **may** denote a requirement, a prohibition, and an implementation choice, respectively.

## 2. Semantic Boundary

The decoder shall translate one stable 32-bit instruction into `inst_sem_t`. It shall identify static decode support, architectural register references and dependencies, a normalized immediate, typed execution operations, execution/result class, and destination-write authorization.

The decoder shall not generate FSM state, PC write timing, register-file enables, operand mux controls, memory requests, result-retention controls, trap entry, or other cycle-specific behavior.

Execution units shall consume semantic operations and operand values supplied by the core. They shall not repeat raw instruction-encoding validation.

## 3. Validity

`legal` means that the decoder accepts the instruction encoding for semantic processing. It does not claim that the integrated core implements the complete execution path, and it does not report dynamic execution faults.

When `legal` is clear, every other semantic field is unspecified and shall not be consumed. A default bit pattern does not acquire semantic meaning in this state.

When `legal` is set, only fields active for that instruction are meaningful. Inactive operation fields shall not be inspected. Typed operation enums do not require invalid members because validity is supplied independently.

## 4. Register References and Dependencies

`rs1` and `rs2` are architectural register indices. `rs1_used` and `rs2_used` qualify true architectural dependencies; the flags shall not be set merely because the encoded bit positions exist.

The core shall perform register-file lookup and route the resulting values to execution units. Register indices shall not cross the execution-unit boundary as operands.

`rd_write` authorizes architectural destination writeback for the instruction class. It shall remain independent of the encoded destination index, including `rd == x0`. Preservation of the architectural zero register belongs to the register-file boundary.

## 5. Immediate

The decoder shall expose a complete 32-bit execution operand rather than an encoded immediate fragment. Reconstruction, extension, placement of implied low bits, and U-type positioning belong on the decoder side of the boundary.

For shift-immediate instructions, the semantic immediate shall contain the unsigned shift amount rather than the complete encoded I-type field. Downstream units shall not reconstruct immediates from the raw instruction.

## 6. Execution and Result Classification

ALU, CTRL, and LSU requests shall use the typed operations defined by `rv32_inst_pkg`. Their numerical encodings and correspondence with ISA fields remain package implementation details.

`wb_src` identifies the semantic execution/result-producing class used by the core for dispatch and result selection. It remains meaningful for a branch or store even though that instruction does not write a GPR. `rd_write`, not `wb_src`, is the sole register-write authorization.

For a legal instruction, the selected execution-unit operation may be trusted as statically valid. Dynamic checks such as address alignment and memory failure remain outside the decoder.

## 7. Combinational Use

The decoder shall remain combinational. The core shall hold the current instruction stable or retain its semantics for as long as downstream execution requires them; a change to core timing shall not introduce decoder-owned instruction state.

Decoder acceptance and integrated-core support are separate milestones. An instruction may be decoded before its execution path is complete, but project support claims shall require both execution behavior and verification.

## 8. Conformance and Change Control

Verification shall test the instruction-to-semantic-record mapping independently of core FSM timing. It shall cover accepted and rejected encodings, active-field values, architectural dependency flags, normalized immediates, execution classification, and write authorization.

This contract requires revision if field validity, dependency meaning, immediate normalization, execution classification, or decoder/core ownership changes. Adding encodings or changing enum values requires updates to RTL and tests but not this contract when the semantic boundary remains unchanged.

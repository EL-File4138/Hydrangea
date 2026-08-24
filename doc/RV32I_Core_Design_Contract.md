# RV32I Core Design Contract

**Scope:** Semantic decode and execution boundary for the baseline RV32I core

**Related planning:** [Controller and Datapath](RV32I_Core_Controller_and_Datapath_Plan.md), [LSU](RV32I_LSU_Implementation_Plan.md), and [Exceptions, Traps, and Extensions](RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## 1. Purpose

This document records cross-module design decisions that cannot be determined reliably from an individual RTL module. It does not duplicate instruction tables, type declarations, signal widths, enum values, module ports, or test cases.

The terms **shall**, **shall not**, and **may** denote a requirement, a prohibition, and an implementation choice, respectively.

## 2. Sources of Authority

The following sources are authoritative within their respective domains:

- The RISC-V Unprivileged ISA specification defines architectural instruction behavior.
- `rv32_inst_pkg` defines the current semantic record, type names, and encoded values.
- `rv32_instdec` and its tests define the instruction encodings accepted by the current implementation and their field-level decode results.
- Each RTL module defines its own ports and cycle-level behavior.
- This contract defines ownership, validity rules, and abstraction boundaries between those modules.

Implementation details intentionally omitted here shall not be inferred from this document.

## 3. Decode Boundary

### 3.1 Semantic interface

The instruction decoder shall translate an instruction into semantic information. It shall not generate cycle-specific controls or prescribe execution sequencing.

The semantic interface shall remain independent of controller state partitioning, memory latency, and datapath resource sharing. Execution units shall consume decoded semantic operations rather than repeat raw instruction-encoding checks.

The main controller shall own core-level sequencing, including instruction fetch, instruction capture, PC update timing, operand selection, intermediate-result retention, memory transaction sequencing, and register writeback timing.

### 3.2 Validity

`legal` means that the instruction encoding is accepted by the implemented decoder for semantic processing. It does not by itself claim that an integrated execution path exists, that every architecturally valid RV32I instruction is decoded, or that execution will complete without a dynamic fault.

When `legal` is clear, every other semantic field is unspecified and shall not be consumed. Default bit patterns do not acquire semantic meaning in this state.

When `legal` is set, only fields required by that instruction are meaningful. Inactive operation fields shall not be inspected. An enum does not require an invalid member when validity is already supplied by `legal` and the field's semantic qualifier.

### 3.3 Architectural dependencies

`rs1_used` and `rs2_used` describe architectural source dependencies. They shall not be set merely because the corresponding bit positions exist in the instruction encoding. Dependency analysis, hazard logic, operand gating, and verification may rely on these flags.

`rd_write` describes whether the instruction class produces a destination-register result. It shall remain independent of the encoded destination index. In particular, selecting `x0` does not change instruction legality or clear `rd_write`.

The register-file or writeback boundary shall preserve the architectural value of `x0`. Whether this is implemented by suppressing writes or by another equivalent mechanism is not constrained here. `rd_write` is the sole authorization for architectural register writeback; `wb_src` shall not cause a write by itself.

### 3.4 Immediate normalization

The decoder shall expose a complete 32-bit execution operand, not an encoded immediate fragment. Reconstruction, extension, placement of architecturally implied bits, and shift-immediate normalization belong on the decoder side of the boundary.

Downstream units shall not reconstruct an immediate from the raw instruction. For shift-immediate operations, the semantic immediate represents the unsigned shift amount rather than the complete encoded I-type field.

## 4. Execution-Unit Boundary

### 4.1 Semantic operations

ALU, load/store, and control-transfer requests shall use typed semantic operations. Numerical encodings and any deliberate correspondence with ISA fields are implementation details owned by `rv32_inst_pkg`.

### 4.2 Operand and result values

`rv32_instdec` emits architectural register indices. The Core Controller, including its datapath, is the sole owner of register-file access: it shall resolve each active source index and route the resulting 32-bit value to the selected execution unit.

ALU, LSU, and CTRL shall consume register contents as raw 32-bit operand values, not as architectural register indices. They shall not read the register file directly or interpret an operand input as a register identifier.

Architectural result ports from these units shall likewise carry raw 32-bit values. Execution units shall not select a destination register or authorize a register write. The controller shall retain `rd`, apply `rd_write`, select the result source, and perform writeback.

This value-only rule applies to architectural operand and result data. It does not prohibit typed operation selectors or protocol, completion, and fault signals required by a unit's function.

### 4.3 Validity and dynamic checks

For a legal instruction, the decoder is the trust boundary for static encoding validity. An execution unit may assume that a selected semantic operation is valid and shall not be required to validate the original instruction encoding.

This rule does not remove responsibility for dynamic checks such as address alignment, access permission, or transaction failure. Such checks belong to the execution or memory-system boundary that has the required runtime information.

## 5. PC and Control-Transfer Semantics

Any operation defined relative to the PC shall use the address of the instruction being executed. It shall not depend on whether the fetch PC has already advanced. The controller shall retain or otherwise provide this instruction PC whenever fetch timing makes the live PC ambiguous.

CTRL shall compute the complete architectural next-PC value for every control-transfer instruction. For a conditional branch, that value shall be the branch target when taken and the executing instruction PC plus four when not taken. The controller shall not apply a second fall-through increment after selecting the CTRL result.

At the architectural next-PC selection point, controller behavior is equivalent to:

```systemverilog
if (is_ctrl)
  pc_d = ctrl_pc;
else
  pc_d = instruction_pc + 32'd4;
```

The identifiers are conceptual. `instruction_pc` denotes the PC of the instruction being executed, and `ctrl_pc` denotes CTRL's complete next-PC result. This rule does not prescribe the cycle in which the PC register is written.

For jump instructions, the control-transfer path has two distinct raw results: the next-PC value and the link value. The next-PC value updates the PC, while the link value is eligible for register writeback. The target shall not be written to `rd`.

`AUIPC` shall use the ALU semantic path, with the controller supplying the current instruction PC and the decoded immediate as operands. `LUI` shall use the normalized immediate directly. These choices define operand provenance without prescribing physical muxes or cycle allocation.

## 6. Memory Boundary

Instruction fetch and load/store execution are separate semantic responsibilities. A later implementation may share a physical memory or bus, but that sharing shall remain below the semantic interface and under controller arbitration.

The LSU shall translate an ISA-level load/store operation into the generic memory operation required by the RAM or external memory interface. The memory implementation shall not distinguish ISA operations that differ only in processor-side behavior, such as load extension policy. The LSU or its memory adapter shall derive the requested lanes and store-data representation; load extraction and extension remain processor-side responsibilities.

The location of effective-address arithmetic is not part of this contract. It may use a shared ALU or LSU-local logic without changing the semantic interface.

## 7. Baseline Execution Model

The baseline core shall execute instructions in order and shall have at most one architectural instruction in progress. It shall issue no speculative memory access and shall have at most one outstanding memory transaction.

This contract does not prescribe the number or names of controller states, operation latency, intermediate registers, physical memory topology, or arithmetic-resource sharing. Those choices shall be defined by the implementing RTL and its protocol documentation.

## 8. Unsupported Instructions and Traps

Decoder acceptance and integrated-core support are separate milestones. An instruction may be decoded before its execution path is complete, but it shall not be advertised as supported by the core until the required execution behavior and verification exist.

Encodings with no implemented semantic decode shall remain rejected rather than being treated as successful no-ops. Adding ordering, environment-call, privileged, or extension instructions requires corresponding execution behavior before the integrated support claim changes; it does not transfer trap, privilege, or memory-ordering policy into the decoder.

The decoder's legality result concerns static decode support only. Trap routing and dynamic exceptions remain outside the decode boundary.

## 9. Conformance and Change Control

Decoder verification shall test the instruction-to-semantic-record mapping independently of controller timing. Integration verification shall check the ownership and validity rules in this contract, especially inactive-field handling, value-only execution-unit operands and results, instruction-PC identity, complete CTRL next-PC selection, writeback authorization, and the decoder-to-execution trust boundary.

This document shall be revised when one of these cross-module decisions changes. Changes limited to supported instruction lists, enum values, field widths, ports, or cycle timing shall be made in their authoritative implementation sources and shall require a contract revision only when they alter an abstraction boundary or invariant stated here.

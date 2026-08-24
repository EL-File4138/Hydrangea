# RV32I CTRL Design Contract

**Scope:** Architectural branch and jump execution

**Governing contract:** [RV32I Core Design Contract](RV32I_Core_Design_Contract.md)

## 1. Purpose

This document defines the semantic boundary between the core controller/datapath and CTRL. The RTL module remains authoritative for port names, widths, and encoded operation values; this contract defines operand ownership and the meaning of CTRL results.

The terms **shall**, **shall not**, and **may** denote a requirement, a prohibition, and an implementation choice, respectively.

## 2. Operand Boundary

`rv32_instdec` emits architectural `rs1` and `rs2` indices. The Core Controller, including its datapath, shall perform register-file lookup and route the resulting register contents to CTRL.

CTRL shall consume 32-bit operand values, not register indices. Its register-sourced inputs therefore represent values such as `operand_a_i` and `operand_b_i`; CTRL shall not access the register file or infer a register identifier from either value.

CTRL shall emit raw 32-bit result values. It shall not receive or emit an architectural destination-register index, select a destination register, or authorize register-file writeback. The controller shall retain the decoded destination index and write authorization and shall route CTRL's register-result value when required.

Typed operation selection is not an architectural data operand and remains part of the CTRL request.

## 3. Instruction-PC Input

The PC supplied to CTRL shall be the address of the instruction currently being executed. It shall remain logically stable while that instruction is evaluated, regardless of instruction-fetch or live-PC timing elsewhere in the core.

All additions in this contract use 32-bit modulo arithmetic.

## 4. Result Semantics

CTRL shall compute the complete architectural next-PC value for every operation it accepts. The controller shall use this result directly for a control-transfer instruction and shall not independently apply a fall-through increment.

### 4.1 Conditional branches

CTRL shall compare the two operand values according to the selected branch operation. Signed branch operations shall use signed 32-bit comparison; unsigned branch operations shall use unsigned 32-bit comparison.

The next-PC result shall be:

```text
condition true  -> pc_i + imm_i
condition false -> pc_i + 4
```

The register-result output is inactive for a conditional branch and shall not be consumed.

### 4.2 `JAL`

CTRL shall produce:

```text
next PC        = pc_i + imm_i
register value = pc_i + 4
```

Register operands are inactive for `JAL`.

### 4.3 `JALR`

CTRL shall produce:

```text
next PC        = (operand_a_i + imm_i) & ~32'h0000_0001
register value = pc_i + 4
```

The mandatory clearing of target bit zero shall be performed explicitly inside CTRL. `operand_b_i` is inactive for `JALR`.

## 5. Controller Integration

For an instruction dispatched to CTRL, CTRL owns both the taken and fall-through next-PC calculations. For an ordinary non-control instruction, the main controller owns sequential progression by four bytes.

The architectural selection is equivalent to:

```systemverilog
if (is_ctrl)
  pc_d = ctrl_pc;
else
  pc_d = instruction_pc + 32'd4;
```

Here, `ctrl_pc` is CTRL's complete next-PC result and `instruction_pc` is the PC associated with the executing instruction. The code is illustrative and does not fix signal names or PC-register timing.

CTRL does not own the PC register, instruction sequencing, destination-register selection, or writeback enable. Its next-PC and register-result outputs are independent raw values; the controller commits each through the appropriate architectural path.

## 6. Validity

CTRL may assume that the decoder and controller provide a valid control-transfer micro-operation and the operands active for that operation. It shall not repeat raw instruction-encoding validation.

Inputs identified as inactive above are unspecified and shall not affect active results. The register-result output for an operation without register writeback is likewise unspecified and shall not be consumed.

## 7. Conformance

Verification shall cover:

- taken and not-taken outcomes for every implemented conditional branch operation;
- signed and unsigned comparison boundary values;
- positive, negative, and wrapping PC-relative targets;
- `JAL` target and link generation;
- `JALR` target and link generation, including explicit bit-zero clearing;
- independence from inactive operands; and
- controller integration in which CTRL supplies conditional-branch fall-through while the controller supplies ordinary non-control progression.

Changes to numerical operation encodings or port names belong to RTL and tests. This contract requires revision only if operand ownership, PC identity, result meaning, or controller/CTRL responsibility changes.

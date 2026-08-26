# RV32I Instruction Decoder Design Contract

## Purpose

This document defines the semantic boundary of the RV32I instruction decoder. RTL packages are authoritative for encoded type values and field widths. This contract defines encoding-trap ownership, operand dependencies, immediate meaning, execution classification, and the division between structural decode and specialist-unit policy.

## 1. Semantic Boundary

The decoder shall translate the retained 32-bit instruction into one typed semantic record and one architectural trap candidate. Downstream logic shall consume those outputs rather than independently reconstructing opcode, `funct3`, or `funct7` meaning.

The semantic record shall identify at least:

- ALU operation;
- register-source usage;
- destination-register write intent;
- writeback-source class;
- normal PC-source class;
- a normalized immediate;
- CSR or SYSTEM operation class; and
- the five-bit CSR immediate source.

The shared record shall therefore include fields equivalent to:

```systemverilog
csr_op_e          csr_op;
logic [4:0]       csr_uimm;
pc_source_e       pc_source;
```

`inst_semantics_t` shall not contain a semantic `legal` or `valid` field. The decoder shall instead expose `inst_trap_o`, serving the decoder `trap_o` role, with type `rv32_trap_pkg::trap_req_t`.

The decoder shall not read the register file, access memory, update architectural state, or select a trap vector.

## 2. Encoding Trap Reporting

For a normally decoded instruction, `inst_trap_o.is_valid` shall be clear and the semantic record shall carry the instruction's valid execution meaning.

For an illegal or unsupported encoding, the decoder shall report:

```text
inst_trap_o.is_valid     = 1
inst_trap_o.is_interrupt = 0
inst_trap_o.code      = EXC_ILLEGAL_INST
inst_trap_o.tval      = inst_i
```

The decoder shall assign benign defaults to every semantic field on all combinational paths. The core shall ignore the complete semantic record whenever `inst_trap_o.is_valid` is set.

The decoder owns illegal conditions fully determined by instruction bits, including unsupported major opcodes, reserved `funct3` or `funct7` combinations, unsupported extension encodings, reserved SYSTEM `funct3` values, unsupported FENCE.I encodings, and other structurally illegal forms.

The decoder shall not determine legality that depends on specialist-unit state or implementation resources. CSR implementation, write permission, privilege permission, exact `CSR_SYS` interpretation, memory alignment, memory-access failure, and control-target alignment belong to their respective units.

For the SYSTEM major opcode with `funct3 == 3'b000`, the decoder shall emit `csr_op = CSR_SYS` without resolving the exact SYSTEM operation. A structurally valid SYSTEM dispatch may therefore produce a CSR/SYSTEM trap during execution.

## 3. Register Dependencies and Write Intent

Source usage flags shall represent true register-file dependencies:

- register-register ALU operations use `rs1` and `rs2`;
- immediate ALU operations use `rs1` only;
- loads use `rs1` only;
- stores use `rs1` for the base and `rs2` for store data;
- conditional branches use both sources;
- JAL uses neither source;
- JALR uses `rs1` only;
- LUI and AUIPC use neither source;
- register-source CSR operations use `rs1`;
- immediate-source CSR operations use no register source; and
- SYSTEM and FENCE operations use no register source.

Destination-register write intent shall be asserted for ALU, upper-immediate, jump-and-link, load, and CSR read-result forms. It shall be clear for stores, conditional branches, SYSTEM operations, FENCE, and benign semantic defaults accompanying a decoder trap. Architectural suppression of writes to `x0` remains a core commit responsibility.

## 4. Immediate Semantics

The decoder shall emit one normalized 32-bit immediate:

- I-type immediates are sign-extended;
- S-type immediates are sign-extended;
- B-type immediates are sign-extended and include the implicit low zero;
- U-type immediates occupy bits 31:12 and have twelve low zeros;
- J-type immediates are sign-extended and include the implicit low zero; and
- shift-immediate operations use the zero-extended five-bit shift amount.

For CSR and SYSTEM encodings, `sem.imm[11:0]` shall preserve the instruction's 12-bit CSR or SYSTEM immediate field. No separate CSR-address field shall be added. The dedicated CSR immediate source shall preserve `inst[19:15]`, equivalently `rs1[4:0]`, for immediate CSR forms and shall be zero for non-immediate forms.

The decoder shall not add the PC, a register value, or an architectural base address to an immediate.

## 5. ALU Classification

The ALU operation field shall distinguish the supported arithmetic, logical, comparison, and shift operations. The decoder shall report invalid arithmetic `funct3` and `funct7` combinations rather than mapping them to a nearby supported operation.

The ALU operation may be inactive for instruction classes that do not consume an ALU result.

## 6. Memory Classification

Supported memory semantics are:

| Instruction class | Width | Signed load | Register dependencies | Destination write |
| --- | --- | --- | --- | --- |
| LB | byte | yes | `rs1` | yes |
| LH | halfword | yes | `rs1` | yes |
| LW | word | not applicable | `rs1` | yes |
| LBU | byte | no | `rs1` | yes |
| LHU | halfword | no | `rs1` | yes |
| SB | byte | not applicable | `rs1`, `rs2` | no |
| SH | halfword | not applicable | `rs1`, `rs2` | no |
| SW | word | not applicable | `rs1`, `rs2` | no |

Unsupported load or store `funct3` values shall produce a decoder trap. The decoder defines the operation semantics but shall not calculate the effective address, generate byte strobes, perform alignment checks, or authorize writeback.

## 7. Control-Transfer Classification

The decoder shall distinguish conditional branch, JAL, and JALR semantics. It shall report invalid branch `funct3` values and invalid JALR encodings.

The decoder emits branch or jump intent, the normalized displacement, and the control-transfer PC-source class. It shall not compare operands, calculate the target or link value, clear the JALR target low bit, validate target alignment, or update the PC.

## 8. CSR and SYSTEM Classification

The SYSTEM major opcode shall map `funct3` as follows:

| `funct3` | Semantic operation | Source form |
| --- | --- | --- |
| `000` | `CSR_SYS` | SYSTEM immediate |
| `001` | `CSR_RW` | register |
| `010` | `CSR_RS` | register |
| `011` | `CSR_RC` | register |
| `100` | Decoder illegal-instruction trap | none |
| `101` | `CSR_RWI` | five-bit immediate |
| `110` | `CSR_RSI` | five-bit immediate |
| `111` | `CSR_RCI` | five-bit immediate |

Structurally valid register and immediate CSR forms shall select CSR writeback, assert destination-register write intent, and select the sequential normal-PC source. The SYSTEM form shall select CSR writeback and the CSR/SYSTEM normal-PC source without destination-register write intent.

The [CSR/SYSTEM controller contract](../Execution/RV32I_CSR_SYSTEM_Design_Contract.md#6-exact-system-interpretation) owns the exact ECALL, EBREAK, WFI, MRET, malformed-encoding, and zero-register rules. The main decoder shall preserve the SYSTEM immediate and required register fields without duplicating that policy.

## 9. FENCE Classification

Every MISC-MEM encoding with `funct3 = 000` shall be accepted as base FENCE, regardless of `rs1`, `rd`, `fm`, predecessor, or successor fields. This includes FENCE.TSO and PAUSE encodings. In this implementation FENCE is a serialization no-op: it uses no register source, writes no destination register, issues no LSU transaction, and selects `pc + 4` through the normal sequential path.

Because FENCE has no architectural writeback value, its writeback-source field is not consumed. The implementation shall assign it a non-memory completion class so that it cannot be dispatched to the LSU.

FENCE.I and other unsupported MISC-MEM encodings shall produce a decoder illegal-instruction trap.

## 10. Result and PC Classification

The writeback-source field shall classify the producer of a normal destination-register value. Supported classes include immediate, ALU, control-transfer link, memory load, and CSR read result.

The normal PC-source field is independent of writeback selection. It shall distinguish:

- sequential `pc + 4`;
- the control-transfer unit result; and
- the CSR/SYSTEM controller result.

Ordinary non-control, non-SYSTEM instructions shall select the sequential source. Branches, JAL, and JALR shall select the control-transfer source. Only the structural SYSTEM form shall select the CSR/SYSTEM source at decode time.

Trap entry is an exceptional override selected by the core and shall not be encoded as a normal decoder PC source.

## 11. Conformance

Decoder verification shall show that:

- every supported RV32I encoding produces the required semantic record with no decoder trap;
- every unsupported or reserved encoding owned by the decoder reports `EXC_ILLEGAL_INST` with the raw instruction in `tval`;
- semantic defaults are benign and ignored whenever the decoder trap is valid;
- no semantic legality or validity boolean is required by the core;
- source-usage and destination-write flags match true dependencies;
- immediates, CSR addresses, and CSR immediate sources are reconstructed correctly;
- CSR and SYSTEM forms receive the required operation, writeback, and PC classifications;
- all base-FENCE encodings are legal and side-effect free while FENCE.I remains unsupported;
- writeback and normal PC selection remain independent; and
- exact SYSTEM, CSR-access, memory, and control-target legality is not duplicated in the decoder.

## Module Contracts

- [Core architecture](../../Philosophy/RV32I_Core_Architecture.md)
- [Core design contract](../RV32I_Core_Design_Contract.md)
- [ALU contract](../Execution/RV32I_ALU_Design_Contract.md)
- [CTRL unit contract](../Execution/RV32I_CTRL_Design_Contract.md)
- [LSU contract](../Execution/RV32I_LSU_Contract.md)
- [CSR/SYSTEM controller contract](../Execution/RV32I_CSR_SYSTEM_Design_Contract.md)
- [Memory subsystem contract](../IO/RV32I_Memory_Subsystem_Design_Contract.md)

## Metadata

- Document type: module contract
- Authority: semantic interpretation of `rv32_inst_decoder`
- RTL authority: `rtl/core/ctrl/rv32_inst_decoder.sv`, `rtl/core/type/rv32_inst_pkg.sv`
- Verification authority: decoder unit tests and core integration tests

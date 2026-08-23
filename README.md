# Hydrangea / アジサイ

An ongoing implementation of a simply explainable, specification-compliant, research/educational RISC-V IP core targeting bare-metal RV32I systems. The project favors explicit interfaces, inspectable control flow, and verification-friendly RTL over microarchitectural complexity.

## Status

This is a work in progress, not a complete processor or FPGA-ready system. The repository currently provides independently tested implementation blocks for instruction decode, immediate generation, ALU operations, register-file behavior, synchronous RAM, and controller development. An integrated instruction-fetch, execution, load/store, trap, and board-level system is still under construction.

Do not use this repository as a conformance-proven CPU core or in safety-, security-, or mission-critical hardware.

## Scope

- Base ISA:          RV32I
- Target Deployment: FPGA Bare-metal
- Extensions:        Zicsr, optionally Zifencei
- Privilege:         M-mode only
- Endianness:        Little-endian
- Instruction width: 32-bit only; IALIGN=32
- Misaligned access: Trap; never emulate in hardware
- Trap vector:       Direct mode only
- Interrupts:        Machine timer interrupt only
- Memory system:     No caches, MMU, coherency, or speculation
- Execution:         In-order, one instruction in flight
- External bus:      Separate instruction/data ready-valid interfaces
- Outstanding ops:   At most one on each interface
- RTL:               Synthesizable SystemVerilog.
- Verification:      Cocotb regression tests, Verible linting, and a planned SymbiYosys formal flow.

The RISC-V ISA specification remains the architectural authority. Project-specific ownership and interface decisions are documented in [`doc/RV32I_Core_Design_Contract.md`](doc/RV32I_Core_Design_Contract.md).

## Repository Layout

| Path | Purpose |
| --- | --- |
| `rtl/core/` | Core type definitions and ALU, control, decode, and register-file RTL. |
| `rtl/mem/` | Memory implementation blocks. |
| `rtl/files.f` | Authoritative root-relative manifest of RTL sources. |
| `testbench/cocotb/` | Self-checking Cocotb tests for implemented modules. |
| `formal_verification/` | SymbiYosys jobs as formal properties are added. |
| `constraints/` | FPGA constraint files. |
| `scripts/` | Manifest, firmware-image, and FPGA-flow support scripts. |
| `doc/` | Design contract, implementation plans, and extension roadmap. |

## Prerequisites

Activate an EDA environment that provides the tools used by the Makefile:

- Python 3 and Cocotb
- Verilator
- Verible
- Yosys and SymbiYosys for formal jobs
- A RISC-V bare-metal GCC toolchain for firmware targets
- Vivado for Xilinx synthesis and bitstream targets (Optional, only for FPGA deployment and testing)

The environment activation mechanism is intentionally outside this repository. Confirm the currently required development tools with:

```bash
make check-tools
```

## Development Workflow

```bash
make check-files                     # Verify rtl/files.f matches rtl/**/*.sv
# make update-files                  # If not, update it to rtl/**/*.sv
make lint                            # Run the lowRISC-style Verible profile
make test TOP=rv32_alu               # Run one module's Cocotb regression
make sim TOP=rv32_alu                # Run the test and write an FST waveform
make formal                          # Run all formal_verification/*.sby jobs
make firmware                        # Build bare-metal ELF, BIN, HEX, and disassembly
make clean                           # Remove generated output
```

Use `make help` for all supported targets and configurable variables. Simulation test modules default to `testbench/cocotb/test-<module>.py`; set `COCOTB_TEST_MODULE` only when that naming does not apply.

## Contributing RTL

This project is a personal undertaking and is likely not accepting any contribution. However, if you are still interested:

1. Add one documented, synthesizable SystemVerilog module under the relevant `rtl/` directory.
2. Run `make update-files` to regenerate `rtl/files.f`.
3. Add or update a self-checking test under `testbench/cocotb/`.
4. Run `make check-files`, `make lint`, and the relevant `make test TOP=<module>` command in the activated EDA environment.
5. Add a formal job for control, protocol, or safety properties where exhaustive proof is practical.

The repository configures Git to use `.githooks/`. The pre-commit hook checks that the checked-in RTL manifest is current and run the validation commands above before committing to ensure basic syntax confrontance.

## RTL Conventions

RTL follows the [lowRISC Verilog Coding Style Guide](https://github.com/lowRISC/style-guides/blob/master/VerilogCodingStyle.md). Use SystemVerilog constructs such as `logic`, `always_comb`, and `always_ff`; lower-snake-case identifiers; typed UpperCamelCase parameters; `_i` and `_o` port suffixes; and `_q`/`_d` state naming. RTL modules use explicit widths, named port connections, and `` `default_nettype none``.

## Documentation

- [Core design contract](doc/RV32I_Core_Design_Contract.md)
- [Controller and datapath plan](doc/RV32I_Core_Controller_and_Datapath_Plan.md)
- [Load/store implementation plan](doc/RV32I_LSU_Implementation_Plan.md)
- [Exceptions, traps, and extensions roadmap](doc/RV32I_Exceptions_Traps_and_Extensions_Roadmap.md)

## License

This project is a partial dependency of the ongoing thesis project of author. It may or may not fall under the University's policy regarding intellectual contribution for work conducted under University's regulation, depending on final inclusion.
Please do not assume permission to reuse, distribute, or modify the source until a explicit license announcement is made.

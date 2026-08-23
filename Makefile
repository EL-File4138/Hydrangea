# ==============================================================================
# RISC-V RV32I Core Implementation
#
# Intended repository layout:
#
# .
# ├── Makefile
# ├── rtl/
# │   ├── top.sv
# │   └── ...
# ├── tb/
# │   └── cocotb/
# │       └── test_top.py
# ├── formal/
# │   ├── top.sby
# │   └── ...
# ├── sw/
# │   ├── start.S
# │   ├── main.c
# │   └── link.ld
# ├── constraints/
# │   └── board.xdc
# └── build/
#
# Main workflow:
#
#   make lint
#   make test
#   make formal
#   make firmware
#   make synth
#   make bitstream
#
# Most configuration variables may be overridden on the command line:
#
#   make test TOP=alu32
#   make firmware MARCH=rv32i
#   make synth PART=xc7a100tfgg484-2
#
# ==============================================================================


# ------------------------------------------------------------------------------
# Project configuration
# ------------------------------------------------------------------------------

PROJECT     ?= riscv-preplan
# Select a DUT explicitly for simulation, synthesis, or bitstream targets.
TOP         ?=

RTL_DIR     ?= rtl
TB_DIR      ?= testbench
FORMAL_DIR  ?= formal_verification
SW_DIR      ?= simulation_wave
CONSTR_DIR  ?= constraints
BUILD_DIR   ?= build

SIM_BUILD   := $(BUILD_DIR)/sim
SW_BUILD    := $(BUILD_DIR)/simulation_wave
SYNTH_BUILD := $(BUILD_DIR)/synth
FORMAL_BUILD:= $(BUILD_DIR)/formal_verification
WAVE_FILE   ?= $(abspath $(SW_DIR)/$(TOP).fst)
SURFER      ?= surfer


# ------------------------------------------------------------------------------
# RTL source manifest
#
# Keep source ordering and inclusion explicit. Each line in RTL_FILELIST is
# relative to the repository root so it also works with HDL tools' -f option.
# ------------------------------------------------------------------------------

RTL_FILELIST ?= $(RTL_DIR)/files.f
RTL_SRCS := $(shell sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$$/d' $(RTL_FILELIST))


# ------------------------------------------------------------------------------
# Tool configuration inherited from the activated EDA environment.
# ------------------------------------------------------------------------------

VERILATOR   ?= verilator
VERIBLE     ?= verible-verilog-lint
SBY         ?= sby
YOSYS       ?= yosys
VIVADO      ?= vivado

PYTHON      ?= python3
COCOTB_CONFIG ?= cocotb-config
UPDATE_FILES_SCRIPT ?= scripts/update_files_f.py

# The full Verible ruleset enforces the lowRISC SystemVerilog style guide's
# naming, port, register, and formatting conventions.
VERIBLE_LINT_FLAGS ?= --ruleset=all --rules=-instance-shadowing
VERIBLE_SUPPRESSED_LINT_MESSAGE := Should be a simple reference, ending with a valid suffix:


# ------------------------------------------------------------------------------
# RISC-V toolchain
# ------------------------------------------------------------------------------

RISCV_PREFIX ?= riscv64-unknown-elf-

CC      := $(RISCV_PREFIX)gcc
AS      := $(RISCV_PREFIX)gcc
LD      := $(RISCV_PREFIX)gcc
OBJCOPY := $(RISCV_PREFIX)objcopy
OBJDUMP := $(RISCV_PREFIX)objdump
READELF := $(RISCV_PREFIX)readelf
NM      := $(RISCV_PREFIX)nm

MARCH ?= rv32i
MABI  ?= ilp32

ARCH_FLAGS := \
	-march=$(MARCH) \
	-mabi=$(MABI)

CFLAGS := \
	$(ARCH_FLAGS) \
	-ffreestanding \
	-fno-builtin \
	-fno-stack-protector \
	-fno-pic \
	-fno-pie \
	-ffunction-sections \
	-fdata-sections \
	-Wall \
	-Wextra \
	-Werror \
	-Os

ASFLAGS := \
	$(ARCH_FLAGS) \
	-ffreestanding

LDFLAGS := \
	$(ARCH_FLAGS) \
	-nostdlib \
	-nostartfiles \
	-static \
	-Wl,--gc-sections \
	-Wl,-T,$(SW_DIR)/link.ld


# ------------------------------------------------------------------------------
# Simulation configuration
# ------------------------------------------------------------------------------

SIM ?= verilator

COCOTB_TEST_MODULE ?= test-$(TOP)

VERILATOR_FLAGS ?= \
	-I$(RTL_DIR) \
	-I$(TB_DIR) \
	--Wall \
	--Wno-fatal \
	--trace \
	--timing

# ------------------------------------------------------------------------------
# FPGA configuration
#
# Default below matches an XC7A100T-2FGG484-class target.
# Override if the exact device differs.
# ------------------------------------------------------------------------------

PART ?= xc7a100tfgg484-2
XDC  ?= $(CONSTR_DIR)/board.xdc

CLOCK_PERIOD_NS ?= 20.000


# ------------------------------------------------------------------------------
# User-facing targets
# ------------------------------------------------------------------------------

.PHONY: all
all: lint

.PHONY: help
help:
	@printf '%s\n' \
		'' \
		'RISC-V RTL development targets:' \
		'' \
		'  make help         Show this help text' \
		'  make all          Run the default workflow (lint)' \
		'  make lint         Run lowRISC-style Verible RTL lint' \
		'  make lint-strict  Run fatal lowRISC-style Verible RTL lint' \
		'  make test TOP=<module>  Run the selected module Cocotb test' \
		'  make sim TOP=<module>   Run the selected module test with a waveform' \
		'  make wave         Open the latest FST waveform in Surfer' \
		'  make formal       Run SymbiYosys formal jobs' \
		'  make formal-smoke Run smoke formal job' \
		'  make update-files Refresh rtl/files.f from rtl/**/*.sv' \
		'  make check-files  Check whether rtl/files.f is up to date' \
		'  make firmware     Build ELF, BIN, HEX and disassembly' \
		'  make disasm       Print firmware disassembly' \
		'  make elf-info     Print ELF headers/sections/symbols' \
		'  make synth        Run Vivado synthesis' \
		'  make bitstream    Run synthesis + implementation + bitstream' \
		'  make check-tools  Check required toolchain executables' \
		'  make check-vivado Check Vivado availability/version' \
		'  make clean        Remove generated build products' \
		'  make distclean    Remove all generated state' \
		'' \
		'Default variables:' \
		'' \
		'  TOP=$(TOP)' \
		'  SIM=$(SIM)' \
		'  MARCH=$(MARCH)' \
		'  MABI=$(MABI)' \
		'  PART=$(PART)' \
		'  XDC=$(XDC)' \
		''


# ==============================================================================
# Directory creation
# ==============================================================================

$(BUILD_DIR):
	mkdir -p $@

$(SIM_BUILD):
	mkdir -p $@

$(SW_BUILD):
	mkdir -p $@

$(SYNTH_BUILD):
	mkdir -p $@

$(FORMAL_BUILD):
	mkdir -p $@


# ==============================================================================
# Manifest maintenance
# ==============================================================================

.PHONY: update-files
update-files:
	$(PYTHON) $(UPDATE_FILES_SCRIPT)

.PHONY: check-files
check-files:
	$(PYTHON) $(UPDATE_FILES_SCRIPT) --check


# ==============================================================================
# Lint
# ==============================================================================

.PHONY: lint
lint:
	@output=$$(mktemp); \
	$(VERIBLE) $(VERIBLE_LINT_FLAGS) $(RTL_SRCS) >$$output 2>&1; status=$$?; \
	grep -F -v '$(VERIBLE_SUPPRESSED_LINT_MESSAGE)' $$output || true; \
	if [ $$status -ne 0 ] && grep -F -q -v '$(VERIBLE_SUPPRESSED_LINT_MESSAGE)' $$output; then \
		rm -f $$output; exit $$status; \
	fi; \
	rm -f $$output


# Optional stricter target.
#
# Once the codebase stabilizes, this is the target that should ideally pass.
#
.PHONY: lint-strict
lint-strict:
	@output=$$(mktemp); \
	$(VERIBLE) $(VERIBLE_LINT_FLAGS) --lint_fatal $(RTL_SRCS) >$$output 2>&1; status=$$?; \
	grep -F -v '$(VERIBLE_SUPPRESSED_LINT_MESSAGE)' $$output || true; \
	if [ $$status -ne 0 ] && grep -F -q -v '$(VERIBLE_SUPPRESSED_LINT_MESSAGE)' $$output; then \
		rm -f $$output; exit $$status; \
	fi; \
	rm -f $$output


# ==============================================================================
# Simulation
#
# Tests are per-DUT Cocotb modules under testbench/cocotb/.
# For TOP=rv32_alu, the default test module is test-rv32_alu.
#
# Usage:
#
#   make test TOP=rv32_alu
#   make sim TOP=rv32_alu
#   make test TOP=rv32_alu COCOTB_TEST_MODULE=test-rv32_alu
#
# ==============================================================================

COCOTB_BUILD_TARGET ?= sim_build/Vtop

.PHONY: cocotb-build
cocotb-build: $(SIM_BUILD)
	$(MAKE) \
		-C $(SIM_BUILD) \
		-f $(CURDIR)/Makefile.cocotb \
		$(COCOTB_BUILD_TARGET) \
		SIM=$(SIM) \
		TOP=$(TOP) \
		RTL_SRCS="$(addprefix $(CURDIR)/,$(RTL_SRCS))" \
		TB_DIR="$(CURDIR)/$(TB_DIR)" \
		VERILATOR_FLAGS="$(VERILATOR_FLAGS)" \
		COCOTB_TEST_MODULE=$(COCOTB_TEST_MODULE)

.PHONY: test test/cocotb
test: test/cocotb

test/cocotb: cocotb-build
	$(MAKE) \
		-C $(SIM_BUILD) \
		-f $(CURDIR)/Makefile.cocotb \
		SIM=$(SIM) \
		TOP=$(TOP) \
		RTL_SRCS="$(addprefix $(CURDIR)/,$(RTL_SRCS))" \
		TB_DIR="$(CURDIR)/$(TB_DIR)" \
		VERILATOR_FLAGS="$(VERILATOR_FLAGS)" \
		COCOTB_TEST_MODULE=$(COCOTB_TEST_MODULE)

.PHONY: sim sim/cocotb
sim: sim/cocotb

sim/cocotb: cocotb-build
	@set -e; \
	mkdir -p "$(SW_DIR)"; \
	$(MAKE) \
		-C $(SIM_BUILD) \
		-f $(CURDIR)/Makefile.cocotb \
		SIM=$(SIM) \
		TOP=$(TOP) \
		RTL_SRCS="$(addprefix $(CURDIR)/,$(RTL_SRCS))" \
		TB_DIR="$(CURDIR)/$(TB_DIR)" \
		VERILATOR_FLAGS="$(VERILATOR_FLAGS)" \
		COCOTB_TEST_MODULE=$(COCOTB_TEST_MODULE) \
		COMPILE_ARGS="$(if $(strip $(COMPILE_ARGS)),$(strip $(COMPILE_ARGS)) )--trace-fst --trace-structs" \
		SIM_ARGS="$(if $(strip $(SIM_ARGS)),$(strip $(SIM_ARGS)) )--trace --trace-file $(WAVE_FILE)"; \
	nohup $(SURFER) "$(WAVE_FILE)" >/dev/null 2>&1 &

.PHONY: wave
wave:
	@set -e; \
	wave_file="$$(ls -t "$(SW_DIR)"/*.fst 2>/dev/null | head -n 1)"; \
	if [ -z "$$wave_file" ]; then \
		echo "No FST waveform found in $(SW_DIR)/"; \
		exit 1; \
	fi; \
	nohup $(SURFER) "$$wave_file" >/dev/null 2>&1 &


# ==============================================================================
# Formal verification
#
# Each .sby file is treated as an independent formal job.
#
# Examples:
#
#   formal/protocol.sby
#   formal/regfile.sby
#   formal/core_smoke.sby
#
# ==============================================================================

SBY_FILES := $(sort $(wildcard $(FORMAL_DIR)/*.sby))

.PHONY: formal
formal: | $(FORMAL_BUILD)
	@if [ -z "$(SBY_FILES)" ]; then \
		echo "No .sby files found under $(FORMAL_DIR)/"; \
		exit 1; \
	fi
	@set -e; \
	for f in $(SBY_FILES); do \
		echo "==> Formal: $$f"; \
		$(SBY) --prefix "$(FORMAL_BUILD)/$$(basename "$$f" .sby)" -f "$$f"; \
	done


# Fast subset for routine development.
#
.PHONY: formal-smoke
formal-smoke: | $(FORMAL_BUILD)
	@if [ ! -f "$(FORMAL_DIR)/smoke.sby" ]; then \
		echo "Missing $(FORMAL_DIR)/smoke.sby"; \
		exit 1; \
	fi
	$(SBY) --prefix "$(FORMAL_BUILD)/smoke" -f $(FORMAL_DIR)/smoke.sby


# ==============================================================================
# Firmware
# ==============================================================================

SW_C_SRCS := $(sort $(wildcard $(SW_DIR)/*.c))
SW_S_SRCS := $(sort $(wildcard $(SW_DIR)/*.S))

SW_C_OBJS := \
	$(patsubst $(SW_DIR)/%.c,$(SW_BUILD)/%.o,$(SW_C_SRCS))

SW_S_OBJS := \
	$(patsubst $(SW_DIR)/%.S,$(SW_BUILD)/%.o,$(SW_S_SRCS))

SW_OBJS := $(SW_S_OBJS) $(SW_C_OBJS)

ELF := $(SW_BUILD)/firmware.elf
BIN := $(SW_BUILD)/firmware.bin
HEX := $(SW_BUILD)/firmware.hex
DIS := $(SW_BUILD)/firmware.dis
MAP := $(SW_BUILD)/firmware.map


$(SW_BUILD)/%.o: $(SW_DIR)/%.c | $(SW_BUILD)
	$(CC) $(CFLAGS) -c $< -o $@


$(SW_BUILD)/%.o: $(SW_DIR)/%.S | $(SW_BUILD)
	$(AS) $(ASFLAGS) -c $< -o $@


$(ELF): $(SW_OBJS) $(SW_DIR)/link.ld | $(SW_BUILD)
	$(LD) \
		$(LDFLAGS) \
		-Wl,-Map,$(MAP) \
		$(SW_OBJS) \
		-o $@


$(BIN): $(ELF)
	$(OBJCOPY) -O binary $< $@


$(HEX): $(BIN)
	$(PYTHON) scripts/bin2hex.py $< $@


$(DIS): $(ELF)
	$(OBJDUMP) \
		-d \
		-M no-aliases,numeric \
		$< > $@


.PHONY: firmware
firmware: $(ELF) $(BIN) $(HEX) $(DIS)
	@echo
	@echo "Firmware:"
	@echo "  ELF:  $(ELF)"
	@echo "  BIN:  $(BIN)"
	@echo "  HEX:  $(HEX)"
	@echo "  DIS:  $(DIS)"
	@echo "  MAP:  $(MAP)"


.PHONY: disasm
disasm: $(DIS)
	cat $(DIS)


.PHONY: elf-info
elf-info: $(ELF)
	$(READELF) -h -S -s $(ELF)


# ==============================================================================
# Vivado synthesis
#
# The Makefile intentionally delegates Tcl-heavy FPGA operations to scripts.
#
# Do not encode an entire FPGA implementation flow as shell commands here.
# Vivado Tcl is much easier to inspect, reproduce and debug.
#
# scripts/vivado_synth.tcl should consume:
#
#   $::env(TOP)
#   $::env(PART)
#   $::env(XDC)
#   $::env(RTL_SRCS)
#   $::env(SYNTH_BUILD)
#
# ==============================================================================

.PHONY: synth
synth: | $(SYNTH_BUILD)
	TOP="$(TOP)" \
	PART="$(PART)" \
	XDC="$(abspath $(XDC))" \
	RTL_SRCS="$(foreach f,$(RTL_SRCS),$(abspath $(f)))" \
	SYNTH_BUILD="$(abspath $(SYNTH_BUILD))" \
	$(VIVADO) \
		-mode batch \
		-source scripts/vivado_synth.tcl


.PHONY: bitstream
bitstream: | $(SYNTH_BUILD)
	TOP="$(TOP)" \
	PART="$(PART)" \
	XDC="$(abspath $(XDC))" \
	RTL_SRCS="$(foreach f,$(RTL_SRCS),$(abspath $(f)))" \
	SYNTH_BUILD="$(abspath $(SYNTH_BUILD))" \
	$(VIVADO) \
		-mode batch \
		-source scripts/vivado_bitstream.tcl


# ==============================================================================
# Toolchain sanity checking
# ==============================================================================

.PHONY: check-tools
check-tools:
	@set -e; \
	for tool in \
		$(VERIBLE) \
		$(SBY) \
		$(YOSYS) \
		$(PYTHON) \
		$(COCOTB_CONFIG); \
	do \
		printf '%-30s' "$$tool"; \
		if command -v "$$tool" >/dev/null 2>&1; then \
			echo "OK"; \
		else \
			echo "MISSING"; \
			exit 1; \
		fi; \
	done


# Vivado is separated because it may deliberately not be present on simulation
# or CI machines.
#
.PHONY: check-vivado
check-vivado:
	@command -v "$(VIVADO)" >/dev/null 2>&1 || { \
		echo "Vivado not found: $(VIVADO)"; \
		exit 1; \
	}
	@$(VIVADO) -version | head


# ==============================================================================
# Cleaning
# ==============================================================================

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(FORMAL_DIR)/*/
	rm -rf __pycache__
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( \
		-name '*.vcd' \
		-o -name '*.fst' \
		-o -name '*.jou' \
		-o -name '*.log' \
	\) -delete


.PHONY: distclean
distclean: clean
	rm -rf .Xil

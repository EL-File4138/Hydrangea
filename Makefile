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
# ├── software/
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
SW_DIR      ?= software
CONSTR_DIR  ?= constraints
BUILD_DIR   ?= build

WAVE_DIR    ?= simulation_wave

SIM_BUILD   := $(BUILD_DIR)/sim/$(TOP)
SW_BUILD    := $(BUILD_DIR)/software
SYNTH_BUILD := $(BUILD_DIR)/synth
FORMAL_BUILD:= $(BUILD_DIR)/formal_verification
WAVE_FILE   ?= $(abspath $(WAVE_DIR)/$(TOP).fst)
SURFER      ?= surfer


# ------------------------------------------------------------------------------
# RTL and testbench source manifests
#
# Keep source ordering and inclusion explicit. Each line is relative to the
# repository root so it also works with HDL tools' -f option.
# ------------------------------------------------------------------------------

RTL_FILELIST ?= $(RTL_DIR)/files.f
RTL_SRCS := $(shell sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$$/d' $(RTL_FILELIST))
TB_FILELIST ?= $(TB_DIR)/tb_files.f
TB_SRCS := $(shell sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$$/d' $(TB_FILELIST))
SIM_SRCS := $(RTL_SRCS) $(TB_SRCS)


# ------------------------------------------------------------------------------
# Tool configuration inherited from the activated EDA environment.
# ------------------------------------------------------------------------------

VERILATOR   ?= verilator
VERIBLE     ?= verible-verilog-lint
VERIBLE_SYNTAX ?= verible-verilog-syntax
SBY         ?= sby
YOSYS       ?= yosys
VIVADO      ?= vivado

PYTHON      ?= python3
COCOTB_CONFIG ?= cocotb-config
UPDATE_FILES_SCRIPT ?= scripts/update_files_f.py
RTL_NAMING_CHECKER ?= scripts/check_rtl_naming.py
RTL_NAMING_POLICY ?= scripts/rtl_naming_policy.json
VERIBLE_RULES_CONFIG ?= .rules.verible_lint
VERIBLE_WAIVER_FILE ?= config/verible.waiver

# The full Verible ruleset enforces the lowRISC SystemVerilog style guide's
# naming, port, register, and formatting conventions.
VERIBLE_LINT_FLAGS ?= --ruleset=all --rules=-instance-shadowing --rules_config=$(VERIBLE_RULES_CONFIG) --waiver_files=$(VERIBLE_WAIVER_FILE)


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

MARCH ?= rv32i_zicsr
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

# Prefer a listed `_tb` wrapper while keeping TOP named after the RTL DUT.
SIM_TOP := $(if $(filter $(TOP)_tb.sv,$(notdir $(TB_SRCS))),$(TOP)_tb,$(TOP))
COCOTB_TEST_MODULE ?= test-$(TOP)

VERILATOR_FLAGS ?= \
	-I$(RTL_DIR) \
	-I$(TB_DIR) \
	--Wall \
	--Wno-fatal \
	--trace \
	--timing

# Check elaborates the RTL without simulation-only trace generation. TOP takes
# precedence when supplied, while the complete core remains the default target.
CHECK_TOP ?= $(or $(TOP),rv32_core)
VERILATOR_CHECK_FLAGS ?= \
	-I$(RTL_DIR) \
	--Wall \
	--Wno-fatal \
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
		'  make check [TOP=<module>]  Elaborate RTL with Verilator' \
		'  make lint         Run lowRISC-style Verible RTL lint' \
		'  make lint-strict  Run fatal lowRISC-style Verible RTL lint' \
		'  make test TOP=<module>  Run the selected module Cocotb test' \
		'  make sim TOP=<module>   Run the selected module test with a waveform' \
		'  make wave         Open the latest FST waveform in Surfer' \
		'  make formal       Run SymbiYosys formal jobs' \
		'  make formal-smoke Run smoke formal job' \
		'  make update-files Refresh RTL and testbench SystemVerilog manifests' \
		'  make check-files  Check whether SystemVerilog manifests are up to date' \
		'  make source/vivado Stage RTL sources for Vivado' \
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

$(SW_DIR):
	mkdir -p $@

$(WAVE_DIR):
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

.PHONY: check
check:
	$(VERILATOR) $(VERILATOR_CHECK_FLAGS) --lint-only --top-module $(CHECK_TOP) $(RTL_SRCS)

.PHONY: lint lint-verible lint-naming check-waivers check-tool-compat
lint: lint-verible lint-naming

lint-verible:
	$(VERIBLE) $(VERIBLE_LINT_FLAGS) $(SIM_SRCS)

lint-naming:
	$(PYTHON) $(RTL_NAMING_CHECKER) --policy $(RTL_NAMING_POLICY) $(SIM_SRCS)

check-waivers:
	@test -f $(VERIBLE_WAIVER_FILE)
	@! grep -n -E '^[[:space:]]*waive[[:space:]]+' $(VERIBLE_WAIVER_FILE) || \
		{ echo "Verible waivers require an explicit review before use."; exit 1; }

check-tool-compat:
	$(VERIBLE) --version
	$(VERIBLE_SYNTAX) --version
	$(PYTHON) $(RTL_NAMING_CHECKER) --version


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
		TOP=$(SIM_TOP) \
		RTL_SRCS="$(addprefix $(CURDIR)/,$(SIM_SRCS))" \
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
		TOP=$(SIM_TOP) \
		RTL_SRCS="$(addprefix $(CURDIR)/,$(SIM_SRCS))" \
		TB_DIR="$(CURDIR)/$(TB_DIR)" \
		VERILATOR_FLAGS="$(VERILATOR_FLAGS)" \
		COCOTB_TEST_MODULE=$(COCOTB_TEST_MODULE)

.PHONY: sim sim/cocotb
sim: sim/cocotb

	sim/cocotb: cocotb-build | $(WAVE_DIR)
	@set -e; \
	$(MAKE) \
		-C $(SIM_BUILD) \
		-f $(CURDIR)/Makefile.cocotb \
		SIM=$(SIM) \
		TOP=$(SIM_TOP) \
		RTL_SRCS="$(addprefix $(CURDIR)/,$(SIM_SRCS))" \
		TB_DIR="$(CURDIR)/$(TB_DIR)" \
		VERILATOR_FLAGS="$(VERILATOR_FLAGS)" \
		COCOTB_TEST_MODULE=$(COCOTB_TEST_MODULE) \
		COMPILE_ARGS="$(if $(strip $(COMPILE_ARGS)),$(strip $(COMPILE_ARGS)) )--trace-fst --trace-structs" \
		SIM_ARGS="$(if $(strip $(SIM_ARGS)),$(strip $(SIM_ARGS)) )--trace --trace-file $(WAVE_FILE)"; \
	nohup $(SURFER) "$(WAVE_FILE)" >/dev/null 2>&1 &

.PHONY: wave
wave:
	@set -e; \
	wave_file="$$(ls -t "$(WAVE_DIR)"/*.fst 2>/dev/null | head -n 1)"; \
	if [ -z "$$wave_file" ]; then \
		echo "No FST waveform found in $(WAVE_DIR)/"; \
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

.PHONY: source/vivado
source/vivado:
	@set -e; \
	destination="$(BUILD_DIR)/vivado/$(RTL_DIR)"; \
	rm -rf "$(BUILD_DIR)/vivado"; \
	find "$(RTL_DIR)" -type f -print | while IFS= read -r source; do \
		target="$$destination/$${source#$(RTL_DIR)/}"; \
		mkdir -p "$$(dirname "$$target")"; \
		sed '/^[[:space:]]*`default_nettype[[:space:]]/d' "$$source" > "$$target"; \
	done

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
		$(VERIBLE_SYNTAX) \
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

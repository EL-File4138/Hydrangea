`default_nettype none

typedef enum logic [2:0] {
  ST_FETCH,
  ST_EXECUTE,
  ST_IO_WAIT,
  ST_COMMIT,
  ST_TRAP
} core_state_e;


module rv32_core #(
    parameter logic [31:0] ResetVector = 32'h0000_0000,
    // Verification-only fault injection; normal instantiations leave this disabled.
    parameter bit RejectTrapWriteForTest = 1'b0
) (
    input logic clk_i,
    input logic rst_ni,

    rv32_mem_if.requester imem_if,
    rv32_mem_if.requester dmem_if
);

  // State

  core_state_e state_q;

  logic [31:0] pc_q;
  logic [31:0] next_pc_q;

  logic [31:0] instruction_q;

  logic [31:0] rd_value_q;

  rv32_trap_pkg::trap_req_t trap_q;

  // Signal

  core_state_e state_d;

  logic [31:0] rd_value_d;
  logic [31:0] next_pc_d;

  logic trap_accept;
  rv32_trap_pkg::trap_req_t trap_d;

  logic rd_is_zero;
  logic rs1_is_zero;

  // Retained as an architectural retirement hook for the next core milestone.
  /* verilator lint_off UNUSEDSIGNAL */
  logic retire;
  /* verilator lint_on UNUSEDSIGNAL */

  rv32_inst_pkg::inst_semantics_t instruction_semantics;
  rv32_trap_pkg::trap_req_t instruction_trap;

  logic [31:0] rs1_value;
  logic [31:0] rs2_value;

  logic [31:0] alu_operand_a;
  logic [31:0] alu_operand_b;
  logic [31:0] alu_result;

  logic [31:0] control_pc;
  logic [31:0] control_result;
  rv32_trap_pkg::trap_req_t control_trap;

  logic regfile_write_enable;

  logic imem_ready;
  logic [31:0] imem_read_data;
  rv32_trap_pkg::trap_req_t lsu_imem_trap;
  logic dmem_ready;
  logic [31:0] lsu_result;
  rv32_trap_pkg::trap_req_t lsu_dmem_trap;

  logic [11:0] instruction_csr_read_address[2];
  logic instruction_csr_read_is_legal[2];
  logic [31:0] instruction_csr_read_data[2];
  logic [31:0] csr_result;
  // The decoder owns redirect selection; retain the controller status signal
  // for observability without making it a second PC arbitration path.
  /* verilator lint_off UNUSEDSIGNAL */
  logic csr_pc_is_valid;
  /* verilator lint_on UNUSEDSIGNAL */
  rv32_csr_pkg::csr_write_t instruction_csr_write;
  logic instruction_csr_write_is_legal;
  logic [31:0] csr_pc;
  rv32_trap_pkg::trap_req_t csr_trap;

  logic [11:0] trap_read_address[2];
  logic trap_read_is_legal[2];
  logic [31:0] trap_read_data[2];
  rv32_csr_pkg::csr_write_t trap_write[4];
  logic trap_write_is_legal[4];
  logic trap_pc_is_valid;
  logic [31:0] trap_pc;
  logic trap_is_legal;

  logic [11:0] csr_read_address[4];
  logic csr_read_is_legal[4];
  logic [31:0] csr_read_data[4];
  rv32_csr_pkg::csr_write_t csr_write[8];
  logic csr_write_is_legal[8];
  logic csr_write_enable;

  // Instances

  rv32_inst_decoder instruction_decoder (
      .inst_i(instruction_q),
      .sem_o(instruction_semantics),
      .inst_trap_o(instruction_trap)
  );

  rv32_register_file register_file (
      .clk_i(clk_i),
      .rst_ni(rst_ni),
      .write_enable_i(regfile_write_enable),
      .read_addr_a_i(instruction_semantics.rs1),
      .read_addr_b_i(instruction_semantics.rs2),
      .write_addr_i(instruction_semantics.rd),
      .write_data_i(rd_value_q),
      .read_data_a_o(rs1_value),
      .read_data_b_o(rs2_value)
  );

  rv32_alu alu (
      .operand_a_i(alu_operand_a),
      .operand_b_i(alu_operand_b),
      .opcode_i(instruction_semantics.alu_op),
      .result_o(alu_result)
  );

  rv32_control_transfer control_transfer (
      .ctrl_op_i(instruction_semantics.control_op),
      .pc_v_i(pc_q),
      .operand_a_i(rs1_value),
      .operand_b_i(rs2_value),
      .imm_i(instruction_semantics.imm),
      .pc_v_o(control_pc),
      .rd_v_o(control_result),
      .trap_o(control_trap)
  );

  rv32_lsu lsu (
      .if_req_i(state_q == ST_FETCH),
      .if_addr_i(pc_q),
      .if_ready_o(imem_ready),
      .if_rdata_o(imem_read_data),
      .if_trap_o(lsu_imem_trap),
      .data_req_i(state_q == ST_IO_WAIT),
      .lsu_op_i(instruction_semantics.lsu_op),
      .base_i(rs1_value),
      .store_data_i(rs2_value),
      .imm_i(instruction_semantics.imm),
      .data_ready_o(dmem_ready),
      .load_result_o(lsu_result),
      .data_trap_o(lsu_dmem_trap),
      .imem_if_i(imem_if),
      .dmem_if_i(dmem_if)
  );

  rv32_csr_controller csr (
      .csr_op_i(instruction_semantics.csr_op),
      .csr_imm_i(instruction_semantics.imm[11:0]),
      .csr_uimm_i(instruction_semantics.csr_uimm),
      .rs1_var_i(rs1_value),
      .rd_is_zero_i(rd_is_zero),
      .rs1_is_zero_i(rs1_is_zero),
      .csr_raddr_o(instruction_csr_read_address),
      .csr_rlegal_i(instruction_csr_read_is_legal),
      .csr_rdata_i(instruction_csr_read_data),
      .rd_result_o(csr_result),
      .csr_wr_o(instruction_csr_write),
      .csr_wr_legal_i(instruction_csr_write_is_legal),
      .pc_valid_o(csr_pc_is_valid),
      .pc_o(csr_pc),
      .trap_o(csr_trap)
  );

  rv32_trap trap (
      .trap_i(trap_q),
      .pc_i(pc_q),
      .csr_raddr_o(trap_read_address),
      .csr_rdata_i(trap_read_data),
      .csr_rlegal_i(trap_read_is_legal),
      .csr_wr_o(trap_write),
      .csr_wr_legal_i(trap_write_is_legal),
      .pc_valid_o(trap_pc_is_valid),
      .pc_o(trap_pc),
      .legal_o(trap_is_legal)
  );

  rv32_csr_register_bank csr_register_bank (
      .clk_i(clk_i),
      .rst_ni(rst_ni),
      .rd_addr_i(csr_read_address),
      .wr_en_i(csr_write_enable),
      .wr_i(csr_write),
      .rd_legal_o(csr_read_is_legal),
      .wr_legal_o(csr_write_is_legal),
      .rd_data_o(csr_read_data)
  );

  // Conditional signal
  assign rd_is_zero = (instruction_semantics.rd == '0);
  assign rs1_is_zero = (instruction_semantics.rs1 == '0);

  // MUX
  /// ALU Operand MUX
  assign alu_operand_a = instruction_semantics.rs1_is_used ? rs1_value : pc_q;
  assign alu_operand_b = instruction_semantics.rs2_is_used ? rs2_value : instruction_semantics.imm;

  /// rd Writeback MUX
  always_comb begin
    rd_value_d = '0;
    unique case (instruction_semantics.writeback_source)
      rv32_inst_pkg::WRITEBACK_SOURCE_ALU: rd_value_d = alu_result;
      rv32_inst_pkg::WRITEBACK_SOURCE_LSU: rd_value_d = lsu_result;
      rv32_inst_pkg::WRITEBACK_SOURCE_CONTROL: rd_value_d = control_result;
      rv32_inst_pkg::WRITEBACK_SOURCE_IMMEDIATE: rd_value_d = instruction_semantics.imm;
      rv32_inst_pkg::WRITEBACK_SOURCE_CSR: rd_value_d = csr_result;
      default: ;
    endcase
  end

  /// pc Next MUX
  always_comb begin
    next_pc_d = pc_q + 4;
    unique case (instruction_semantics.pc_source)
      rv32_inst_pkg::PC_SOURCE_SEQUENTIAL: next_pc_d = pc_q + 4;
      rv32_inst_pkg::PC_SOURCE_CONTROL: next_pc_d = control_pc;
      rv32_inst_pkg::PC_SOURCE_CSR: next_pc_d = csr_pc;
      default: ;
    endcase
  end

  /// CSR Register Bank MUX
  always_comb begin
    csr_read_address = '{default: '0};
    csr_write = '{default: '0};

    if (state_q == ST_TRAP) begin
      csr_read_address[0]   = trap_read_address[0];
      csr_read_address[1]   = trap_read_address[1];

      for (int i = 0; i < 4; i++) begin
        csr_write[i] = trap_write[i];
      end
    end else begin
      csr_read_address[0] = instruction_csr_read_address[0];
      csr_read_address[1] = instruction_csr_read_address[1];
      csr_write[0] = instruction_csr_write;
    end
  end

  always_comb begin
    instruction_csr_read_is_legal = '{default: '0};
    instruction_csr_read_data = '{default: '0};
    trap_read_is_legal = '{default: '0};
    trap_read_data = '{default: '0};
    trap_write_is_legal = '{default: '0};
    instruction_csr_write_is_legal = 1'b0;

    if (state_q == ST_TRAP) begin
      trap_read_is_legal[0] = csr_read_is_legal[0];
      trap_read_is_legal[1] = csr_read_is_legal[1];
      trap_read_data[0]     = csr_read_data[0];
      trap_read_data[1]     = csr_read_data[1];

      for (int i = 0; i < 4; i++) begin
        trap_write_is_legal[i] = csr_write_is_legal[i] && !(RejectTrapWriteForTest && (i == 0));
      end
    end else begin
      instruction_csr_read_is_legal[0] = csr_read_is_legal[0];
      instruction_csr_read_is_legal[1] = csr_read_is_legal[1];
      instruction_csr_read_data[0] = csr_read_data[0];
      instruction_csr_read_data[1] = csr_read_data[1];
      instruction_csr_write_is_legal = csr_write_is_legal[0];
    end
  end

  // FSM

  // Transition
  always_comb begin
    state_d = state_q;
    unique case (state_q)
      ST_FETCH: begin
        if (trap_accept) begin
          state_d = ST_TRAP;
        end else if (imem_ready) begin
          state_d = ST_EXECUTE;
        end
      end
      ST_EXECUTE: begin
        if (trap_accept) begin
          state_d = ST_TRAP;
        end else if (instruction_semantics.writeback_source
            == rv32_inst_pkg::WRITEBACK_SOURCE_LSU) begin
          state_d = ST_IO_WAIT;
        end else begin
          state_d = ST_COMMIT;
        end
      end
      ST_IO_WAIT: begin
        if (trap_accept) begin
          state_d = ST_TRAP;
        end else if (dmem_ready) begin
          state_d = ST_COMMIT;
        end
      end
      ST_COMMIT: begin
        state_d = ST_FETCH;
      end
      ST_TRAP: begin
        if (trap_pc_is_valid) begin
          state_d = ST_FETCH;
        end
      end
      default: begin

      end
    endcase
  end

  // State-derived signal

  always_comb begin
    regfile_write_enable = 0;
    csr_write_enable = 0;
    retire = 0;

    if (state_q == ST_COMMIT) begin
      retire = 1;
      if (instruction_semantics.rd_write_enable) begin
        regfile_write_enable = 1;
      end

      if (instruction_csr_write.write_enable) begin
        csr_write_enable = 1;
      end
    end else if (state_q == ST_TRAP) begin
      if (trap_is_legal) begin
        csr_write_enable = 1;
      end
    end
  end

  /// Trap Acceptance Priority MUX
  always_comb begin
    trap_accept = 0;
    trap_d = '0;

    unique case (state_q)
      ST_FETCH: begin
        if (lsu_imem_trap.is_valid) begin
          trap_accept = 1;
          trap_d = lsu_imem_trap;
        end

      end
      ST_EXECUTE: begin
        if (instruction_trap.is_valid) begin
          trap_accept = 1;
          trap_d = instruction_trap;
        end else if (instruction_semantics.writeback_source
            == rv32_inst_pkg::WRITEBACK_SOURCE_CONTROL
            && control_trap.is_valid) begin
          trap_accept = 1;
          trap_d = control_trap;
        end else if (instruction_semantics.writeback_source == rv32_inst_pkg::WRITEBACK_SOURCE_LSU
            && lsu_dmem_trap.is_valid) begin
          trap_accept = 1;
          trap_d = lsu_dmem_trap;
        end else if (instruction_semantics.writeback_source == rv32_inst_pkg::WRITEBACK_SOURCE_CSR
            && csr_trap.is_valid) begin
          trap_accept = 1;
          trap_d = csr_trap;
        end
      end
      ST_IO_WAIT: begin
        if (lsu_dmem_trap.is_valid) begin
          trap_accept = 1;
          trap_d = lsu_dmem_trap;
        end
      end
      default: begin
        // COMMIT and TRAP does nor arbitrate new trap
      end
    endcase
  end

  // Sequential
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin  // Async reset
      pc_q    <= ResetVector;
      state_q <= ST_FETCH;
      trap_q  <= '0;
    end else begin
      state_q <= state_d;  // FSM progression

      // FETCH -> EXECUTE
      if ((state_q == ST_FETCH) && imem_ready && !lsu_imem_trap.is_valid) begin
        instruction_q <= imem_read_data;
      end

      // EXECUTE/IO_WAIT -> COMMIT
      if (((state_q == ST_EXECUTE) || (state_q == ST_IO_WAIT)) && (state_d == ST_COMMIT)) begin
        next_pc_q <= next_pc_d;

        if (instruction_semantics.rd_write_enable) begin
          rd_value_q <= rd_value_d;
        end
      end

      // Any accepted synchronous trap -> TRAP
      if (trap_accept) begin
        trap_q <= trap_d;
      end

      // COMMIT -> FETCH_n
      if (state_q == ST_COMMIT) begin
        pc_q <= next_pc_q;
      end  // TRAP -> FETCH_n
      else if ((state_q == ST_TRAP) && trap_pc_is_valid) begin
        pc_q <= trap_pc;
      end
    end
  end

endmodule : rv32_core

`default_nettype wire

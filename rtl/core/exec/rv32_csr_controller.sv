`default_nettype none

module rv32_csr_controller (
    input rv32_inst_pkg::csr_op_e        csr_op_i,
    input logic                   [11:0] csr_imm_i,
    input logic                   [ 4:0] csr_uimm_i,

    input logic [31:0] rs1_var_i,
    input logic        rd_is_zero_i,  // Exception: Need a condition in Core to drive these
    input logic        rs1_is_zero_i,

    output logic [11:0] csr_raddr_o [2],
    input  logic        csr_rlegal_i[2],
    input  logic [31:0] csr_rdata_i [2],

    output logic                     [31:0] rd_result_o,
    output rv32_csr_pkg::csr_write_t        csr_wr_o,
    input  logic                            csr_wr_legal_i,

    output logic        pc_valid_o,
    output logic [31:0] pc_o,

    output rv32_trap_pkg::trap_req_t trap_o
);

  import rv32_trap_pkg::*;

  rv32_csr_pkg::csr_write_t write_tr;

  always_comb begin
    csr_raddr_o[0] = '0;
    csr_raddr_o[1] = '0;

    rd_result_o = '0;

    csr_wr_o = '0;

    pc_valid_o = 1'b0;
    pc_o = '0;

    trap_o = '0;

    write_tr = '0;

    unique case (csr_op_i)
      rv32_inst_pkg::CSR_SYS: begin
        if (!rd_is_zero_i || !rs1_is_zero_i) begin
          trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
        end else begin
          unique case (csr_imm_i)
            12'h000:  // ECALL
            trap_o = make_exception(EXC_ECALL_M, 32'b0);

            12'h001:  // EBREAK
            trap_o = make_exception(EXC_BREAKPOINT, 32'b0);

            12'h105: begin  // WFI - nop for now
            end

            12'h302: begin  // MRET
              logic [31:0] mstatus_next;

              csr_raddr_o[0] = rv32_csr_pkg::MEPC;
              csr_raddr_o[1] = rv32_csr_pkg::MSTATUS;
              if (csr_rlegal_i[0] && csr_rlegal_i[1]) begin
                mstatus_next = csr_rdata_i[1];
                mstatus_next[3] = csr_rdata_i[1][7];
                mstatus_next[7] = 1;

                write_tr.write_enable = 1;
                write_tr.address = rv32_csr_pkg::MSTATUS;
                write_tr.write_data = mstatus_next;

                csr_wr_o = write_tr;

                if (csr_wr_legal_i) begin
                  pc_valid_o = 1;
                  pc_o = csr_rdata_i[0];
                end else begin
                  trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
                end
              end else begin
                trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
              end
            end
            default: trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
          endcase
        end
      end
      rv32_inst_pkg::CSR_RW: begin
        if (!rd_is_zero_i) begin
          // Read
          csr_raddr_o[0] = csr_imm_i;
          if (!csr_rlegal_i[0]) begin
            trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
          end else begin
            rd_result_o = csr_rdata_i[0];

            // Write

            write_tr.write_enable = 1;
            write_tr.address = csr_imm_i;
            write_tr.write_data = rs1_var_i;

            csr_wr_o = write_tr;

            if (!csr_wr_legal_i) begin
              trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
            end
          end
        end else begin
          // Read suppressed architecturally, write still happens
          write_tr.write_enable    = 1;
          write_tr.address  = csr_imm_i;
          write_tr.write_data = rs1_var_i;

          csr_wr_o       = write_tr;

          if (!csr_wr_legal_i) begin
            trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
          end
        end
      end
      rv32_inst_pkg::CSR_RS: begin
        // Read
        csr_raddr_o[0] = csr_imm_i;
        if (!csr_rlegal_i[0]) begin
          trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
        end else begin
          rd_result_o = csr_rdata_i[0];


          if (!rs1_is_zero_i) begin
            // Write

            write_tr.write_enable = 1;
            write_tr.address = csr_imm_i;
            write_tr.write_data = csr_rdata_i[0] | rs1_var_i;

            csr_wr_o = write_tr;

            if (!csr_wr_legal_i) begin
              trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
            end
          end
        end
      end
      rv32_inst_pkg::CSR_RC: begin
        // Read
        csr_raddr_o[0] = csr_imm_i;
        if (!csr_rlegal_i[0]) begin
          trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
        end else begin
          rd_result_o = csr_rdata_i[0];


          if (!rs1_is_zero_i) begin
            // Write

            write_tr.write_enable = 1;
            write_tr.address = csr_imm_i;
            write_tr.write_data = csr_rdata_i[0] & ~rs1_var_i;

            csr_wr_o = write_tr;

            if (!csr_wr_legal_i) begin
              trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
            end
          end
        end
      end
      rv32_inst_pkg::CSR_RWI: begin
        if (!rd_is_zero_i) begin
          // Read
          csr_raddr_o[0] = csr_imm_i;
          if (!csr_rlegal_i[0]) begin
            trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
          end else begin
            rd_result_o = csr_rdata_i[0];


            // Write

            write_tr.write_enable = 1;
            write_tr.address = csr_imm_i;
            write_tr.write_data = {27'b0, csr_uimm_i};

            csr_wr_o = write_tr;

            if (!csr_wr_legal_i) begin
              trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
            end
          end
        end else begin
          // Read suppressed architecturally, write still happens
          write_tr.write_enable    = 1;
          write_tr.address  = csr_imm_i;
          write_tr.write_data = {27'b0, csr_uimm_i};

          csr_wr_o       = write_tr;

          if (!csr_wr_legal_i) begin
            trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
          end
        end
      end
      rv32_inst_pkg::CSR_RSI: begin
        // Read
        csr_raddr_o[0] = csr_imm_i;
        if (!csr_rlegal_i[0]) begin
          trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
        end else begin
          rd_result_o = csr_rdata_i[0];


          if (csr_uimm_i != 5'b0) begin
            // Write

            write_tr.write_enable = 1;
            write_tr.address = csr_imm_i;
            write_tr.write_data = csr_rdata_i[0] | {27'b0, csr_uimm_i};

            csr_wr_o = write_tr;

            if (!csr_wr_legal_i) begin
              trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
            end
          end
        end
      end
      rv32_inst_pkg::CSR_RCI: begin
        // Read
        csr_raddr_o[0] = csr_imm_i;
        if (!csr_rlegal_i[0]) begin
          trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
        end else begin
          rd_result_o = csr_rdata_i[0];


          if (csr_uimm_i != 5'b0) begin
            // Write

            write_tr.write_enable = 1;
            write_tr.address = csr_imm_i;
            write_tr.write_data = csr_rdata_i[0] & ~{27'b0, csr_uimm_i};

            csr_wr_o = write_tr;

            if (!csr_wr_legal_i) begin
              trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
            end
          end
        end
      end
      default: begin
        trap_o = make_exception(EXC_ILLEGAL_INST, 32'b0);
      end
    endcase
  end

endmodule : rv32_csr_controller

`default_nettype wire

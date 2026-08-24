// `include "../type/rv32_inst_pkg.sv"

`default_nettype none

module rv32_instdec (
    input logic [31:0] inst_i,
    output rv32_inst_pkg::inst_sem_t sem_o,
    output rv32_trap_pkg::trap_req_t inst_trap_o
);
  logic [6:0] op;
  logic [2:0] funct3;
  logic legal;

  assign op = inst_i[6:0];
  assign funct3 = inst_i[14:12];

  rv32_inst_pkg::inst_fmt_t imm_fmt;
  logic [31:0] imm;

  rv32_immgen immgen (
      .inst_i(inst_i),
      .inst_fmt_i(imm_fmt),
      .imm_o(imm)
  );

  always_comb begin
    // Defaults: instruction is illegal unless recognized below.
    legal = 0;
    sem_o = '0;
    inst_trap_o = '0;
    imm_fmt = rv32_inst_pkg::R;  // arbitrary safe default; ignored if legal == 0
    if (op[1:0] == 2'b11) begin
      case (op[6:2])
        5'b00000: begin  // LSU - Load
          if (funct3 == 3'b011 || funct3 == 3'b110 || funct3 == 3'b111) begin
          end else begin
            imm_fmt = rv32_inst_pkg::I;

            legal = 1;

            sem_o.rs1 = inst_i[19:15];
            sem_o.rd = inst_i[11:7];

            sem_o.rs1_used = 1;
            sem_o.rs2_used = 0;

            sem_o.rd_write = 1;

            sem_o.imm = imm;

            sem_o.lsu_op = rv32_inst_pkg::lsu_op_t'({op[5], funct3});

            sem_o.wb_src = rv32_inst_pkg::WB_LSU;
          end
        end
        5'b00100: begin  // ALU - Immediate
          if (
              (
                funct3 == 3'b001 && inst_i[31:25] != 7'b0000000
              ) ||
              (
                funct3 == 3'b101 &&
                inst_i[31:25] != 7'b0000000 &&
                inst_i[31:25] != 7'b0100000
              )
             ) begin
          end else begin
            imm_fmt = rv32_inst_pkg::I;

            legal = 1;

            sem_o.rs1 = inst_i[19:15];
            sem_o.rd = inst_i[11:7];

            sem_o.rs1_used = 1;
            sem_o.rs2_used = 0;

            sem_o.rd_write = 1;

            sem_o.imm = (funct3 == 3'b001 || funct3 == 3'b101) ? {27'b0, imm[4:0]} : imm;

            sem_o.alu_op = (funct3 == 3'b001 || funct3 == 3'b101)
            ? rv32_inst_pkg::alu_op_t'({inst_i[30], funct3})
            : rv32_inst_pkg::alu_op_t'({1'b0, funct3});

            sem_o.wb_src = rv32_inst_pkg::WB_ALU;
          end
        end
        5'b00101: begin  // `auipc`
          imm_fmt = rv32_inst_pkg::U;

          legal = 1;

          sem_o.rd = inst_i[11:7];

          sem_o.rd_write = 1;

          sem_o.imm = imm;

          sem_o.alu_op = rv32_inst_pkg::ALU_Add;

          sem_o.wb_src = rv32_inst_pkg::WB_ALU;
        end
        5'b01000: begin  // LSu - Store
          if (funct3 == 3'b000 || funct3 == 3'b001 || funct3 == 3'b010) begin
            imm_fmt = rv32_inst_pkg::S;

            legal = 1;

            sem_o.rs1 = inst_i[19:15];
            sem_o.rs2 = inst_i[24:20];

            sem_o.rs1_used = 1;
            sem_o.rs2_used = 1;

            sem_o.rd_write = 0;

            sem_o.imm = imm;

            sem_o.lsu_op = rv32_inst_pkg::lsu_op_t'({op[5], funct3});

            sem_o.wb_src = rv32_inst_pkg::WB_LSU;
          end else begin
          end
        end
        5'b01100: begin  // ALU - Register
          if (inst_i[31:25] == 7'b0000000 ||
              (
                inst_i[31:25] == 7'b0100000 &&
                (
                  funct3 == 3'b000 || funct3 == 3'b101
                )
              )
             ) begin
            imm_fmt = rv32_inst_pkg::R;

            legal = 1;

            sem_o.rs1 = inst_i[19:15];
            sem_o.rs2 = inst_i[24:20];
            sem_o.rd = inst_i[11:7];

            sem_o.rs1_used = 1;
            sem_o.rs2_used = 1;

            sem_o.rd_write = 1;

            sem_o.alu_op = rv32_inst_pkg::alu_op_t'({inst_i[30], funct3});

            sem_o.wb_src = rv32_inst_pkg::WB_ALU;
          end
        end
        5'b01101: begin  // `lui`
          imm_fmt = rv32_inst_pkg::U;

          legal = 1;

          sem_o.rd = inst_i[11:7];

          sem_o.rd_write = 1;

          sem_o.imm = imm;

          sem_o.wb_src = rv32_inst_pkg::WB_IMM;
        end
        5'b11000: begin  // CTRL - Branch
          if (funct3 == 3'b010 || funct3 == 3'b011) begin
          end else begin
            imm_fmt = rv32_inst_pkg::B;

            legal = 1;

            sem_o.rs1 = inst_i[19:15];
            sem_o.rs2 = inst_i[24:20];

            sem_o.rs1_used = 1;
            sem_o.rs2_used = 1;

            sem_o.rd_write = 0;

            sem_o.imm = imm;

            sem_o.ctrl_op = rv32_inst_pkg::ctrl_op_t'(funct3);

            sem_o.wb_src = rv32_inst_pkg::WB_CTRL;
            sem_o.pc_src = rv32_inst_pkg::PC_CTRL;
          end
        end
        5'b11001: begin  // `jalr`
          if (funct3 == 3'b000) begin
            imm_fmt = rv32_inst_pkg::I;

            legal = 1;

            sem_o.rs1 = inst_i[19:15];
            sem_o.rd = inst_i[11:7];

            sem_o.rs1_used = 1;
            sem_o.rs2_used = 0;

            sem_o.rd_write = 1;

            sem_o.imm = imm;

            sem_o.ctrl_op = rv32_inst_pkg::CTRL_Jalr;

            sem_o.wb_src = rv32_inst_pkg::WB_CTRL;
            sem_o.pc_src = rv32_inst_pkg::PC_CTRL;
          end
        end
        5'b11011: begin  // `jal`
          imm_fmt = rv32_inst_pkg::J;

          legal = 1;

          sem_o.rd = inst_i[11:7];

          sem_o.rs1_used = 0;
          sem_o.rs2_used = 0;

          sem_o.rd_write = 1;

          sem_o.imm = imm;

          sem_o.ctrl_op = rv32_inst_pkg::CTRL_Jal;

          sem_o.wb_src = rv32_inst_pkg::WB_CTRL;
          sem_o.pc_src = rv32_inst_pkg::PC_CTRL;
        end
        5'b11100: begin  // SYSTEM
          if (funct3 == 3'b100) begin
          end else begin
            imm_fmt = rv32_inst_pkg::I;

            legal = 1;

            sem_o.rs1 = (funct3[2] == 1) ? 5'b0 : inst_i[19:15];
            sem_o.rd = inst_i[11:7];

            sem_o.rs1_used = (!(funct3 == 3'b000) && !(funct3[2] == 1));
            sem_o.rs2_used = 0;

            sem_o.rd_write = !(funct3 == 3'b000);

            sem_o.imm = imm;

            sem_o.csr_op = rv32_inst_pkg::csr_op_t'(funct3);

            sem_o.csr_uimm = (funct3[2] == 1) ? inst_i[19:15] : 5'b0;

            sem_o.wb_src = rv32_inst_pkg::WB_CSR;
            sem_o.pc_src = (funct3 == 3'b000) ? rv32_inst_pkg::PC_CSR : rv32_inst_pkg::PC_SEQ;
          end
        end
        5'b00011: begin  // `FENCE`
          if (funct3 == 3'b000) begin
            // Base FENCE is a serialization no-op; FENCE.I is unsupported.
            legal = 1;
            sem_o.pc_src = rv32_inst_pkg::PC_SEQ;
          end
        end
        default: begin
        end
      endcase
    end

    if (!legal) begin
      inst_trap_o = rv32_trap_pkg::exception(rv32_trap_pkg::EXC_ILLEGAL_INST, inst_i);
    end
  end


endmodule : rv32_instdec

`default_nettype wire

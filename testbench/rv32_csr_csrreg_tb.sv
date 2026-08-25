module rv32_csr_csrreg_tb (
    input logic clk_i,
    input logic rst_ni,

    input rv32_inst_pkg::csr_op_t csr_op_i,
    input logic [11:0] csr_imm_i,
    input logic [4:0] csr_uimm_i,
    input logic [31:0] rs1_var_i,
    input logic rd_is_zero_i,
    input logic rs1_is_zero_i,

    output logic [31:0] rd_result_o,
    output logic pc_valid_o,
    output logic [31:0] pc_o,
    output rv32_trap_pkg::trap_req_t trap_o
);

  logic [11:0] csr_raddr[2];
  logic csr_rlegal[2];
  logic [31:0] csr_rdata[2];
  rv32_csr_pkg::csr_write_t csr_wr[1];
  logic csr_wr_legal[1];

  rv32_csr csr (
      .csr_op_i,
      .csr_imm_i,
      .csr_uimm_i,
      .rs1_var_i,
      .rd_is_zero_i,
      .rs1_is_zero_i,
      .csr_raddr_o(csr_raddr),
      .csr_rlegal_i(csr_rlegal),
      .csr_rdata_i(csr_rdata),
      .rd_result_o,
      .csr_wr_o(csr_wr[0]),
      .csr_wr_legal_i(csr_wr_legal[0]),
      .pc_valid_o,
      .pc_o,
      .trap_o
  );

  rv32_csrreg #(
      .ReadPorts(2),
      .WritePorts(1)
  ) csrreg (
      .clk_i,
      .rst_ni,
      .rd_addr_i(csr_raddr),
      .wr_en_i(1'b1),
      .wr_i(csr_wr),
      .rd_legal_o(csr_rlegal),
      .wr_legal_o(csr_wr_legal),
      .rd_data_o(csr_rdata)
  );

endmodule : rv32_csr_csrreg_tb

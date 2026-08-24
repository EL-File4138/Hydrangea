`default_nettype none

module rv32_lsu_tb (
    input logic if_req_i,
    input logic [31:0] if_addr_i,
    output logic if_ready_o,
    output logic [31:0] if_rdata_o,
    output logic if_err_o,
    input logic data_req_i,
    input rv32_inst_pkg::lsu_op_t lsu_op_i,
    input logic [31:0] base_i,
    input logic [31:0] store_data_i,
    input logic [31:0] imm_i,
    output logic data_ready_o,
    output logic [31:0] load_result_o,
    output logic data_err_o,
    input logic imem_ready_i,
    input logic [31:0] imem_rdata_i,
    input logic imem_err_i,
    output logic imem_req_o,
    output logic imem_we_o,
    output logic [31:0] imem_addr_o,
    output logic [31:0] imem_wdata_o,
    output logic [3:0] imem_wstrb_o,
    input logic dmem_ready_i,
    input logic [31:0] dmem_rdata_i,
    input logic dmem_err_i,
    output logic dmem_req_o,
    output logic dmem_we_o,
    output logic [31:0] dmem_addr_o,
    output logic [31:0] dmem_wdata_o,
    output logic [3:0] dmem_wstrb_o
);
  rv32_mem_if imem_if();
  rv32_mem_if dmem_if();

  assign imem_if.ready = imem_ready_i;
  assign imem_if.rdata = imem_rdata_i;
  assign imem_if.err = imem_err_i;
  assign imem_req_o = imem_if.req;
  assign imem_we_o = imem_if.we;
  assign imem_addr_o = imem_if.addr;
  assign imem_wdata_o = imem_if.wdata;
  assign imem_wstrb_o = imem_if.wstrb;

  assign dmem_if.ready = dmem_ready_i;
  assign dmem_if.rdata = dmem_rdata_i;
  assign dmem_if.err = dmem_err_i;
  assign dmem_req_o = dmem_if.req;
  assign dmem_we_o = dmem_if.we;
  assign dmem_addr_o = dmem_if.addr;
  assign dmem_wdata_o = dmem_if.wdata;
  assign dmem_wstrb_o = dmem_if.wstrb;

  rv32_lsu dut (
      .if_req_i,
      .if_addr_i,
      .if_ready_o,
      .if_rdata_o,
      .if_err_o,
      .data_req_i,
      .lsu_op_i,
      .base_i,
      .store_data_i,
      .imm_i,
      .data_ready_o,
      .load_result_o,
      .data_err_o,
      .imem_if_i(imem_if),
      .dmem_if_i(dmem_if)
  );
endmodule : rv32_lsu_tb

`default_nettype wire

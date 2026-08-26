`default_nettype none

module rv32_core_backpressure_tb (
    input logic clk_i,
    input logic rst_ni,
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
    output logic [3:0] dmem_wstrb_o,
    output logic [31:0] pc_o,
    output logic [2:0] state_o,
    output logic [31:0] gpr_o[32]
);
  rv32_mem_if imem_if ();
  rv32_mem_if dmem_if ();

  rv32_core u_core (
      .clk_i,
      .rst_ni,
      .imem_if(imem_if),
      .dmem_if(dmem_if)
  );

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

  assign pc_o = u_core.pc_q;
  assign state_o = u_core.state_q;
  for (genvar i = 0; i < 32; i++) begin : g_gpr_debug
    assign gpr_o[i] = u_core.register_file.reg_cell[i];
  end
endmodule : rv32_core_backpressure_tb

`default_nettype wire

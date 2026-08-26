`default_nettype none

module rv32_core_failclosed_tb (
    input logic clk_i,
    input logic rst_ni,
    output logic [31:0] pc_o,
    output logic [2:0] state_o,
    output logic [31:0] csr_o[15]
);
  rv32_mem_if imem_if ();
  rv32_mem_if dmem_if ();

  rv32_core #(
      .RejectTrapWriteForTest(1'b1)
  ) u_core (
      .clk_i,
      .rst_ni,
      .imem_if(imem_if),
      .dmem_if(dmem_if)
  );

  rv32_shared_sync_ram_adapter #(
      .AddrWidth(8)
  ) u_memory (
      .clk_i,
      .rst_ni,
      .imem_if_i(imem_if),
      .dmem_if_i(dmem_if)
  );

  assign pc_o = u_core.pc_q;
  assign state_o = u_core.state_q;

  for (genvar i = 0; i < 15; i++) begin : g_csr_debug
    assign csr_o[i] = u_core.csr_register_bank.reg_cell[i];
  end
endmodule : rv32_core_failclosed_tb

`default_nettype wire
